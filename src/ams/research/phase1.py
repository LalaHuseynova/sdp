"""Guarded Phase 1 preparation commands; intentionally no LLM dependencies."""

from __future__ import annotations

import json
import platform
import secrets
from collections import Counter
from pathlib import Path

from ams.research.phase1_annotations import (
    eligible_records,
    review_template,
    utility_template,
)
from ams.research.phase1_blinding import blind_episode, keyed_id
from ams.research.phase1_common import (
    PROTOCOL_HASH,
    SCHEMA,
    PreparationError,
    digest,
    file_hash,
    opaque,
    read_jsonl,
    require,
    write_json,
    write_jsonl,
)
from ams.research.phase1_data import (
    catalogs,
    duplicate_groups,
    frozen_claims,
    import_evidence_catalog,
    inventory,
    load_corpus,
)
from ams.research.phase1_scenarios import (
    SCENARIOS,
    assert_public,
    make_episode,
    select_bags,
    validate_public_contribution,
)


def implementation_fingerprints() -> dict:
    repo = Path(__file__).resolve().parents[3]
    paths = sorted((repo / "src/ams/research").glob("*.py"))
    paths += [
        repo / "scripts/prepare_mpbench_phase1.py",
        repo / "configs/research/mpbench_phase1.json",
    ]
    return {str(p.relative_to(repo)): file_hash(p) for p in paths}


def check_prepared(prepared: Path) -> dict:
    manifest = json.loads((prepared / "preparation_manifest.json").read_text())
    require(manifest.get("schema") == SCHEMA, "Unknown preparation schema")
    require(manifest["protocol_sha256"] == PROTOCOL_HASH, "Wrong protocol preparation")
    require(
        manifest.get("implementation_sha256") == implementation_fingerprints(),
        "Preparation code/config changed; regenerate and review annotations before reuse",
    )
    for name, expected in manifest["files"].items():
        path = prepared / name
        require(path.resolve().is_relative_to(prepared.resolve()), "Manifest path escapes output")
        require(file_hash(path) == expected, f"Changed preparation artifact: {name}")
    return manifest


