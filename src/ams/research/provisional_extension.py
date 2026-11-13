"""Versioned extension to every remaining existing development bag, D01–D07.

Reuses the frozen AI-feedback interpretation, original governance, policies and
query engine. Neither held-out outcome selection nor human labels are introduced.
"""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.core.env import load_env
from ams.core.lattice import coarsen
from ams.eval.judge import MemoryJudge
from ams.llm.types import ChatRequest, Message
from ams.research import comparison
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.models import check, digest, event_dict, parse_event
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.execution.session import new_json
from ams.research.native import pipeline as native
from ams.research.phase1_common import read_jsonl
from ams.research.pilot_finish.utility import collect, verified_proposals
from ams.research.provisional.episodes import recode
from ams.research.provisional.pipeline import check_manifest
from ams.research.provisional_execution import (
    budget_snapshot,
    cell_contract,
    check_store,
    nonpolicy,
    read,
)
from ams.research.provisional_run import preparation as first
from ams.research.provisional_run.runner import (
    BoundClient,
    Journal,
    answer_query,
    observation,
    resolve_models,
)
from ams.research.provisional_run.transport import ProvisionalSession
from ams.research.recovery.offline import sha_file
from ams.research.sequential.state import RuntimeState

SCHEMA = "AI-development-extension-D01-D07-v1"
BAGS = tuple(f"D{i:02d}" for i in range(1, 8))
REGIMES = {"strong_localized", "strong_distributed", "uninformative"}


