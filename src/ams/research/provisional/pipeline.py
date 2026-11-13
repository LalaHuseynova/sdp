"""Versioned provisional Steps 4–6. No safety labels, audits or defense are executed."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ams.research.phase1 import check_prepared
from ams.research.phase1_annotations import review_template
from ams.research.phase1_blinding import keyed_id
from ams.research.phase1_common import digest, opaque, read_jsonl, require, write_json, write_jsonl
from ams.research.phase1_scenarios import SCENARIOS
from ams.research.provisional.annotations import prepare_annotations
from ams.research.provisional.episodes import (
    assignments,
    make_episode,
    recode,
    select_bags,
    source_pool,
    validate_episode,
    view,
)
from ams.research.provisional.questions import prepare_questions
from ams.research.recovery.annotation import qa_validation_template, review_coverage
from ams.research.recovery.offline import no_network, sha_file
from ams.research.recovery.pipeline import validate_outputs


def check_manifest(root: Path, manifest_name: str):
    manifest = json.loads((root / manifest_name).read_text())
    for name, expected in manifest["files"].items():
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()), "Manifest path escapes root")
        require(sha_file(path) == expected, f"Modified input/output: {name}")
    return manifest


def prepare(phase1: Path, recovered: Path, utility: Path, out: Path, config: Path) -> dict:
    require(not out.exists(), "Output exists; choose a fresh provisional version")
    with no_network():
        settings = json.loads(config.read_text())
        require(
            settings["schema"] == "mpbench-provisional-case-intent-v1"
            and settings["n_groups"] == 20
            and settings["cases_per_group"] == 32,
            "Unsupported provisional design",
        )
        require(
            settings["scenario_weights"] == {s: list(w) for s, w in SCENARIOS.items()},
            "Scenario weights differ from the declared design",
        )
        check_prepared(phase1)
        validate_outputs(recovered)
        um = check_manifest(utility, "utility_manifest.json")
        require(
            um["source_manifest_sha256"] == sha_file(recovered / "recovery_manifest.json"),
            "Question drafts belong to a different recovery",
        )
        input_paths = [
            phase1 / "preparation_manifest.json",
            recovered / "recovery_manifest.json",
            utility / "utility_manifest.json",
            config,
            Path("reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md"),
        ]
        inputs = {str(p): sha_file(p) for p in input_paths}
        rows = read_jsonl(phase1 / "private/case_index.jsonl")
        recovered_bundles = {
            r["contribution_id"]: r for r in read_jsonl(recovered / "private/bundle_index.jsonl")
        }
        # This is mechanical completeness only, never a safe/unsafe eligibility filter.
        candidates = [
            r
            for r in rows
            if r["review_candidate"]
            and recovered_bundles[r["contribution_id"]]["bundle_completeness"]
            == "complete_text_and_structural_provenance"
        ]
        original_packets = read_jsonl(recovered / "private/review_packets.jsonl")
        packets, hints, annotation_report = prepare_annotations(original_packets)
        claims = read_jsonl(recovered / "private/claims.jsonl")
        parents = {r["record_id"]: r.get("legacy_parent_artifact_id") for r in claims}
        roles = {r["record_id"]: r.get("legacy_parent_source_role") for r in claims}
        questions, question_report = prepare_questions(
            packets, parents, read_jsonl(utility / "private/utility_candidates.jsonl")
        )
        groups = read_jsonl(phase1 / "private/duplicate_groups.jsonl")
        bags = select_bags(candidates, groups)
        packet_index = {p["contribution_id"]: p for p in packets}
        catalog = {
            r["contribution_id"]: r for r in read_jsonl(phase1 / "public/candidate_inputs.jsonl")
        }
        key = bytes.fromhex(
            json.loads((phase1 / "private/identifier_key.json").read_text())["hex_key"]
        )
        require(len(key) == 32, "Bad private identifier key")
        old_by_pid = {p["contribution_id"]: p for p in original_packets}
        versions = [
            {
                "contribution_id": p["contribution_id"],
                "previous_packet_hash": digest(old_by_pid[p["contribution_id"]]),
                "current_packet_hash": digest(p),
                "old_votes_not_migrated": True,
            }
            for p in packets
        ]
        out.mkdir(parents=True)
        (out / ".gitignore").write_text(
            "# Generated drafts and private construction metadata\n*\n!.gitignore\n"
        )
        write_jsonl(out / "private/review_packets.jsonl", packets, private=True)
        write_jsonl(out / "private/automated_hints_NOT_HUMAN_LABELS.jsonl", hints, private=True)
        write_jsonl(out / "private/question_drafts.jsonl", questions, private=True)
        write_json(out / "private/packet_versions.json", versions, private=True)
        write_json(
            out / "private/annotation_preparation_report.json", annotation_report, private=True
        )
        write_json(out / "private/question_preparation_report.json", question_report, private=True)
        write_jsonl(out / "private/evaluator_case_index.jsonl", rows, private=True)
        for n, form in ((1, "reviews_a.jsonl"), (2, "reviews_b.jsonl"), (3, "adjudications.jsonl")):
            directory = out / "reviewers" / f"reviewer_{n}"
            write_jsonl(directory / "packets.jsonl", packets, private=True)
            write_jsonl(directory / form, [review_template(p) for p in packets], private=True)
            write_jsonl(directory / "question_drafts.jsonl", questions, private=True)
            write_jsonl(
                directory / "qa_reviews.jsonl",
                [qa_validation_template(c) for c in questions],
                private=True,
            )
            write_json(
                directory / "instructions.json",
                {
                    "status": "pending_genuine_human_review",
                    "role": n,
                    "guide": "reports/PROVISIONAL_20261029_GUIDE.md",
                    "automated_warning_hints_included": False,
                    "do_not_view": [
                        "evaluator indexes",
                        "automated warning file",
                        "peer initial votes",
                    ],
                    "adjudicator_only_after_real_disagreements": n == 3,
                },
                private=True,
            )
        out.joinpath("reviewers").chmod(0o700)
        episode_index, selection_index = [], []
        for bi, bag in enumerate(bags):
            bid = f"D{bi:02d}"
            token = keyed_id(opaque("g", "provisional", bid), key)
            pool = source_pool(bag, catalog, packet_index, roles)
            public_pool = recode(pool, key)
            write_json(out / "public" / token / "inputs.json", public_pool)
            selected_ids = {r["contribution_id"] for r in bag}
            jobs = [c for c in questions if c["contribution_id"] in selected_ids]
            write_jsonl(out / "private" / token / "pending_question_jobs.jsonl", jobs, private=True)
            selection_index.append(
                {
                    "bag_id": bid,
                    "bag_token": token,
                    "split_intent": "development"
                    if bi < 8
                    else "reserved_unvalidated_not_locked_test",
                    "source_ids": sorted(selected_ids),
                    "component_ids": sorted(r["group_id"] for r in bag),
                    "case_intent_counts": dict(Counter(r["stratum"] for r in bag)),
                    "original_case_keys": sorted(r["original_case_key"] for r in bag),
                    "safety_balance": "unknown; not a 16-safe/16-unsafe claim",
                }
            )
            for scenario in SCENARIOS:
                mapping, hidden = assignments(bag, bid, scenario)
                episode = make_episode(bag, mapping, hidden, pool, bid, key)
                episode_token = keyed_id(opaque("ep", "provisional", bid, scenario), key)
                public_part = {
                    k: episode[k] for k in ("overlay", "events", "shared_arm_inputs", "status")
                }
                write_json(out / "public" / token / f"{episode_token}.json", public_part)
                write_json(
                    out / "private" / token / f"{episode_token}.json",
                    episode["private"],
                    private=True,
                )
                episode_index.append(
                    {
                        "bag_token": token,
                        "episode_token": episode_token,
                        "bag_id": bid,
                        "scenario": scenario,
                        "shared_arm_inputs": episode["shared_arm_inputs"],
                        "public_file": f"public/{token}/{episode_token}.json",
                        "private_file": f"private/{token}/{episode_token}.json",
                    }
                )
        write_json(out / "private/group_selections.json", selection_index, private=True)
        write_json(out / "private/episode_index.json", episode_index, private=True)
        report = {
            "schema": settings["schema"],
            "status": "provisional_development_data_prepared",
            "provisional_groups_generated": len(bags),
            "source_cases_selected": 32 * len(bags),
            "metadata_overlays_generated": len(episode_index),
            "cases_per_group": 32,
            "per_group_case_labels": {"attack_input": 20, "benign_input": 12},
            "per_context_strata": {
                "attack_input": 10,
                "explicit_benign": 1,
                "suggestive_benign": 5,
            },
            "all_case_memory_safety": "unknown",
            "human_verified_labels": 0,
            "human_validated_questions": 0,
            "validated_safety_pilot_groups_generated": 0,
            "scientific_pilot_ready": False,
            "scientific_evaluation_allowed": False,
            "actual_completed_audits": 0,
            "planned_audit_requests_per_overlay": 5,
            "original_query_requests_per_overlay": 27,
            "annotation_preparation": annotation_report,
            "question_preparation": {
                k: v for k, v in question_report.items() if k != "mechanically_rejected"
            },
            "case_selection_uses_qa_quality_or_automated_warnings": False,
            "duplicate_component_reuse": 0,
            "api_calls": 0,
            "model_inference_calls": 0,
            "defense_implemented": False,
            "experimental_results_generated": False,
            "original_protocol_modified": False,
            "next_step": (
                "Human review can follow. Recheck and rebuild cohorts before treating these "
                "development groups as the original Z-balanced scientific pilot."
            ),
        }
        write_json(out / "preparation_report.json", report)
        require(
            all(sha_file(Path(p)) == h for p, h in inputs.items()),
            "Inputs changed during preparation",
        )
        paths = sorted(Path(__file__).parent.glob("*.py")) + [
            config,
            Path("scripts/prepare_mpbench_provisional.py"),
        ]
        write_json(
            out / "provisional_manifest.json",
            {
                "schema": report["schema"],
                "input_sha256": inputs,
                "code_sha256": {str(p): sha_file(p) for p in paths},
                "files": {
                    str(p.relative_to(out)): sha_file(p)
                    for p in sorted(out.rglob("*"))
                    if p.is_file()
                },
                "unverified_development_only": True,
            },
        )
        return report


def validate(root: Path) -> dict:
    manifest = check_manifest(root, "provisional_manifest.json")
    selections = json.loads((root / "private/group_selections.json").read_text())
    index = json.loads((root / "private/episode_index.json").read_text())
    components = [g for s in selections for g in s["component_ids"]]
    require(len(components) == len(set(components)) == 640, "Template overlap across bags")
    for row in index:
        public = json.loads((root / row["public_file"]).read_text())
        private = json.loads((root / row["private_file"]).read_text())
        pool = json.loads((root / "public" / row["bag_token"] / "inputs.json").read_text())
        episode = {**public, "private": private}
        validate_episode(episode, pool)
        require(view(pool, episode, 0)["visible_contributions"] == {}, "Future input exposure")
        require(not view(pool, episode, 38)["revealed_audit_results"], "Invented audit result")
    return {
        "status": "passed",
        "files_checked": len(manifest["files"]),
        "groups_checked": len(selections),
        "overlays_checked": len(index),
        "human_verified_labels": 0,
        "scientific_pilot_ready": False,
    }


def import_humans(prepared: Path, reviews: Path, out: Path) -> dict:
    require(not out.exists(), "Review output exists; use a new version")
    validate(prepared)
    packets = read_jsonl(prepared / "private/review_packets.jsonl")
    questions = read_jsonl(prepared / "private/question_drafts.jsonl")

    def read(name):
        p = reviews / name
        return read_jsonl(p) if p.exists() else []

    result = review_coverage(
        packets,
        read("reviews_a.jsonl"),
        read("reviews_b.jsonl"),
        read("adjudications.jsonl"),
        questions,
        read("qa_reviews.jsonl"),
    )
    write_json(out / "private/human_review_coverage.json", result, private=True)
    write_json(
        out / "import_manifest.json",
        {
            "source_manifest_sha256": sha_file(prepared / "provisional_manifest.json"),
            "pilot_automatically_unlocked": False,
            "review_file_sha256": {str(p): sha_file(p) for p in reviews.glob("*.jsonl")},
        },
    )
    return result