def prepare(
    root: Path,
    journal: Path,
    protocol: Path,
    out: Path,
    identifier_key: Path | None = None,
    evidence_catalog: Path | None = None,
) -> dict:
    require(not out.exists(), "Preparation output already exists; choose a fresh directory")
    require(
        file_hash(protocol) == PROTOCOL_HASH, "Protocol changed; review/version before building"
    )
    cases, raw_hashes = load_corpus(root)
    # This key affects names only, never seed-based sampling, weights or chronology.
    key_data = (
        json.loads(identifier_key.read_text())
        if identifier_key
        else {"hex_key": secrets.token_hex(32), "purpose": "public identifier blinding only"}
    )
    require(len(bytes.fromhex(key_data["hex_key"])) == 32, "Invalid identifier key")
    claims, extraction = frozen_claims(journal, {c.cid for c in cases})
    if evidence_catalog is not None:
        extraction.update(import_evidence_catalog(evidence_catalog, cases, claims))
    groups, group_report = duplicate_groups(cases)
    public, private, packets = catalogs(cases, claims, groups)
    assert_public(public)
    for row in public:
        validate_public_contribution(row)
    capacity = {}
    for context in ("email", "file_and_doc"):
        for label in ("attack", "explicit_benign", "suggestive_benign"):
            rows = [
                r
                for r in private
                if r["review_candidate"] and r["context_id"] == context and r["stratum"] == label
            ]
            capacity[f"{context}/{label}"] = {
                "cases": len(rows),
                "nonempty_frozen_bundles": sum(bool(r["records"]) for r in rows),
                "distinct_template_groups": len({r["group_id"] for r in rows}),
                "nonempty_template_groups": len({r["group_id"] for r in rows if r["records"]}),
                "verified_Z_unsafe": 0,
                "verified_Z_safe": 0,
            }
    report = {
        "schema": SCHEMA,
        "status": "not_ready_missing_independent_annotations",
        "pilot_ready": False,
        "real_episodes_generated": 0,
        "protocol_sha256": file_hash(protocol),
        "raw_sha256": raw_hashes,
        "frozen_extraction": extraction,
        "review_bundle_coverage": (
            "claims_and_evidence"
            if extraction["chunk_records_available"]
            else "claims_only_incomplete_for_pilot"
        ),
        "inventory": inventory(cases),
        "review_candidates": len(packets),
        "independently_reviewed_Z_bundles": 0,
        "review_candidate_claims": sum(len(p["records"]) for p in packets),
        "empty_review_candidate_bundles": sum(not p["records"] for p in packets),
        "unverified_sampling_capacity": capacity,
        "source_links_independently_verified": 0,
        "validated_grounded_questions": 0,
        "group_count": len(group_report),
        "multi_case_groups": sum(g["size"] > 1 for g in group_report),
        "groups_requiring_manual_review": sum(g["manual_review_required"] for g in group_report),
        "planned_pilot": {
            "bags": 20,
            "development_bags": 8,
            "locked_pilot_bags": 12,
            "cases_per_bag": 32,
            "Z_unsafe_per_bag": 16,
            "Z_safe_per_bag": 16,
            "Y_attack_per_bag": 20,
            "Y_benign_per_bag": 12,
            "explicit_per_bag": 2,
            "suggestive_per_bag": 10,
            "required_per_context_all_bags": {
                "attack_Z_unsafe": 160,
                "attack_Z_safe": 40,
                "explicit_Z_safe": 20,
                "suggestive_Z_safe": 100,
            },
        },
        "missing": [
            *(
                []
                if extraction["chunk_records_available"]
                else [
                    "Actual frozen/cached evidence-chunk export and independent chunk/use reviews"
                ]
            ),
            "Two independent blinded record/use reviews and source-span maps",
            "Third-reviewer adjudication of disagreements",
            "Validated source-grounded QA for each selected safe bundle",
            "Final-bag unique/disambiguated QA support review",
            "Manual review of oversized/generic duplicate components",
        ],
        "notes": [
            "Raw case labels establish sampling capacity only, not memory safety",
            "Frozen claims lack authenticated source-span maps; chunks were not serialized",
            "No real annotated pilot or efficacy result has been produced",
        ],
    }
    write_jsonl(out / "public/candidate_inputs.jsonl", public)
    write_json(out / "private/identifier_key.json", key_data, private=True)
    write_jsonl(out / "private/case_index.jsonl", private, private=True)
    write_jsonl(out / "private/duplicate_groups.jsonl", group_report, private=True)
    write_jsonl(out / "private/blinded_packets.jsonl", packets, private=True)
    for reviewer in ("a", "b"):
        write_jsonl(
            out / f"private/reviewer_{reviewer}_template.jsonl",
            [review_template(p) for p in packets],
            private=True,
        )
    write_jsonl(out / "private/adjudications_template.jsonl", [], private=True)
    write_jsonl(
        out / "private/utility_template.jsonl", [utility_template(p) for p in packets], private=True
    )
    write_jsonl(out / "private/bag_validations_template.jsonl", [], private=True)
    write_json(
        out / "private/group_review_template.json",
        {"approved_group_ids": [], "reviewer_id": "", "status": "pending"},
        private=True,
    )
    write_json(out / "composition_report.json", report)
    manifest = {
        "schema": SCHEMA,
        "protocol_sha256": PROTOCOL_HASH,
        "implementation_sha256": implementation_fingerprints(),
        "raw_sha256": raw_hashes,
        "frozen_journal_sha256": extraction["journal_sha256"],
        "frozen_chunk_catalog_available": extraction["chunk_records_available"],
        "python": platform.python_version(),
        "prng": "CPython random.Random MT19937",
        "seed_encoding": "8-byte big-endian UTF-8 byte length per component; SHA256 first64",
        "files": {
            str(p.relative_to(out)): file_hash(p) for p in sorted(out.rglob("*")) if p.is_file()
        },
    }
    write_json(out / "preparation_manifest.json", manifest)
    return report