def prepare(repo, out):
    check(not out.exists(), "Refuse to overwrite the development extension")
    prepared = repo / "research_data/mpbench_provisional_v1_20261029"
    stores = repo / "research_data/dynamic_native_stores_v1_20261031"
    reviews = repo / "research_data/ai_pilot_post_adjudication_view_v1_20261101"
    parent = repo / "research_data/provisional_comparison_freeze_v1_20261101"
    parent_cfg, _ = first.verify(parent)
    session = Path(parent_cfg["session_directory"])
    budget = budget_snapshot(session)
    manifest = check_manifest(prepared, "provisional_manifest.json")
    native.verify(stores)
    key_path = repo / "research_data/mpbench_phase1/private/identifier_key.json"
    key = bytes.fromhex(read(key_path)["hex_key"])
    packets, records, _, _, _ = collect([reviews], prepared)
    proposals = list(verified_proposals(reviews))
    record_calls = {r["record_id"]: p["call_id"] for p in proposals for r in p["records"]}
    bags = [b for b in read(prepared / "private/group_selections.json") if b["bag_id"] in BAGS]
    check(
        len(bags) == 7 and all(b["split_intent"] == "development" for b in bags),
        "Wrong fixed development groups",
    )
    cases = {
        r["contribution_id"]: r for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
    }
    ids = {pid for b in bags for pid in b["source_ids"]}
    check(len(ids) == 224, "Repeated/missing development inputs")
    for p in proposals:
        if p["contribution_id"] in ids and p["records"]:
            check(
                p["packet_hash"] == digest(packets[p["contribution_id"]]),
                "Changed development review packet",
            )
    receipts = first.saved_receipts(
        session, {record_calls[r["record_id"]] for pid in ids for r in packets[pid]["records"]}
    )
    absolute = Decimal(parent_cfg["budget_start_used_usd"]) + Decimal("5.00")
    remaining = absolute - Decimal(budget["used_usd"])
    check(remaining > 0, "Original cumulative USD 5 task allowance exhausted")
    cfg = {
        **parent_cfg,
        "schema": SCHEMA,
        "budget_start_used_usd": budget["used_usd"],
        "additional_task_limit_usd": str(remaining),
        "cumulative_task_project_ceiling_usd": str(absolute),
        "parent_experiment_manifest_sha256": sha_file(parent / "manifest.json"),
        "groups": list(BAGS),
        "selection_rule": "all_remaining_preexisting_development_bags_no_outcome_filter",
        "cost_estimate_usd": {
            "conditional_working": "4.903570",
            "conditional_stress": "16.040773",
            "new_verifier_inference": "0",
            "completion_under_task_stop_guaranteed": False,
        },
    }
    deps = {str((prepared / n).resolve()): h for n, h in manifest["files"].items()}
    deps.update(read(stores / "native_manifest.json")["dependencies"])
    for p in [
        prepared / "provisional_manifest.json",
        stores / "native_manifest.json",
        key_path,
        parent / "manifest.json",
        reviews / "results_manifest.json",
        reviews / "automated_proposals.jsonl",
        *Path(first.__file__).parent.glob("*.py"),
        Path(__file__),
        repo / "scripts/run_provisional_extension.py",
        repo / "src/ams/research/evidence_memoization.py",
    ]:
        deps[str(p.resolve())] = sha_file(p)
    out.mkdir(parents=True, mode=0o700)
    (out / "private").mkdir(mode=0o700)
    cells = []
    episode_rows = read(prepared / "private/episode_index.json")
    for bag in sorted(bags, key=lambda b: b["bag_id"]):
        token = bag["bag_token"]
        back = {recode(pid, key): pid for pid in bag["source_ids"]}
        pool = read(prepared / "public" / token / "inputs.json")
        cp = stores / "private" / token / "construction_crosswalk.json.gz"
        with gzip.open(cp, "rt") as stream:
            cw = json.load(stream)
        for path in [cp, cp.with_name("initial_state.json.gz"), cp.with_name("arms.json")]:
            deps[str(path.resolve())] = sha_file(path)
        selected = [
            e for e in episode_rows if e["bag_id"] == bag["bag_id"] and e["scenario"] in REGIMES
        ]
        check(len(selected) == 3, "Missing fixed scenarios")
        for row in sorted(selected, key=lambda e: e["scenario"]):
            state = native.load_store(stores, token, "R")
            checked = check_store(state, cw, pool, key)
            runtime, evaluator = cell_contract(
                row,
                read(prepared / row["public_file"]),
                read(prepared / row["private_file"]),
                pool,
                checked["ingestion_order"],
                sha_file(cp.with_name("initial_state.json.gz")),
            )
            provenance = first.initialize(state, cw, packets, records, runtime["overlay"], key)
            snapshot = state.dump()
            audits, details = first.audits_for(
                state, runtime["audit_requests"], back, packets, records, record_calls, receipts
            )
            qlist = []
            probes = []
            root = runtime["overlay"][runtime["audit_requests"][0]["contribution_id"]]
            for q in runtime["queries"]:
                target = evaluator["targets"][q["query_id"]]
                pid = target["contribution_id"]
                original = back[pid]
                check(q["text"] == packets[original]["intended_use"], "AI audit/query use mismatch")
                item = runtime["overlay"][pid]
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
                qlist.append(
                    {
                        **q,
                        "use_id": packets[original]["use_id"],
                        "input_id": pid,
                        "expected_memory": target["expected_memory"],
                        "metric": metric,
                    }
                )
            graph = state.memory._graphs[cw["session_id"]]
            episode = {
                "episode_id": runtime["episode_id"],
                "session_id": cw["session_id"],
                "queries": qlist,
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
                "write_diagnostics": [
                    {
                        "input_id": recode(pid, key),
                        "expected_memory": cases[pid]["expected_memory"],
                        "entries": [
                            state.memory._entry(graph.claim(link["native_id"]), graph).text
                            for link in cw["record_links"]
                            if link["contribution_id"] == pid and link["record_kind"] == "claim"
                        ],
                    }
                    for pid in bag["source_ids"]
                    if cases[pid]["Y_case"]
                ],
            }
            eid = runtime["episode_id"]
            native.write_gzip(out / "private" / (eid + ".json.gz"), snapshot)
            new_json(out / "private" / (eid + ".json"), episode)
            cells.append(
                {
                    "episode_id": eid,
                    "group_id": bag["bag_id"],
                    "scenario": row["scenario"],
                    "memory_input_hash": runtime["arms"]["R"]["input_schedule_hash"],
                    "feedback_hash": digest(episode["audits"]),
                    "audit_tickets": 5,
                    "input_ids": sorted(back),
                    "template_group_ids": bag["component_ids"],
                    "probes": probes,
                }
            )
            print(f"Frozen {bag['bag_id']} {row['scenario']}", flush=True)
            del state, snapshot
    spec = {
        "schema": comparison.SCHEMA,
        "basis": "AI_exploratory",
        "model": "openai/gpt-4o-mini",
        "policy_hashes": {a: Policy(a).fingerprint for a in "RCMS"},
        "cells": cells,
        "execution_enabled": False,
    }
    comparison.validate_spec(spec)
    new_json(out / "settings.json", cfg)
    new_json(out / "study.json", spec)
    new_json(out / "private/saved_review_receipts.json", receipts)
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
        "status": "remaining_development_bags_frozen",
        "groups": 7,
        "cells": 21,
        "additional_task_limit_usd": str(remaining),
        "new_verifier_calls": 0,
    }


