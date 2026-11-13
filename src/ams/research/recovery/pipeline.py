"""Versioned Steps 3–5 outputs. Never writes to original data, caches or Phase 1."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.phase1 import check_prepared
from ams.research.phase1_common import digest, read_jsonl, require, write_json, write_jsonl
from ams.research.recovery.annotation import (
    assert_blinded,
    draft_questions,
    qa_validation_template,
    review_coverage,
    reviewer_forms,
    update_packets,
)
from ams.research.recovery.offline import ReadOnlyCache, no_network, original_cut, sha_file
from ams.research.recovery.records import reconstruct, saved_chunk_observations


def protected_fingerprints(path: Path) -> dict:
    before = json.loads(path.read_text())
    changes = [name for name, expected in before.items() if sha_file(Path(name)) != expected]
    require(not changes, f"Pre-existing protected files changed: {changes}")
    return {
        "checked_existing_files": len(before),
        "changed_existing_files": changes,
        "before_snapshot_sha256": sha_file(path),
    }


def run(
    prepared: Path, history: Path, caches: list[Path], out: Path, reviews: Path | None = None
) -> dict:
    require(not out.exists(), "Output exists: choose a new version; nothing is overwritten")
    with no_network():
        check_prepared(prepared)
        manifest = json.loads((history / "manifest.json").read_text())
        config = manifest["config"]
        require(
            config["typed"]["endorsement"] == "sentence"
            and config["typed"]["evidence_slots"] == 4
            and config["models"]["embed"] == "local:"
            and config["models"]["memory"] == "openrouter:openai/gpt-4o-mini",
            "Unsupported historical configuration; no substitution allowed",
        )
        prompts = PromptLibrary()
        for name, expected in manifest["prompts"].items():
            prompt, version = name.split("/")
            require(
                prompts.get(prompt, version).sha256 == expected,
                f"Historical prompt fingerprint mismatch: {name}",
            )
        inputs = [
            prepared / "preparation_manifest.json",
            prepared / "private/case_index.jsonl",
            prepared / "private/blinded_packets.jsonl",
            prepared / "public/candidate_inputs.jsonl",
            history / "manifest.json",
            history / "graph_stats.json",
            history / "written_memories-no_defence.jsonl",
            history / "outcome_progress-no_defence.jsonl",
            *caches,
        ]
        input_hashes = {str(p): sha_file(p) for p in inputs}
        public = {
            r["contribution_id"]: r for r in read_jsonl(prepared / "public/candidate_inputs.jsonl")
        }
        private_rows = read_jsonl(prepared / "private/case_index.jsonl")
        private = {r["original_case_key"]: r for r in private_rows}
        journal = read_jsonl(history / "written_memories-no_defence.jsonl")
        require(len(journal) == len(private) == 6240, "Wrong historical input coverage")
        require({r["cid"] for r in journal} == set(private), "Write journal/source join mismatch")
        graph_stats = json.loads((history / "graph_stats.json").read_text())
        require(
            sum(len(r["written"]) for r in journal) == graph_stats["n_claims"],
            "Historical claim count/journal mismatch",
        )
        observed = saved_chunk_observations(history / "outcome_progress-no_defence.jsonl")
        print(f"Saved evidence observations: {len(observed)} unique chunk IDs", flush=True)
        cache = ReadOnlyCache(caches)
        try:
            bundles, recovery = reconstruct(
                journal,
                public,
                private,
                cache,
                original_cut(Path("src/ams/memory/evidence.py")),
                prompts,
                observed,
                graph_stats["n_evidence_chunks"],
            )
            recovery["cache_access"] = dict(cache.counts)
        finally:
            cache.close()
        print(
            f"Recovered chunk texts: {recovery['verification']['reconstructed_chunks']}", flush=True
        )
        old_packets = read_jsonl(prepared / "private/blinded_packets.jsonl")
        packets, versions = update_packets(old_packets, bundles)
        require(len(packets) == 2114, "Unexpected review population; do not change strata")
        parents = {
            r["record_id"]: r.get("legacy_parent_artifact_id") for b in bundles for r in b["claims"]
        }
        candidates, qa = draft_questions(packets, parents)

        def review_input(name):
            path = reviews / name if reviews else None
            return read_jsonl(path) if path and path.exists() else []

        coverage = review_coverage(
            packets,
            review_input("reviews_a.jsonl"),
            review_input("reviews_b.jsonl"),
            review_input("adjudications.jsonl"),
            candidates,
            review_input("qa_reviews.jsonl"),
        )
        claim_rows, chunk_rows, bundle_rows, links, evidence_catalog = [], [], [], [], []
        exporter = digest(
            {
                "method": "cached-vector-cut-v1",
                "history": input_hashes[str(history / "manifest.json")],
                "algorithm": sha_file(Path("src/ams/memory/evidence.py")),
            }
        )
        for b in bundles:
            pid = b["contribution_id"]
            claim_rows += [{"contribution_id": pid, **r} for r in b["claims"]]
            chunk_rows += [{"contribution_id": pid, **r} for r in b["evidence_chunks"]]
            bundle_rows.append(
                {k: v for k, v in b.items() if k not in {"claims", "evidence_chunks"}}
                | {
                    "claim_ids": [r["record_id"] for r in b["claims"]],
                    "chunk_ids": [r["record_id"] for r in b["evidence_chunks"]],
                }
            )
            for r in [*b["claims"], *b["evidence_chunks"]]:
                links.append(
                    {
                        "contribution_id": pid,
                        "record_id": r["record_id"],
                        "record_kind": r["record_kind"],
                        "content_hash": r["content_hash"],
                        "construction_source_spans": r.get("source_spans", []),
                        "parent_status": r["structural_parent_status"],
                        "semantic_attribution_status": "not_independently_reviewed",
                        "attributable_origin_id": None,
                        "uploader_id": None,
                    }
                )
            original = public[pid]
            evidence_catalog.append(
                {
                    "cid": b["original_case_key"],
                    "payload_hash": digest([original["user_query"], original["context"]]),
                    "complete": b["bundle_completeness"]
                    == "complete_text_and_structural_provenance",
                    "exporter_fingerprint": exporter,
                    "source_run_id": manifest["run_id"],
                    "recovery_status": b["recovery_status"],
                    "evidence_chunks": [
                        {
                            "chunk_id": r["legacy_entry_id"],
                            "text": r["text"],
                            "content_hash": r["content_hash"],
                            "source_spans": r["source_spans"],
                        }
                        for r in b["evidence_chunks"]
                    ],
                }
            )
        assert_blinded(links)
        write_jsonl(out / "public/source_links.jsonl", links)
        write_jsonl(out / "private/claims.jsonl", claim_rows, private=True)
        write_jsonl(out / "private/evidence_chunks.jsonl", chunk_rows, private=True)
        write_jsonl(out / "private/bundle_index.jsonl", bundle_rows, private=True)
        write_jsonl(
            out / "private/recovered_evidence_catalog.jsonl", evidence_catalog, private=True
        )
        write_jsonl(out / "private/review_packets.jsonl", packets, private=True)
        write_json(out / "private/packet_versions.json", versions, private=True)
        write_jsonl(out / "private/utility_candidates.jsonl", candidates, private=True)
        write_json(out / "private/utility_candidate_coverage.json", qa, private=True)
        write_json(out / "private/annotation_coverage.json", coverage, private=True)
        write_jsonl(out / "private/evaluator_case_index.jsonl", private_rows, private=True)
        for n, filename in (
            (1, "reviews_a.jsonl"),
            (2, "reviews_b.jsonl"),
            (3, "adjudications.jsonl"),
        ):
            directory = out / "reviewers" / f"reviewer_{n}"
            write_jsonl(directory / "packets.jsonl", packets, private=True)
            write_jsonl(directory / filename, reviewer_forms(packets), private=True)
            write_jsonl(directory / "utility_candidates.jsonl", candidates, private=True)
            write_jsonl(
                directory / "qa_reviews.jsonl",
                [qa_validation_template(c) for c in candidates],
                private=True,
            )
            write_json(
                directory / "instructions.json",
                {
                    "role": "independent_first_review"
                    if n == 1
                    else ("independent_second_review" if n == 2 else "disagreement_adjudicator"),
                    "review_status": "pending_real_human",
                    "guide": "reports/RECOVERY_20261029_REVIEW_GUIDE.md",
                    "instructions": [
                        "Review every actual record for the stated use; retain uncertainty",
                        "Do not access gold labels, targets or another initial review",
                        "Construction parents identify source locations, not authenticated authors",
                        "Reviewer 3 adjudicates only actual disagreements after initial reviews",
                        "QA candidates are safety-unverified and unvalidated; check usefulness too",
                        "Do not replace human votes with model outputs or fixture identities",
                    ],
                },
                private=True,
            )
        out.joinpath("reviewers").chmod(0o700)
        strata = Counter(
            (r["context_id"], r["stratum"]) for r in private_rows if r["review_candidate"]
        )
        eligible = Counter()
        valid_qa_sources = {
            c["contribution_id"]
            for c in candidates
            if c["candidate_id"] in coverage["safe_source_and_qa_validated_candidate_ids"]
        }
        by_pid = {r["contribution_id"]: r for r in private_rows}
        full_ids = {
            b["contribution_id"]
            for b in bundles
            if b["bundle_completeness"] == "complete_text_and_structural_provenance"
        }
        for a in coverage["approved_reviews"]:
            pid = a["contribution_id"]
            if pid not in full_ids:
                continue
            if a["Z_bundle"] == "unsafe" or pid in valid_qa_sources:
                r = by_pid[pid]
                eligible[(r["context_id"], r["stratum"], a["Z_bundle"])] += 1
        report = {
            "schema": "mpbench-recovery-annotation-v1",
            "date": "2026-10-29",
            "recovery": recovery,
            "review_packets": len(packets),
            "review_packet_records": sum(len(p["records"]) for p in packets),
            "annotation": {k: v for k, v in coverage.items() if k != "approved_reviews"},
            "qa_candidates": {k: v for k, v in qa.items() if k != "missing"},
            "review_population_by_original_stratum": {
                "/".join(k): v for k, v in sorted(strata.items())
            },
            "independently_eligible_by_stratum": {
                "/".join(k): v for k, v in sorted(eligible.items())
            },
            "pilot_ready": False,
            "pilot_groups_generated": 0,
            "blocked_by": [
                "Independent human safety/provenance reviews",
                "Human validation of candidate question usefulness, safety and answers",
                "Verified per-stratum capacity and final-group support/duplicate checks",
            ],
            "next_step": (
                "Assign independent humans to the versioned packets; import reviews, "
                "then check exact strata. Do not generate pilot groups yet."
            ),
            "network_calls": 0,
            "model_inference_calls": 0,
            "downloads": 0,
            "preserved_scope": (
                "Text and mechanical lineage do not certify safety, authenticated authorship, "
                "full graph state or answer equivalence."
            ),
        }
        if not recovery["verification"]["historical_verification_chain_passed"]:
            report["blocked_by"].insert(0, "Unresolved recovery/historical verification")
        write_json(out / "recovery_readiness_report.json", report)
        require(
            not any(
                m.startswith(("openai", "transformers", "sentence_transformers"))
                for m in sys.modules
            ),
            "Unexpected model/SDK import",
        )
        require(
            all(sha_file(Path(p)) == h for p, h in input_hashes.items()),
            "Input changed during offline recovery",
        )
        code_paths = sorted(Path(__file__).parent.glob("*.py"))
        code_paths += [
            Path("scripts/prepare_mpbench_recovery.py"),
            Path("src/ams/core/spans.py"),
            Path("src/ams/memory/evidence.py"),
            Path("src/ams/memory/typed.py"),
            Path("src/ams/memory/graph.py"),
            Path("src/ams/llm/types.py"),
        ]
        write_json(
            out / "recovery_manifest.json",
            {
                "schema": report["schema"],
                "input_sha256": input_hashes,
                "code_sha256": {str(p): sha_file(p) for p in code_paths},
                "files": {
                    str(p.relative_to(out)): sha_file(p)
                    for p in sorted(out.rglob("*"))
                    if p.is_file()
                },
                "network": "socket connections and DNS denied",
                "sqlite": "mode=ro&immutable=1; nonempty WAL refused",
                "historical_verification_scope": recovery["verification_scope"],
            },
        )
        return report


def import_reviews(prepared: Path, reviews: Path, out: Path, utility: Path | None = None) -> dict:
    require(not out.exists(), "Review result output exists; use a new version")
    validate_outputs(prepared)
    packets = read_jsonl(prepared / "private/review_packets.jsonl")
    if utility:
        um = json.loads((utility / "utility_manifest.json").read_text())
        require(
            um["source_manifest_sha256"] == sha_file(prepared / "recovery_manifest.json"),
            "Utility revision belongs to another recovery",
        )
        for name, expected in um["files"].items():
            require(sha_file(utility / name) == expected, "Utility revision modified")
    candidates = read_jsonl((utility or prepared) / "private/utility_candidates.jsonl")

    def optional(name):
        path = reviews / name
        return read_jsonl(path) if path.exists() else []

    result = review_coverage(
        packets,
        optional("reviews_a.jsonl"),
        optional("reviews_b.jsonl"),
        optional("adjudications.jsonl"),
        candidates,
        optional("qa_reviews.jsonl"),
    )
    write_json(out / "private/annotation_coverage.json", result, private=True)
    write_json(
        out / "review_import_manifest.json",
        {
            "source_manifest_sha256": sha_file(prepared / "recovery_manifest.json"),
            "review_file_sha256": {str(p): sha_file(p) for p in sorted(reviews.glob("*.jsonl"))},
            "pilot_ready": False,
            "pilot_groups_generated": 0,
        },
    )
    return result


def prepare_utility_revision(prepared: Path, out: Path) -> dict:
    """Reuse complete recovery; do not rerun chunk recovery or edit earlier drafts."""
    require(not out.exists(), "Utility revision exists; choose another output version")
    validate_outputs(prepared)
    packets = read_jsonl(prepared / "private/review_packets.jsonl")
    parents = {
        r["record_id"]: r.get("legacy_parent_artifact_id")
        for r in read_jsonl(prepared / "private/claims.jsonl")
    }
    candidates, coverage = draft_questions(packets, parents)
    write_jsonl(out / "private/utility_candidates.jsonl", candidates, private=True)
    write_json(out / "private/utility_coverage.json", coverage, private=True)
    for n in (1, 2, 3):
        directory = out / "reviewers" / f"reviewer_{n}"
        write_jsonl(directory / "utility_candidates.jsonl", candidates, private=True)
        write_jsonl(
            directory / "qa_reviews.jsonl",
            [qa_validation_template(c) for c in candidates],
            private=True,
        )
        write_json(
            directory / "instructions.json",
            {
                "packet_source": f"Use the original recovery reviewer_{n}/packets.jsonl",
                "status": "unvalidated; all sources safety-unverified",
                "claim_supported": "Pending human safety, utility and governance checks",
                "chunk_only": "Blocked by frozen external_evidence=false; not final utility",
                "guide": "reports/RECOVERY_20261029_REVIEW_GUIDE.md",
            },
            private=True,
        )
    out.joinpath("reviewers").chmod(0o700)
    write_json(
        out / "utility_manifest.json",
        {
            "source_manifest_sha256": sha_file(prepared / "recovery_manifest.json"),
            "code_sha256": {
                str(p): sha_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))
            },
            "reason": "Prefer claim support; frozen baseline excludes external chunks",
            "files": {
                str(p.relative_to(out)): sha_file(p) for p in sorted(out.rglob("*")) if p.is_file()
            },
            "pilot_ready": False,
            "pilot_groups_generated": 0,
        },
    )
    return {k: v for k, v in coverage.items() if k != "missing"}


def validate_outputs(out: Path) -> dict:
    manifest = json.loads((out / "recovery_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        p = out / name
        require(p.resolve().is_relative_to(out.resolve()), "Output manifest path traversal")
        require(sha_file(p) == expected, f"Output changed: {name}")
    for p in read_jsonl(out / "private/review_packets.jsonl"):
        assert_blinded(p)
        sources = {a["artifact_id"]: a for a in p["artifacts"]}
        for r in p["records"]:
            require(digest(r["text"]) == r["content_hash"], "Changed record text")
            for s in r["construction_source_spans"] + r["proposed_support_spans"]:
                require(
                    sources[s["artifact_id"]]["text"][s["start"] : s["end"]] == s["quote"],
                    "Broken exact source span",
                )
    return {
        "status": "passed",
        "files_checked": len(manifest["files"]),
        "pilot_ready": False,
        "scope": "Artifact integrity and structural annotation readiness",
    }