def validate_preparation(out: Path, root: Path) -> dict:
    manifest = check_prepared(out)
    _, hashes = load_corpus(root)
    require(hashes == manifest["raw_sha256"], "Raw inputs changed")
    public = read_jsonl(out / "public/candidate_inputs.jsonl")
    assert_public(public)
    require(
        len(public) == len({r["contribution_id"] for r in public}) == 6240,
        "Public contribution count/ID error",
    )
    private = read_jsonl(out / "private/case_index.jsonl")
    require(
        {r["contribution_id"] for r in private} == {r["contribution_id"] for r in public},
        "Public/private case join mismatch",
    )
    by_id = {r["contribution_id"]: r for r in public}
    for row in public:
        validate_public_contribution(row)
    for p in read_jsonl(out / "private/blinded_packets.jsonl"):
        require(
            set(p)
            == {
                "contribution_id",
                "context_id",
                "use_id",
                "intended_use",
                "task",
                "artifacts",
                "records",
            },
            "Unexpected blinded packet field",
        )
        require(
            p["artifacts"] == by_id[p["contribution_id"]]["artifacts"], "Packet source mismatch"
        )
        for r in p["records"]:
            require(
                set(r) == {"record_id", "record_kind", "text", "content_hash"},
                "Unexpected/unblinded memory metadata",
            )
    return {
        "status": "passed",
        "files_checked": len(manifest["files"]),
        "inputs_checked": len(public),
        "raw_sha256": hashes,
        "pilot_ready": False,
        "reason": "Validation does not create independent annotations",
    }


def export_review(prepared: Path, out: Path, slot: str) -> dict:
    """Create a reviewer folder without case labels, targets, legacy IDs or peers' votes."""
    require(slot in {"a", "b"}, "Reviewer slot must be a or b")
    require(not out.exists(), "Review export already exists; use a fresh directory")
    manifest = check_prepared(prepared)
    name = "private/blinded_packets.jsonl"
    require(file_hash(prepared / name) == manifest["files"][name], "Changed review packets")
    packets = read_jsonl(prepared / name)
    write_jsonl(out / "packets.jsonl", packets, private=True)
    write_jsonl(out / f"reviews_{slot}.jsonl", [review_template(p) for p in packets], private=True)
    write_jsonl(out / "utilities.jsonl", [utility_template(p) for p in packets], private=True)
    write_json(
        out / "instructions.json",
        {
            "status": "blank_review_workflow",
            "packet_count": len(packets),
            "instructions": [
                "Use a real reviewer ID; attest independent human review only after reviewing",
                "Do not access the private case index, targets, labels or other reviewer votes",
                "Read reports/PHASE1_ANNOTATION_GUIDE.md for the record/use and span rubric",
                "Blank or uncertain entries never establish a safe bundle",
            ],
        },
        private=True,
    )
    return {
        "status": "blank_review_exported",
        "review_candidates": len(packets),
        "pilot_ready": False,
    }