def verify(root):
    lock = read(root / "manifest.json")
    check(
        lock["schema"] == SCHEMA
        and lock["scientific_execution_enabled"] is False
        and lock["hash"] == digest(lock["files"]),
        "Invalid extension manifest",
    )
    for n, h in lock["files"].items():
        check(
            (root / n).resolve().is_relative_to(root.resolve()) and sha_file(root / n) == h,
            "Changed extension payload",
        )
    for n, h in lock["dependencies"].items():
        check(sha_file(Path(n)) == h, "Changed extension dependency")
    cfg = read(root / "settings.json")
    spec = read(root / "study.json")
    check(
        cfg["schema"] == SCHEMA
        and cfg["groups"] == list(BAGS)
        and cfg["basis"] == first.BASIS
        and cfg["human_validated"] is cfg["scientific_human_validated"] is False
        and cfg["total_project_limit_usd"] == "30.00"
        and cfg["automatic_retries"] == 0
        and Decimal(cfg["additional_task_limit_usd"]) <= 5
        and Decimal(cfg["additional_task_limit_usd"]) + Decimal(cfg["budget_start_used_usd"])
        == Decimal(cfg["cumulative_task_project_ceiling_usd"]),
        "Changed extension scope or spending ceiling",
    )
    comparison.validate_spec(spec)
    check(
        len(spec["cells"]) == 21
        and {c["group_id"] for c in spec["cells"]} == set(BAGS)
        and all(len(c["input_ids"]) == 32 and len(c["probes"]) == 27 for c in spec["cells"]),
        "Wrong extension matrix",
    )
    return cfg, spec


class ExtensionSession(ProvisionalSession):
    def authorize(self, plan):
        cfg, spec = verify(plan)
        check(
            cfg["session_id"] == self.config["session_id"]
            and Path(cfg["session_directory"]).resolve() == self.directory,
            "Cannot reset shared allowance",
        )
        self.scope, self.study = cfg, spec
        self.scope_hash = digest([cfg, spec])
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS provisional_native_responses "
            "(call_id TEXT PRIMARY KEY,body TEXT NOT NULL)"
        )
        return cfg


