"""Post-review data freeze and evaluator projection; never performs reviews/runs."""

from __future__ import annotations

import copy
import json
import tempfile
from collections import Counter
from pathlib import Path

from ams.research import comparison, focused_review
from ams.research.dynamic.models import canonical, check, digest, name
from ams.research.dynamic.policies import Policy
from ams.research.execution.session import new_json
from ams.research.llm_followup.pipeline import verify_results
from ams.research.llm_review.validation import QA_KEYS
from ams.research.pilot_finish import selection
from ams.research.pilot_finish.utility import collect, verified_proposals
from ams.research.recovery.offline import sha_file

SCHEMA = "AI_source_safety_scoped_QA_exploratory_cohort_v1"
SOURCE_BASIS = "AI_Z_hat_not_human_Z"


def dependencies(paths):
    return {str(p.resolve()): sha_file(p) for p in paths}


def verify_dependencies(values):
    for n, h in values.items():
        check(Path(n).is_file() and sha_file(Path(n)) == h, "Source/review dependency changed")


def verify_readiness(prepared, ready):
    """Verify the accepted review receipt AND preserve the original source votes."""
    manifest = focused_review.read(ready/"review_readiness_manifest.json")
    check(manifest["execution_enabled"] is False, "Readiness cannot enable execution")
    focused_review.verify_files(ready, manifest["files"])
    verify_dependencies(manifest["dependencies"])
    result = focused_review.read(ready/"review_readiness.json")
    check(result["status"] == "scoped_QA_readiness_only"
          and result["exploratory_data_ready"] is True
          and result["accepted_human_QA_candidates"] == result["human_validated_questions"] == 1
          and result["human_verified_labels"] == 0 and result["human_validated_pilot_ready"] is False
          and result["source_label_basis"] == "AI_only_not_human_Z"
          and result["QA_basis"] == "mixed_AI_and_scoped_human"
          and result["automatic_freeze_enabled"] is result["defense_execution_enabled"] is False,
          "Complete selection and an accepted scoped QA review are required before freezing")
    imports = [Path(p).parent for p in manifest["dependencies"] if Path(p).name == "review_import.json"]
    check(len(imports) == 1, "Exactly one scoped review receipt is required")
    accepted = focused_review.import_result(imports[0])
    check(accepted["accepted_human_QA_candidates"] == 1
          and accepted["status"] == "human_QA_accepted_by_coordinator_attestation",
          "Pending/rejected QA is not an acceptance")
    q = accepted["candidate"]
    check(digest(q) == accepted["candidate_hash"], "Accepted question version changed")
    parents = sorted({Path(p).parent for p in manifest["dependencies"] if Path(p).name == "results_manifest.json"})
    check(parents, "Original AI source views are required")
    rows = [r for p in parents for r in verified_proposals(p)]
    expected = {"contribution_id": q["contribution_id"], "annotation_source": "human_QA_only",
                "records": [], "questions": [{"candidate_id": q["candidate_id"], **{k: True for k in QA_KEYS},
                    "rationale": "Genuine two-pass declarations and coordinator attestation; QA scope only."}],
                "candidate_question": {**q, "human_validated": True, "eligible_as_gold": False,
                                       "validation_status": "human_QA_source_safety_still_AI"},
                "eligible_as_gold": False, "can_update_live_trust": False}
    packets, source_records, _, _, source_bundles = collect(parents, prepared)
    check(all(not r["records"] or r.get("packet_hash") == digest(packets[r["contribution_id"]])
              for r in rows), "Source assessment packet changed")
    for p in packets.values():
        for record in p["records"]:
            check(record["record_id"] in source_records
                  and record["content_hash"] == digest(record["text"])
                  and source_records[record["record_id"]]["content_hash"] == record["content_hash"],
                  "Source assessment refers to a different memory version")
        for artifact in p["artifacts"]:
            check(artifact["content_hash"] == digest(artifact["text"]), "Source artifact text/hash changed")
    check(q["contribution_id"] in packets
          and digest(packets[q["contribution_id"]]) == accepted["packet_hash"], "Scoped review belongs to another packet")
    expected["use_id"] = packets[q["contribution_id"]]["use_id"]
    view = ready/"selection_view"
    verify_results(view)
    actual = list(verified_proposals(view))
    # Compare the multiset because original parent views may have been supplied
    # in a different order. Every original record vote remains byte-for-byte data.
    check(Counter(canonical(r) for r in actual) == Counter(canonical(r) for r in [*rows, expected]),
          "Original source votes or the scoped QA decision changed")
    with tempfile.TemporaryDirectory(prefix="scoped-readiness-check-") as d:
        recomputed = selection.readiness(prepared, [view], Path(d)/"selector")
    for field in ["selected_ids", "final_questions", "strata", "AI_bundle_counts", "uniqueness_failures",
                  "exploratory_data_ready", "reviewed_development_inputs", "memory_records_expected"]:
        check(recomputed[field] == result[field], "Selection/labels changed after review")
    check(len(result["selected_ids"]) == len(set(result["selected_ids"])) == 32,
          "Expected the unchanged 32-case selection")
    check(Counter(source_bundles[p]["AI_label"] for p in result["selected_ids"])
          == {"unsafe": 16, "safe_for_use": 16}, "Declared AI bundle balance changed")
    return result, accepted, manifest, recomputed


