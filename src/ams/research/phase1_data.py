"""Read-only corpus inventory, real source boundaries and blinded review packets."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from ams.data.mpbench import load_mpbench
from ams.research.phase1_common import (
    CONTEXTS,
    RAW_HASHES,
    PreparationError,
    digest,
    file_hash,
    opaque,
    read_jsonl,
    require,
    rng,
)

ARTIFACT_BOUNDARY = re.compile(r"\n-{3,}\n|^(?=From:\s)", re.MULTILINE)


def strict_objects(path: Path) -> list[dict]:
    """Consume every byte, including the release's concatenated-object line."""
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    cursor, rows = 0, []
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        try:
            row, end = decoder.raw_decode(text, cursor)
        except json.JSONDecodeError as e:
            raise PreparationError(f"Unconsumed/invalid JSON in {path} at {cursor}") from e
        require(isinstance(row, dict), f"Non-object in {path} at {cursor}")
        rows.append(row)
        cursor = end
    return rows


def load_corpus(root: Path) -> tuple[list, dict]:
    hashes = {name: file_hash(root / name) for name in RAW_HASHES}
    require(hashes == RAW_HASHES, "Official MPBench hashes differ from frozen protocol inputs")
    strict = [row for name in RAW_HASHES for row in strict_objects(root / name)]
    cases, _ = load_mpbench(root)
    require(len(cases) == len(strict) == 6240, "Incomplete MPBench decode")
    require(all(c.raw == r for c, r in zip(cases, strict, strict=True)), "Loader mismatch")
    require(len({c.cid for c in cases}) == len(cases), "Duplicate qualified case keys")
    return cases, hashes


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def stratum(case) -> str:
    if case.is_adversarial:
        return "attack"
    if not case.expected_memory.strip():
        return "unannotated_benign"
    if case.legitimate_memory_write is True:
        return "explicit_benign"
    if case.legitimate_memory_write is False:
        return "suggestive_benign"
    return "unannotated_benign"