def run(plan, out, *, mock=None):
    """Same query/judge helpers as phase one; new explicit seven-bag verifier/session."""
    cfg, spec = verify(plan)
    journal = Journal(out, digest([cfg, spec]))
    try:
        with ExtensionSession(Path(cfg["session_directory"])) as session:
            if mock is None:
                load_env()
                key = os.environ.get("OPENROUTER_API_KEY")
                check(bool(key), "Missing OpenRouter credential")
                session.arm_provisional(plan, key)
            else:
                session.arm_provisional_mock(plan, mock)
            for cell in spec["cells"]:
                eid = cell["episode_id"]
                episode = read(plan / "private" / (eid + ".json"))
                with gzip.open(plan / "private" / (eid + ".json.gz"), "rt") as stream:
                    snapshot = json.load(stream)
                judge_client = BoundClient(session, "judge_answer")
                judge = MemoryJudge(judge_client, model="openai/gpt-4o-mini")
                entry_client = BoundClient(session, "judge_entry")
                entry_judge = MemoryJudge(
                    entry_client, model="openai/gpt-4o-mini", entry_version="v2"
                )
                writes = [
                    {
                        "input_id": w["input_id"],
                        "verdict": asdict(
                            entry_judge.judge_entry(w["expected_memory"], w["entries"])
                        ),
                    }
                    for w in episode["write_diagnostics"]
                ]
                for arm in ["static", "R", "C", "M", "S"]:
                    state = RuntimeState.load(snapshot)
                    state.policy = Policy("R" if arm == "static" else arm)
                    state.effects_enabled = arm != "static"
                    if arm != "static":
                        state.evidence = EvidenceSnapshot(
                            state.evidence.config,
                            (*state.evidence.events, *(parse_event(a) for a in episode["audits"])),
                            5,
                        )
                        state.clock = 5
                    state.validate()
                    refs = resolve_models(state, session)
                    for q in episode["queries"]:
                        value = answer_query(
                            state, episode["session_id"], q["text"], q["use_id"], refs
                        )
                        before = len(judge_client.calls)
                        verdict = asdict(
                            judge.judge_answer(
                                q["text"], q["expected_memory"], value["answer"]["text"].strip()
                            )
                        )
                        retrieved = (
                            asdict(
                                entry_judge.judge_entry(
                                    q["expected_memory"],
                                    [e["text"] for e in value["retrieval"]["retrieval"]["entries"]],
                                )
                            )
                            if q["metric"] == "attack"
                            else None
                        )
                        journal.commit(
                            digest([eid, arm, q["query_id"]]),
                            {
                                "observation": observation(
                                    cell, episode, q, arm, value["answer"], verdict
                                ),
                                "actual": value,
                                "judge": verdict,
                                "retrieved_entry_verdict": retrieved,
                                "written_entry_diagnostics": writes,
                                "judge_call_id": judge_client.calls[-1]
                                if len(judge_client.calls) > before
                                else None,
                            },
                        )
                    print(f"Completed {cell['group_id']} {cell['scenario']} {arm}", flush=True)
                state = RuntimeState.load(snapshot)
                control = BoundClient(session, "no_memory_answer")
                for q in episode["queries"]:
                    required = coarsen(
                        state.memory.use_type.required(q["text"]), state.memory.granularity
                    ).name.lower()
                    prompt = state.memory.prompts.get("answer_typed", "v2").render(
                        query=q["text"], memory="(nothing)", required=required
                    )
                    response = control.complete(
                        ChatRequest(
                            (Message("user", prompt),),
                            state.answer_model,
                            temperature=0,
                            max_tokens=200,
                        )
                    )
                    before = len(judge_client.calls)
                    verdict = asdict(
                        judge.judge_answer(q["text"], q["expected_memory"], response.text.strip())
                    )
                    journal.commit(
                        digest([eid, "no_memory", q["query_id"]]),
                        {
                            "observation": observation(
                                cell, episode, q, "no_memory", asdict(response), verdict
                            ),
                            "actual": {
                                "answer": asdict(response),
                                "model_call_ids": [control.calls[-1]],
                            },
                            "judge": verdict,
                            "judge_call_id": judge_client.calls[-1]
                            if len(judge_client.calls) > before
                            else None,
                        },
                    )
            rows = journal.rows()
            result = comparison.analyse(spec, [r["observation"] for r in rows])
            after = session.summary()
            result.update(
                feedback_caveat=first.BASIS,
                human_validation="pending; source-grounded QA unavailable",
                refusal_annotation="not independently performed",
                empty_answer_events=sum(not r["actual"]["answer"]["text"].strip() for r in rows),
                length_finish_events=sum(
                    r["actual"]["answer"]["raw_finish_reason"] in {"length", "max_tokens"}
                    for r in rows
                ),
            )
            charges = {
                "project_used_usd": str(
                    Decimal(after["budget"]["used_nanodollars"]) / 1_000_000_000
                ),
                "project_remaining_usd": str(
                    Decimal(after["budget"]["remaining_nanodollars"]) / 1_000_000_000
                ),
                "extension_new_usd": str(
                    Decimal(after["budget"]["used_nanodollars"]) / 1_000_000_000
                    - Decimal(cfg["budget_start_used_usd"])
                ),
            }
            if not (out / "comparison.json").exists():
                new_json(out / "comparison.json", result)
                new_json(out / "costs.json", charges)
                (out / "comparison.md").write_text(
                    comparison.markdown(result) + "\nFeedback: " + first.BASIS + "\n"
                )
            else:
                check(read(out / "comparison.json") == result, "Extension replay diverged")
            return {"status": result["status"], "outcomes": len(rows), "costs": charges}
    finally:
        journal.db.close()


def execute_with_cache(plan, out):
    with memoized_evidence_revisions():
        return run(plan, out)