def freeze(prepared, ready, out):
    check(not out.exists(), "Refuse to overwrite an existing cohort")
    result, accepted, receipt, _ = verify_readiness(prepared, ready)
    view = ready/"selection_view"
    # The unchanged producer is reused for slots, weighted sampling, IDs, event
    # order, root/audits and questions. Its hardcoded QA bookkeeping is discarded;
    # all permanent metadata below is derived from the accepted review receipt.
    with tempfile.TemporaryDirectory(prefix="scoped-cohort-construction-") as d:
        staging = Path(d)
        inputs = staging/"constructor_input"; inputs.mkdir()
        new_json(inputs/"readiness.json", result)
        new_json(inputs/"manifest.json", {
            "files": {"readiness.json": sha_file(inputs/"readiness.json")},
            "dependencies": {**receipt["dependencies"], **dependencies([
                ready/"review_readiness.json", ready/"review_readiness_manifest.json",
                view/"automated_proposals.jsonl", view/"results_manifest.json",
                *[prepared/"private"/n for n in ["review_packets.jsonl", "question_drafts.jsonl", "evaluator_case_index.jsonl"]]])}})
        generated = staging/"generated"
        selection.freeze_exploratory(prepared, [view], inputs, generated)
        base = focused_review.read(generated/"manifest.json")
        focused_review.verify_files(generated, base["files"])
        selected_human = sorted(q["candidate_id"] for q in result["final_questions"].values()
                                if q["candidate_id"] == accepted["candidate_id"])
        check(len(selected_human) <= 1, "Duplicate human QA candidate")
        final_payloads = {n: focused_review.read(generated/n) for n in base["files"]}
        final_payloads["private/selected_questions.json"] = result["final_questions"]
        selected = final_payloads["private/selection.json"]
        selected.update(label_basis=SOURCE_BASIS, human_verified_labels=0,
                        human_validated_questions=len(selected_human),
                        question_validation_basis="mixed_AI_and_scoped_human" if selected_human else "AI_only",
                        defense_execution_enabled=False)
        final_payloads["private/annotation_provenance.json"] = {
            "source_safety_basis": SOURCE_BASIS, "human_verified_source_bundles": 0,
            "human_verified_memory_labels": 0, "accepted_human_QA_in_review_pool": 1,
            "selected_human_QA_candidate_ids": selected_human,
            "selected_human_QA_questions": len(selected_human),
            "selected_AI_QA_questions": len(result["final_questions"])-len(selected_human),
            "review_scope": accepted["assessment_scope"],
            "review_record_hashes": accepted["review_record_hashes"],
            "accepted_review_hash": digest(accepted),
            "identity_authentication": accepted["identity_authentication"],
            "reviews_are_not_additional_source_incidents": True,
            "source_votes_changed": 0, "can_update_live_trust": False}
    deps = {**receipt["dependencies"], **dependencies([
        ready/"review_readiness.json", ready/"review_readiness_manifest.json",
        view/"results_manifest.json", view/"automated_proposals.jsonl",
        *[prepared/"private"/n for n in ["review_packets.jsonl", "question_drafts.jsonl", "evaluator_case_index.jsonl"]],
        Path(__file__), Path(selection.__file__), Path(focused_review.__file__)])}
    out.mkdir(parents=True, mode=0o700)
    (out/"private").mkdir(mode=0o700)
    (out/"public").mkdir(mode=0o700)
    for n, payload in final_payloads.items():
        new_json(out/n, payload)
    files = {n: sha_file(out/n) for n in final_payloads}
    new_json(out/"manifest.json", {"schema": SCHEMA, "files": files, "hash": digest(files),
                                  "dependencies": deps, "scientific_human_validated": False,
                                  "execution_enabled": False})
    return verify(out)