def source_parts(case_id: str, user_query: str, context: str) -> list[dict]:
    """Character offsets into untouched user_query/context, matching original splitting."""
    out = [
        {
            "artifact_id": opaque("a", case_id, "principal", digest(user_query)),
            "field": "user_query",
            "role": "principal",
            "start": 0,
            "end": len(user_query),
            "text": user_query,
            "content_hash": digest(user_query),
        }
    ]
    start = 0
    boundaries = [(m.start(), m.end()) for m in ARTIFACT_BOUNDARY.finditer(context)]
    for end, following in [*boundaries, (len(context), len(context))]:
        raw = context[start:end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if raw.strip():
            lo, hi = start + left, start + right
            text = context[lo:hi]
            out.append(
                {
                    "artifact_id": opaque("a", case_id, "external", lo, hi, digest(text)),
                    "field": "context",
                    "role": "external",
                    "start": lo,
                    "end": hi,
                    "text": text,
                    "content_hash": digest(text),
                }
            )
        start = following
    return out


def frozen_claims(journal: Path, valid_cids: set[str]) -> tuple[dict, dict]:
    rows = read_jsonl(journal)
    require(len(rows) == len(valid_cids), "Frozen write journal does not cover every input")
    claims = {}
    for row in rows:
        cid = row["cid"]
        require(cid in valid_cids and cid not in claims, "Duplicate/unknown frozen case")
        claims[cid] = []
        for record in row["written"]:
            text = record.get("metadata", {}).get("raw_text")
            require(isinstance(text, str) and bool(text.strip()), "Frozen raw claim unavailable")
            claims[cid].append(
                {
                    "record_kind": "claim",
                    "record_id": opaque("r", cid, record["entry_id"], digest(text)),
                    "text": text,
                    "content_hash": digest(text),
                    "legacy_entry_id": record["entry_id"],
                    "legacy_source_id_unverified": record.get("metadata", {}).get("source_id"),
                    "source_link_status": "requires_independent_span_review",
                }
            )
    return claims, {
        "journal_sha256": file_hash(journal),
        "claims": sum(map(len, claims.values())),
        "empty_bundles": sum(not v for v in claims.values()),
        "chunk_records_available": False,
    }


def import_evidence_catalog(path: Path, cases: list, records: dict) -> dict:
    """Accept an actual frozen/cached chunk export, never reconstruct chunks by guessing.

    Complete exports have one row per original qualified case, bind raw payloads,
    and declare exporter/config provenance. The trusted preparer must verify the
    exporter; these structural checks cannot prove an export was honestly produced.
    """
    rows = read_jsonl(path)
    by_cid = {c.cid: c for c in cases}
    require(len(rows) == len(by_cid), "Chunk export must cover every original source case")
    seen, count = set(), 0
    for row in rows:
        cid = row.get("cid")
        require(cid in by_cid and cid not in seen, "Duplicate/unknown chunk source")
        seen.add(cid)
        case = by_cid[cid]
        require(
            row.get("payload_hash") == digest([case.user_query, case.context]),
            "Chunk export/raw payload mismatch",
        )
        require(
            row.get("complete") is True and row.get("exporter_fingerprint"),
            "Chunk completeness/exporter fingerprint missing",
        )
        chunks = row.get("evidence_chunks")
        require(isinstance(chunks, list) and bool(chunks), "Missing frozen evidence chunks")
        legacy_ids = set()
        for ch in chunks:
            text, legacy = ch.get("text"), ch.get("chunk_id")
            require(
                isinstance(text, str)
                and text.strip()
                and isinstance(legacy, str)
                and legacy not in legacy_ids,
                "Invalid/duplicate chunk record",
            )
            require(ch.get("content_hash") == digest(text), "Chunk text/hash mismatch")
            legacy_ids.add(legacy)
            records[cid].append(
                {
                    "record_id": opaque("e", cid, legacy, digest(text)),
                    "record_kind": "evidence_chunk",
                    "text": text,
                    "content_hash": digest(text),
                    "legacy_entry_id": legacy,
                    "source_link_status": "requires_independent_span_review",
                }
            )
            count += 1
    return {
        "chunk_records_available": True,
        "chunks": count,
        "chunk_catalog_sha256": file_hash(path),
    }


def duplicate_groups(cases: list) -> tuple[dict[str, str], list[dict]]:
    """Exact input triples or >=.8 token-5-gram Jaccard question components.

    Inverted shingles avoid an unconditional quadratic all-pairs comparison.
    Short questions use exact normalization only (no empty-set similarity).
    """
    parent = list(range(len(cases)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        parent[max(a, b)] = min(a, b)

    seen_input, seen_query = {}, {}
    shingles, inverted = [], defaultdict(list)
    for i, c in enumerate(cases):
        triple = digest(
            [normalized(c.user_query), normalized(c.context), normalized(c.retrieval_query)]
        )
        if triple in seen_input:
            union(i, seen_input[triple])
        seen_input[triple] = i
        question = normalized(c.retrieval_query)
        if question and question in seen_query:
            union(i, seen_query[question])
        if question:
            seen_query[question] = i
        tokens = re.findall(r"\w+", question)
        grams = {tuple(tokens[k : k + 5]) for k in range(max(0, len(tokens) - 4))}
        candidates = Counter(j for g in grams for j in inverted[g])
        for j, overlap in candidates.items():
            denominator = len(grams) + len(shingles[j]) - overlap
            if 5 * overlap >= 4 * denominator:
                union(i, j)
        shingles.append(grams)
        for g in grams:
            inverted[g].append(i)
    components = defaultdict(list)
    for i, c in enumerate(cases):
        components[find(i)].append(c.cid)
    groups, report = {}, []
    for members in components.values():
        gid = opaque("g", sorted(members))
        groups.update({cid: gid for cid in members})
        report.append(
            {
                "group_id": gid,
                "size": len(members),
                "manual_review_required": len(members) > 32,
                "case_keys": sorted(members),
            }
        )
    return groups, sorted(report, key=lambda r: (-r["size"], r["group_id"]))


def catalogs(cases: list, claims: dict, groups: dict) -> tuple[list, list, list]:
    public, private, packets = [], [], []
    for c in cases:
        pid = opaque("p", c.cid)
        parts = source_parts(pid, c.user_query, c.context)
        candidate = (
            c.domain in CONTEXTS
            and bool(c.retrieval_query.strip())
            and bool(c.expected_memory.strip())
        )
        public.append(
            {
                "contribution_id": pid,
                "context_id": c.domain,
                "user_query": c.user_query,
                "context": c.context,
                "artifacts": parts,
                "payload_hash": digest([c.user_query, c.context]),
            }
        )
        private.append(
            {
                "contribution_id": pid,
                "original_case_key": c.cid,
                "original_id": c.original_cid,
                "Y_case": c.is_adversarial,
                "stratum": stratum(c),
                "expected_memory": c.expected_memory,
                "retrieval_query": c.retrieval_query,
                "context_id": c.domain,
                "group_id": groups[c.cid],
                "review_candidate": candidate,
                "records": claims[c.cid],
            }
        )
        if candidate:
            packets.append(
                {
                    "contribution_id": pid,
                    "context_id": c.domain,
                    "use_id": opaque("use", pid, c.retrieval_query),
                    "intended_use": c.retrieval_query,
                    "task": c.user_query,
                    "artifacts": parts,
                    "records": [
                        {k: r[k] for k in ("record_id", "record_kind", "text", "content_hash")}
                        for r in claims[c.cid]
                    ],
                }
            )
    # Release order is split-correlated. Do not leak it through a supposedly blind packet list.
    public.sort(key=lambda r: r["contribution_id"])
    rng("PREPARATION", "blinded-packet-order").shuffle(packets)
    return public, private, packets


def inventory(cases: list) -> dict:
    totals, domains = Counter(), defaultdict(Counter)
    for c in cases:
        readable = bool(c.retrieval_query.strip())
        totals["inputs"] += 1
        totals["attack_inputs" if c.is_adversarial else "benign_inputs"] += 1
        totals["readable" if readable else "write_only"] += 1
        if readable:
            key = stratum(c)
            totals[key] += 1
            domains[c.domain][key] += 1
    return {"counts": dict(totals), "readable_by_context": dict(domains)}