def build_pilot(prepared: Path, annotations: Path, out: Path) -> dict:
    """Build only from validated human reviews. Never bootstrap Z from Y_case."""
    require(not out.exists(), "Build output already exists; use a fresh directory")
    # Verify the immutable preparation before accepting separately stored reviews.
    manifest = check_prepared(prepared)
    packets = read_jsonl(prepared / "private/blinded_packets.jsonl")
    private = read_jsonl(prepared / "private/case_index.jsonl")
    public = {
        r["contribution_id"]: r for r in read_jsonl(prepared / "public/candidate_inputs.jsonl")
    }
    group_rows = read_jsonl(prepared / "private/duplicate_groups.jsonl")

    def optional(name):
        path = annotations / name
        return read_jsonl(path) if path.exists() else []

    eligible, stats = eligible_records(
        private,
        packets,
        optional("reviews_a.jsonl"),
        optional("reviews_b.jsonl"),
        optional("adjudications.jsonl"),
        optional("utilities.jsonl"),
    )
    counts = Counter((r["context_id"], r["stratum"], r["Z_bundle"]) for r in eligible)
    status = {
        "schema": SCHEMA,
        "pilot_ready": False,
        "annotation_status": stats,
        "eligible_counts": {"/".join(k): v for k, v in sorted(counts.items())},
        "real_episodes_generated": 0,
    }
    group_path = annotations / "group_review.json"
    approved_groups = set()
    if group_path.exists():
        gr = json.loads(group_path.read_text())
        require(
            gr.get("status") == "complete" and gr.get("reviewer_id"),
            "Incomplete duplicate-group review",
        )
        approved_groups = set(gr.get("approved_group_ids", []))
    large = {r["group_id"] for r in group_rows if r["manual_review_required"]}
    require(approved_groups <= large, "Unknown oversized group approval")
    try:
        bags = select_bags(eligible, approved_large_groups=approved_groups, large_groups=large)
    except PreparationError as e:
        status.update({"status": "not_ready", "blocking_reason": str(e)})
        write_json(out / "readiness_report.json", status)
        return status
    if not manifest["frozen_chunk_catalog_available"]:
        status.update(
            {
                "status": "not_ready",
                "blocking_reason": (
                    "Evidence chunks are missing; claim-only reviews "
                    "cannot certify complete memory bundles."
                ),
            }
        )
        write_json(out / "readiness_report.json", status)
        return status
    # Freeze proposed selection for a final per-bag QA uniqueness check before release.
    selections = [
        {
            "bag_id": f"{i:02d}",
            "contribution_ids": sorted(r["contribution_id"] for r in bag),
            "selection_hash": digest(sorted(r["contribution_id"] for r in bag)),
        }
        for i, bag in enumerate(bags)
    ]
    validations = optional("bag_validations.jsonl")
    require(len({r["bag_id"] for r in validations}) == len(validations), "Duplicate bag review")
    valid = {r["bag_id"]: r for r in validations}
    missing = []
    for selection in selections:
        v = valid.get(selection["bag_id"], {})
        if not (
            v.get("status") == "complete"
            and v.get("validator_id")
            and v.get("selection_hash") == selection["selection_hash"]
            and v.get("all_grounded_support_unique_or_disambiguated") is True
        ):
            missing.append(selection["bag_id"])
    if missing:
        status.update(
            {
                "status": "not_ready",
                "blocking_reason": "Final-bag QA review missing",
                "bags_missing_validation": missing,
            }
        )
        write_json(out / "private/proposed_bag_selections.json", selections, private=True)
        write_json(out / "readiness_report.json", status)
        return status
    packet_index = {r["contribution_id"]: r for r in packets}
    key = bytes.fromhex(
        json.loads((prepared / "private/identifier_key.json").read_text())["hex_key"]
    )
    arm_references = []
    for index, bag in enumerate(bags):
        bid = f"{index:02d}"
        for scenario in SCENARIOS:
            for budget in (1, 3, 5):
                for fixed in (False, True):
                    episode = blind_episode(
                        make_episode(bag, public, packet_index, bid, scenario, budget, fixed), key
                    )
                    token = keyed_id(opaque("episode", bid, scenario, budget, fixed), key)
                    write_json(out / "public" / token / "inputs.json", episode["public_inputs"])
                    write_json(out / "private" / token / "episode.json", episode, private=True)
                    arm_references.append(
                        {"episode_token": token, "shared_arm_inputs": episode["shared_arm_inputs"]}
                    )
    status.update(
        {
            "status": "offline_metadata_ready",
            "pilot_ready": True,
            "real_episodes_generated": len(arm_references),
            "note": "Prepared schedules only; no defense or experiment executed",
        }
    )
    write_json(out / "private/shared_arm_references.json", arm_references, private=True)
    write_json(out / "readiness_report.json", status)
    return status