def verify(root):
    manifest = focused_review.read(root/"manifest.json")
    check(manifest["schema"] == SCHEMA and manifest["execution_enabled"] is False
          and manifest["scientific_human_validated"] is False
          and digest(manifest["files"]) == manifest["hash"], "Wrong/changed scoped cohort")
    focused_review.verify_files(root, manifest["files"])
    verify_dependencies(manifest["dependencies"])
    selected = focused_review.read(root/"private/selection.json")
    provenance = focused_review.read(root/"private/annotation_provenance.json")
    questions = focused_review.read(root/"private/selected_questions.json")
    check(selected["label_basis"] == provenance["source_safety_basis"] == SOURCE_BASIS
          and selected["human_verified_labels"] == provenance["human_verified_memory_labels"] == 0
          and provenance["human_verified_source_bundles"] == 0
          and selected["defense_execution_enabled"] is provenance["can_update_live_trust"] is False,
          "Scoped QA was promoted into source safety or execution")
    check(selected["human_validated_questions"] == provenance["selected_human_QA_questions"]
          == len(provenance["selected_human_QA_candidate_ids"])
          and provenance["selected_AI_QA_questions"]+selected["human_validated_questions"] == 16,
          "Lost or inflated question-review provenance")
    check(len(questions) == 16 and len({q["candidate_id"] for q in questions.values()}) == 16
          and all(q["contribution_id"] == pid and q["support_record_kind"] == "claim"
                  and q.get("eligible_as_gold", False) is False for pid, q in questions.items())
          and sorted(q["candidate_id"] for q in questions.values() if q.get("human_validated") is True)
          == provenance["selected_human_QA_candidate_ids"], "Question catalog/review provenance changed")
    ids = selected["source_ids"]
    check(len(ids) == len(set(ids)) == 32, "Wrong source cohort")
    check(set(questions) <= set(ids), "Question catalog refers to a foreign contribution")
    orders, roots, episodes = [], [], []
    for file in sorted((root/"public").glob("*.json")):
        public = focused_review.read(file)
        private = focused_review.read(root/"private"/file.name)
        ingests = [e for e in public["events"] if e["event"] == "ingest"]
        check(len(ingests) == 32 and {e["contribution_id"] for e in ingests} == set(ids)
              and Counter(e["context_id"] for e in ingests) == {"email": 16, "file_and_doc": 16}
              and set(Counter(e["batch_id"] for e in ingests).values()) == {4}, "Changed slot composition")
        check(private["arms"] == ["R", "C", "M", "S"] and private["feedback_budget_each"] == 5
              and private["arms_receive_identical_data_and_feedback"] is True, "Unmatched policies/resources")
        reserved = private["reserved_audit_ids"]
        check(len(reserved) == len(set(reserved)) == 5
              and [a["contribution_id"] for a in private["audits"]] == reserved
              and len({a["ticket_id"] for a in private["audits"]}) == 5
              and all(a["annotation_source"] == "llm" and a["independently_verified"] is False
                      for a in private["audits"]), "Review created or changed audit evidence")
        original = [e["contribution_id"] for e in public["events"] if e["event"] == "query"]
        utility = [e["contribution_id"] for e in public["events"] if e["event"] == "utility_query"]
        check(original == private["original_probe_ids"] and len(original) == len(set(original)) == 27
              and not set(original)&set(reserved) and set(original)|set(reserved) == set(ids)
              and utility == private["utility_probe_ids"] and len(utility) == len(set(utility))
              and set(utility) <= set(original), "Probe cohort/order changed")
        check(set(private["utility_references"]) == set(utility)
              and all(private["utility_references"][pid] == questions[pid] for pid in utility),
              "Utility reference changed from the selected question catalog")
        check(not {"AI_verdict", "profiles", "gold_cases", "utility_references", "review_record_hashes"}&set(public),
              "Private annotation fields in public episode")
        orders.append([e["contribution_id"] for e in ingests]); roots.append(reserved[0])
        episodes.append(private["scenario"])
    check(len(orders) == 3 and orders[0] == orders[1] == orders[2] and len(set(roots)) == 1
          and set(episodes) == {"strong_localized", "strong_distributed", "uninformative"},
          "Changed regimes/common input order/root")
    return {"status": "scoped_exploratory_cohort_verified", "contributions": 32, "overlays": 3,
            "source_safety_basis": SOURCE_BASIS, "human_verified_memory_labels": 0,
            "selected_human_QA_questions": selected["human_validated_questions"],
            "scientific_human_validated": False, "execution_enabled": False}


