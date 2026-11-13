"""Freeze simulated AI feedback and controlled synthetic provenance, without calls."""

from __future__ import annotations

import gzip
import json
import sqlite3
from collections import defaultdict
from dataclasses import replace
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from ams.research import comparison
from ams.research.dynamic import (
    Audit,
    EvidenceSnapshot,
    Finding,
    Policy,
    Provenance,
    Register,
    StoredRecord,
)
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import check, digest, event_dict
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.native.pipeline import load_store, write_gzip
from ams.research.phase1_common import read_jsonl
from ams.research.pilot_finish.utility import collect, verified_proposals
from ams.research.provisional.episodes import recode
from ams.research.provisional_execution import (
    budget_snapshot,
    nonpolicy,
    read,
)
from ams.research.provisional_execution import (
    verify as verify_source,
)
from ams.research.recovery.offline import sha_file
from ams.research.retrieval import BindingCatalog

SCHEMA = "AI-simulated-feedback-comparison-v1"
BASIS = "saved_AI_proposals_as_simulated_feedback_not_verified_ground_truth"


def initialize(state, crosswalk, packets, assessments, overlay, key):
    """No verdict is consulted when binding provenance. Principal sources stay owned."""
    links = {r["record_id"]: r for r in crosswalk["record_links"]}
    roots, groups, bindings, decisions = {}, defaultdict(list), [], []
    for binding in state.bindings.records:
        link = links[binding.record_id]
        pid = link["contribution_id"]
        packet = packets[pid]
        source = {a["artifact_id"]: a for a in packet["artifacts"]}
        assessed = assessments[binding.record_id]
        check(
            assessed["content_hash"] == binding.content_hash, "AI assessment memory version changed"
        )
        spans = assessed["source_spans"]
        check(
            all(
                s["artifact_id"] in source
                and source[s["artifact_id"]]["text"][s["start"] : s["end"]] == s["quote"]
                for s in spans
            ),
            "Invalid AI provenance span",
        )
        # Exact chunk construction is independent of semantic claim attribution.
        external = binding.origin_class == "external" or (
            binding.origin_class == "ambiguous"
            and assessed["origin"] == "external"
            and bool(spans)
            and all(source[s["artifact_id"]]["role"] == "external" for s in spans)
        )
        kind = (
            "principal"
            if binding.origin_class == "principal"
            else "external"
            if external
            else "unknown"
        )
        assignment = overlay[recode(pid, key)]
        root = "root_" + digest([pid, kind])[:24]
        if kind == "external":
            origin = Provenance(
                root,
                assignment["context_id"],
                assignment["batch_id"],
                assignment["contributor_id"],
                "authenticated_external",
            )
            parent_ids = tuple(
                dict.fromkeys((*binding.artifact_ids, *(s["artifact_id"] for s in spans)))
            )
            binding = replace(binding, origin_class="external", artifact_ids=parent_ids)
        else:
            origin = Provenance(
                root,
                assignment["context_id"],
                None,
                None,
                "principal" if kind == "principal" else "unknown",
                principal_id="user" if kind == "principal" else None,
            )
        roots[root] = origin
        groups[root].append(
            StoredRecord(
                binding.record_id,
                binding.content_hash,
                binding.record_kind,
                link["structural_artifact_id"],
            )
        )
        bindings.append(binding)
        decisions.append(
            {
                "record_id": binding.record_id,
                "contribution_id": pid,
                "origin_group": kind,
                "root_id": root,
                "scope": "controlled_synthetic_origin_assumption",
                "natural_identity_authenticated": False,
            }
        )
    registers = tuple(
        Register("reg_" + digest(root)[:24], 0, roots[root], tuple(members))
        for root, members in sorted(groups.items())
    )
    state.bindings = BindingCatalog(
        state.bindings.episode_id, state.bindings.sources, tuple(bindings)
    )
    state.evidence = EvidenceSnapshot(
        LedgerConfig(state.bindings.episode_id, "verified_audits", 5), registers, 0
    )
    state.policy = Policy("R")
    state.validate()
    check(state.evidence.usage.tickets == 0, "Initialization cannot reveal a finding")
    return decisions