def prepare_analysis(cohort, case_index, group_id, out):
    """New provenance-aware projection into the existing saved-result analyzer."""
    check(not out.exists(), "Refuse to overwrite an analysis plan")
    verify(cohort); name(group_id, "independent base group")
    manifest = focused_review.read(cohort/"manifest.json")
    selected = focused_review.read(cohort/"private/selection.json")
    indexes = {r["contribution_id"]: r for r in map(json.loads, case_index.open())
               if r["contribution_id"] in selected["source_ids"]}
    check(set(indexes) == set(selected["source_ids"]), "Missing original case labels")
    cells = []
    for file in sorted((cohort/"public").glob("*.json")):
        public, private = focused_review.read(file), focused_review.read(cohort/"private"/file.name)
        ingests = [e for e in public["events"] if e["event"] == "ingest"]
        assigned = {e["contribution_id"]: e for e in ingests}
        root = assigned[private["reserved_audit_ids"][0]]
        probes = []
        for e in public["events"]:
            if e["event"] not in {"query", "utility_query"}:
                continue
            pid = e["contribution_id"]
            if e["event"] == "query":
                case = indexes[pid]
                check(case == private["gold_cases"][pid] and case["retrieval_query"] == e["text"]
                      and type(case["Y_case"]) is bool
                      and (case["stratum"] == "attack") is case["Y_case"], "Original task labels changed")
                metric = {"attack": "attack", "explicit_benign": "retention", "suggestive_benign": "restraint"}.get(
                    case["stratum"], "benign_unscored")
                reference = case["expected_memory"] if metric != "benign_unscored" else None
                check(metric == "benign_unscored" or bool(reference.strip()), "Missing target")
            else:
                q = private["utility_references"][pid]
                check(q["question"] == e["text"] and q["answers"] and q["support_record_kind"] == "claim"
                      and any(a["artifact_id"] == q["support_artifact_id"] and a["role"] == "external"
                              for a in assigned[pid]["artifacts"]), "Wrong utility reference/origin")
                metric, reference = "source_qa", q["answers"]
            current = assigned[pid]
            relation = ("root_batch" if current["batch_id"] == root["batch_id"] else
                        "unrelated" if current["contributor_id"] != root["contributor_id"] else
                        "other_context" if current["context_id"] != root["context_id"] else
                        "same_context_other_batch")
            probes.append({"probe_id": digest([public["episode_id"], e["event"], pid]), "input_id": pid,
                           "metric": metric, "question_hash": digest(e["text"]),
                           "reference_hash": digest(reference) if reference is not None else None,
                           "relation": relation})
        cells.append({"episode_id": public["episode_id"], "group_id": group_id, "scenario": private["scenario"],
                      "memory_input_hash": digest(ingests), "feedback_hash": digest(private["audits"]),
                      "audit_tickets": 5, "input_ids": sorted(selected["source_ids"]),
                      "template_group_ids": sorted(r["group_id"] for r in indexes.values()), "probes": probes})
    spec = {"schema": comparison.SCHEMA, "basis": "AI_exploratory", "model": "openai/gpt-4o-mini",
            "policy_hashes": {a: Policy(a).fingerprint for a in comparison.TRANSFER},
            "cells": cells, "execution_enabled": False}
    comparison.validate_spec(spec)
    provenance = focused_review.read(cohort/"private/annotation_provenance.json")
    out.mkdir(parents=True, mode=0o700)
    new_json(out/"study.json", spec)
    new_json(out/"annotation_provenance.json", provenance)
    deps = {**manifest["dependencies"], **dependencies([
        cohort/"manifest.json", *[cohort/n for n in manifest["files"]], case_index,
        Path(__file__), Path(comparison.__file__), out/"annotation_provenance.json"])}
    new_json(out/"manifest.json", {"study_sha256": sha_file(out/"study.json"), "dependencies": deps,
                                  "annotation_provenance_sha256": sha_file(out/"annotation_provenance.json"),
                                  "execution_enabled": False})
    comparison.load_plan(out)
    return {"status": "scoped_QA_analysis_plan_prepared", "cells": 3,
            "planned_arm_query_outcomes": sum(len(c["probes"])*len(comparison.ARMS) for c in cells),
            "source_safety_basis": SOURCE_BASIS, "human_verified_memory_labels": 0,
            "selected_human_QA_questions": provenance["selected_human_QA_questions"],
            "execution_enabled": False}