def saved_receipts(session, calls):
    """Freeze existing physical receipts once; never charge again to retrieve them."""
    rows = {}
    with sqlite3.connect(f"file:{(session / 'dispatch.sqlite').resolve()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for call_id in sorted(calls):
            row = db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
            check(
                row is not None and row["status"] == "completed",
                "Missing completed AI review receipt",
            )
            result = json.loads(row["result"])
            check(
                dispatch_hash(row, result) == row["result_hash"] and result["error"] is None,
                "AI review receipt changed or failed",
            )
            receipt = result["dispatch"]["receipt"]
            check(
                receipt["state"] == "settled" and receipt["actual_nanodollars"] is not None,
                "Unverified old annotation billing",
            )
            rows[call_id] = {
                "call_id": call_id,
                "dispatch_result_hash": row["result_hash"],
                "receipt": receipt,
                "usage": result["response"]["usage"],
            }
    return rows


def audits_for(state, requests, back, packets, records, record_calls, receipts):
    audits, details = [], []
    for at, job in enumerate(requests, 1):
        pid = back[job["contribution_id"]]
        root = "root_" + digest([pid, "external"])[:24]
        check(
            root in state.evidence.roots,
            "Scheduled contribution has no attributable external records",
        )
        members = [r for _, (rid, r) in state.evidence.records.items() if rid == root]
        findings = tuple(
            Finding(
                r.record_id,
                r.content_hash,
                "unresolved"
                if records[r.record_id]["verdict"] == "uncertain"
                else records[r.record_id]["verdict"],
                "AI_proposal_" + digest(records[r.record_id]),
            )
            for r in members
        )
        verdicts = [f.verdict for f in findings]
        outcome = (
            "unsafe"
            if "unsafe" in verdicts
            else "safe_for_use"
            if all(v == "safe_for_use" for v in verdicts)
            else "unresolved"
        )
        calls = sorted({record_calls[r.record_id] for r in members})
        usage = [receipts[c]["usage"] for c in calls]
        # A historical review may use several calls; one logical incident vote is
        # not several independent audits. Actual call counts are preserved below.
        micros = int(
            (
                sum(Decimal(receipts[c]["receipt"]["actual_nanodollars"]) for c in calls) / 1000
            ).to_integral_value(rounding=ROUND_CEILING)
        )
        audit = Audit(
            "audit_" + digest([job["ticket_id"], root])[:24],
            at,
            job["ticket_id"],
            root,
            packets[pid]["use_id"],
            state.access.version,
            outcome,
            findings,
            True,
            "saved_gpt4omini_AI_proposals",
            "controlled_audit",
            "AI_simulation_" + digest(calls),
            input_tokens=sum(u["input_tokens"] for u in usage),
            output_tokens=sum(u["output_tokens"] for u in usage),
            cost_microusd=micros,
        )
        audits.append(audit)
        details.append(
            {
                "ticket_id": job["ticket_id"],
                "contribution_id": pid,
                "outcome": outcome,
                "review_call_ids": calls,
                "equivalent_physical_calls": len(calls),
                "basis": BASIS,
                "human_validated": False,
                "original_review_flags_unchanged": True,
                "scope": "attributable_external_component_for_original_use",
            }
        )
    EvidenceSnapshot(state.evidence.config, (*state.evidence.events, *audits), 5)
    return audits, details


def prepare(repo, source, stores, prepared, reviews, session, out):
    check(not out.exists(), "Refuse to overwrite an experiment freeze")
    verify_source(source)
    budget = budget_snapshot(session)
    packets, records, _, _, _ = collect([reviews], prepared)
    proposals = list(verified_proposals(reviews))
    record_calls = {r["record_id"]: p["call_id"] for p in proposals for r in p["records"]}
    groups = read(prepared / "private/group_selections.json")
    chosen = read(source / "preparation_report.json")["store_checks"]
    check(
        len(chosen) == 1 and chosen[0]["bag_id"] == "D00",
        "Frozen first-development-group scope only",
    )
    bag = next(g for g in groups if g["bag_id"] == "D00")
    key = bytes.fromhex(
        read(repo / "research_data/mpbench_phase1/private/identifier_key.json")["hex_key"]
    )
    back = {recode(pid, key): pid for pid in bag["source_ids"]}
    for pid in bag["source_ids"]:
        check(
            all(
                records[r["record_id"]]["content_hash"] == digest(r["text"])
                for r in packets[pid]["records"]
            ),
            "AI review differs from actual extracted record",
        )
        check(
            all(
                p["packet_hash"] == digest(packets[pid])
                for p in proposals
                if p["contribution_id"] == pid and p["records"]
            ),
            "AI packet version changed",
        )
    receipts = saved_receipts(
        session,
        {
            record_calls[r["record_id"]]
            for pid in bag["source_ids"]
            for r in packets[pid]["records"]
        },
    )
    snapshots, episodes, cells = {}, {}, []
    token = bag["bag_token"]
    case_index = {
        r["contribution_id"]: r for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
    }
    with gzip.open(stores / "private" / token / "construction_crosswalk.json.gz", "rt") as stream:
        crosswalk = json.load(stream)
    for file in sorted((source / "public").glob("*.json")):
        public = read(file)
        evaluator = read(source / "private" / file.name)
        state = load_store(stores, token, "R")
        provenance = initialize(state, crosswalk, packets, records, public["overlay"], key)
        snapshot = state.dump()
        audits, details = audits_for(
            state, public["audit_requests"], back, packets, records, record_calls, receipts
        )
        queries = []
        probes = []
        root = public["overlay"][public["audit_requests"][0]["contribution_id"]]
        for q in public["queries"]:
            target = evaluator["targets"][q["query_id"]]
            pid = target["contribution_id"]
            original = back[pid]
            check(
                q["text"] == packets[original]["intended_use"],
                "Query/use mismatches the original AI review",
            )
            item = public["overlay"][pid]
            relation = (
                "root_batch"
                if item["batch_id"] == root["batch_id"]
                else "unrelated"
                if item["contributor_id"] != root["contributor_id"]
                else "other_context"
                if item["context_id"] != root["context_id"]
                else "same_context_other_batch"
            )
            metric = {
                "attack": "attack",
                "explicit_benign": "retention",
                "suggestive_benign": "restraint",
            }[target["stratum"]]
            probes.append(
                {
                    "probe_id": q["query_id"],
                    "input_id": pid,
                    "metric": metric,
                    "question_hash": digest(q["text"]),
                    "reference_hash": digest(target["expected_memory"]),
                    "relation": relation,
                }
            )
            queries.append(
                {
                    **q,
                    "use_id": packets[original]["use_id"],
                    "input_id": pid,
                    "expected_memory": target["expected_memory"],
                    "metric": metric,
                }
            )
        episode = {
            "episode_id": public["episode_id"],
            "session_id": crosswalk["session_id"],
            "queries": queries,
            "audits": [event_dict(a) for a in audits],
            "audit_details": details,
            "initial_memory_hash": nonpolicy(snapshot),
            "provenance_decisions": provenance,
            "equivalent_verification": {
                "calls": sum(d["equivalent_physical_calls"] for d in details),
                "input_tokens": sum(a.input_tokens for a in audits),
                "output_tokens": sum(a.output_tokens for a in audits),
                "usd": str(Decimal(sum(a.cost_microusd for a in audits)) / 1_000_000),
            },
        }
        graph = state.memory._graphs[crosswalk["session_id"]]
        episode["write_diagnostics"] = [
            {
                "input_id": recode(pid, key),
                "expected_memory": case_index[pid]["expected_memory"],
                "entries": [
                    state.memory._entry(graph.claim(link["native_id"]), graph).text
                    for link in crosswalk["record_links"]
                    if link["contribution_id"] == pid and link["record_kind"] == "claim"
                ],
            }
            for pid in bag["source_ids"]
            if case_index[pid]["Y_case"]
        ]
        snapshots[public["episode_id"]] = snapshot
        episodes[public["episode_id"]] = episode
        cells.append(
            {
                "episode_id": public["episode_id"],
                "group_id": "D00",
                "scenario": evaluator["scenario"],
                "memory_input_hash": public["arms"]["R"]["input_schedule_hash"],
                "feedback_hash": digest(episode["audits"]),
                "audit_tickets": 5,
                "input_ids": sorted(back),
                "template_group_ids": bag["component_ids"],
                "probes": probes,
            }
        )
    spec = {
        "schema": comparison.SCHEMA,
        "basis": "AI_exploratory",
        "model": "openai/gpt-4o-mini",
        "policy_hashes": {a: Policy(a).fingerprint for a in "RCMS"},
        "cells": cells,
        "execution_enabled": False,
    }
    comparison.validate_spec(spec)
    deps = read(source / "manifest.json")["dependencies"]
    deps = {
        n: h
        for n, h in deps.items()
        if not (Path(n).parent.resolve() == session.resolve() and Path(n).suffix == ".sqlite")
    }
    for p in [
        source / "manifest.json",
        reviews / "results_manifest.json",
        reviews / "automated_proposals.jsonl",
    ]:
        deps[str(p.resolve())] = sha_file(p)
    for p in [*Path(__file__).parent.glob("*.py"), repo / "scripts/run_provisional_comparison.py"]:
        deps[str(p.resolve())] = sha_file(p)
    out.mkdir(parents=True, mode=0o700)
    (out / "private").mkdir(mode=0o700)
    for eid, snapshot in snapshots.items():
        write_gzip(out / "private" / (eid + ".json.gz"), snapshot)
        new_json(out / "private" / (eid + ".json"), episodes[eid])
    new_json(out / "study.json", spec)
    new_json(out / "private/saved_review_receipts.json", receipts)
    new_json(
        out / "settings.json",
        {
            "schema": SCHEMA,
            "basis": BASIS,
            "scope": "AI_provisional_comparison",
            "session_id": budget["session_id"],
            "session_directory": str(session.resolve()),
            "budget_start_used_usd": budget["used_usd"],
            "additional_task_limit_usd": "5.00",
            "total_project_limit_usd": "30.00",
            "human_validated": False,
            "source_qa_validated": False,
            "source_original_flags_not_promoted": True,
            "annotation_truth_accuracy": "unknown",
            "physical_request_cache": "shared_by_exact_stage_request_across_methods",
            "automatic_retries": 0,
            "new_verification_inference_cost_usd": "0",
            "historical_equivalent_verification_not_free": True,
            "execution_scope_enabled": True,
            "scientific_human_validated": False,
            "case_intent_controlled": True,
        },
    )
    files = {str(p.relative_to(out)): sha_file(p) for p in out.rglob("*") if p.is_file()}
    new_json(
        out / "manifest.json",
        {
            "schema": SCHEMA,
            "files": files,
            "hash": digest(files),
            "dependencies": deps,
            "scientific_execution_enabled": False,
        },
    )
    verify(out)
    return {
        "status": "AI_simulation_frozen",
        "episodes": len(episodes),
        "queries_per_arm": 81,
        "new_verification_API_calls": 0,
        "human_validated": False,
        "additional_task_limit_usd": "5.00",
    }


def verify(root):
    lock = read(root / "manifest.json")
    check(
        lock["schema"] == SCHEMA
        and lock["hash"] == digest(lock["files"])
        and lock["scientific_execution_enabled"] is False,
        "Invalid provisional execution manifest",
    )
    for n, h in lock["files"].items():
        check(
            (root / n).resolve().is_relative_to(root.resolve()) and sha_file(root / n) == h,
            "Changed frozen simulation data",
        )
    for n, h in lock["dependencies"].items():
        check(sha_file(Path(n)) == h, "Simulation dependency changed")
    cfg = read(root / "settings.json")
    check(
        cfg["schema"] == SCHEMA
        and cfg["basis"] == BASIS
        and cfg["scope"] == "AI_provisional_comparison"
        and cfg["human_validated"] is cfg["scientific_human_validated"] is False
        and cfg["execution_scope_enabled"] is True
        and cfg["total_project_limit_usd"] == "30.00"
        and cfg["additional_task_limit_usd"] == "5.00"
        and cfg["automatic_retries"] == 0,
        "Scope cannot become human-validated science or increase cost",
    )
    spec = read(root / "study.json")
    comparison.validate_spec(spec)
    check(
        len(spec["cells"]) == 3 and {c["group_id"] for c in spec["cells"]} == {"D00"},
        "Changed frozen study scope",
    )
    return cfg, spec
