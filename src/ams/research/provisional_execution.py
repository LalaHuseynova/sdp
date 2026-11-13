"""Offline provisional execution contract, native compatibility and conditional cost.

This is a preparation path, not a live dispatcher or a scientific-gate override.
Pending audits remain pending. Official case labels never become memory verdicts.
"""

from __future__ import annotations

import copy
import gzip
import json
import sqlite3
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.llm.types import ChatRequest, EmbedRequest, Message
from ams.research.dynamic import Policy
from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.native import pipeline as native
from ams.research.planning.costs import price_snapshot, usd
from ams.research.provisional.episodes import assert_public, recode, validate_episode
from ams.research.provisional.pipeline import check_manifest
from ams.research.recovery.offline import CHAT_MODEL, EMBED_MODEL, sha_file

SCHEMA = "provisional-execution-contract-v1"
ARMS = ("static", "R", "C", "M", "S")
REGIMES = ("strong_localized", "strong_distributed", "uninformative")


def read(path):
    return json.loads(path.read_text())


def budget_snapshot(directory):
    """Read the existing allowance; never initialize, reopen for writing or reset it."""
    config = read(directory / "session.json")
    check(
        config["limit_usd"] == "30.00" and config["model"] == CHAT_MODEL,
        "Use the existing USD 30 research session",
    )
    with sqlite3.connect(f"file:{(directory / 'budget.sqlite').resolve()}?mode=ro", uri=True) as db:
        settings, used, held, blocked = db.execute(
            "SELECT settings,used_nanodollars,held_nanodollars,blocked FROM budget_config"
        ).fetchone()
        states = dict(db.execute("SELECT state,COUNT(*) FROM reservations GROUP BY state"))
    with sqlite3.connect(
        f"file:{(directory / 'dispatch.sqlite').resolve()}?mode=ro", uri=True
    ) as db:
        saved = json.loads(
            db.execute("SELECT value FROM metadata WHERE key='session'").fetchone()[0]
        )
        dispatches = dict(db.execute("SELECT status,COUNT(*) FROM dispatches GROUP BY status"))
    settings = json.loads(settings)
    check(
        saved == config and settings["limit_nanodollars"] == 30_000_000_000,
        "Session/budget identity or ceiling changed",
    )
    check(
        not blocked
        and int(held) == 0
        and not set(states) - {"settled"}
        and not set(dispatches) - {"completed", "failed"},
        "Unsettled/blocked session; reconcile first",
    )
    remaining = Decimal(settings["limit_nanodollars"]) - Decimal(used) - Decimal(held)
    check(remaining >= 0, "Research ceiling exceeded")
    return {
        "session_id": config["session_id"],
        "directory": str(directory.resolve()),
        "total_limit_usd": "30.00",
        "used_usd": str(Decimal(used) / 10**9),
        "held_usd": str(Decimal(held) / 10**9),
        "remaining_usd": str(remaining / 10**9),
        "dispatches": dispatches,
        "new_allowance_created": False,
    }


def nonpolicy(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop("policy")
    value.pop("effects_enabled")
    return digest(value)


def check_store(state, crosswalk, pool, key):
    """Join actual native IDs to public opaque IDs through the private exact crosswalk."""
    state.validate()
    check(
        state.evidence.usage.tickets == 0
        and not state.evidence.observations()
        and all(e.kind == "register" for e in state.evidence.events),
        "Initial state contains audit evidence",
    )
    order = [recode(pid, key) for pid in crosswalk["ingestion_order"]]
    check(
        len(order) == len(set(order)) == len(pool) and set(order) == set(pool),
        "Native ingestion cohort differs from public inputs",
    )
    links = {r["native_id"]: r for r in crosswalk["record_links"]}
    check(
        len(links) == len(crosswalk["record_links"]) == len(state.bindings.records),
        "Missing/duplicate native crosswalk record",
    )
    # The public pool is already blinded. Only native/recovered logical IDs need
    # the keyed translation; applying it again would silently create a second ID.
    logical = {r["record_id"]: (pid, r) for pid, p in pool.items() for r in p["records"]}
    check(
        len(logical) == sum(len(p["records"]) for p in pool.values()), "Repeated public record ID"
    )
    check(
        set(logical) == {recode(r.record_id, key) for r in state.bindings.records},
        "Native/public claim or chunk coverage changed",
    )
    graph = state.memory._graphs[crosswalk["session_id"]]
    artifacts = {a["artifact_id"]: a for p in pool.values() for a in p["artifacts"]}
    for binding in state.bindings.records:
        link = links[binding.native_id]
        pid, record = logical[recode(binding.record_id, key)]
        check(
            recode(link["contribution_id"], key) == pid
            and link["record_id"] == binding.record_id
            and link["record_kind"] == binding.record_kind == record["record_kind"]
            and link["content_hash"] == binding.content_hash == record["content_hash"]
            and digest(record["text"]) == record["content_hash"],
            "Native/logical record mismatch",
        )
        text = (
            graph.claim(binding.native_id).text
            if binding.record_kind == "claim"
            else next(
                c.text
                for c in state.memory._chunks[binding.session_id]
                if c.chunk_id == binding.native_id
            )
        )
        check(text == record["text"], "Native memory text differs from public record")
        check(
            set(recode(list(binding.artifact_ids), key))
            <= {a["artifact_id"] for a in pool[pid]["artifacts"]},
            "Record policy parents cross contributions",
        )
    for binding in state.bindings.sources:
        span = crosswalk["source_spans"][binding.source_id]
        artifact = artifacts[recode(binding.artifact_id, key)]
        check(
            recode(span["artifact_id"], key) == artifact["artifact_id"]
            and artifact["text"][span["start"] : span["end"]]
            == span["quote"]
            == graph.source(binding.source_id).text,
            "Native source span differs",
        )
        check(
            (artifact["role"] == "principal") == (binding.principal_id is not None),
            "Principal/external ownership changed",
        )
    return {
        "native_state_and_spans_checked": True,
        "ingestion_order": order,
        "claims": sum(r.record_kind == "claim" for r in state.bindings.records),
        "chunks": sum(r.record_kind == "evidence_chunk" for r in state.bindings.records),
        "source_bindings": len(state.bindings.sources),
        "unknown_external_roots": sum(
            p.attribution == "unknown" for p in state.evidence.roots.values()
        ),
        "ambiguous_claims": sum(r.origin_class == "ambiguous" for r in state.bindings.records),
        "human_verified_memory_labels": 0,
        "audit_tickets_consumed": 0,
    }


def query_coverage(state, queries):
    """Inspect exact replay tables without invoking classification, retrieval or a model."""
    check(
        not any(c.history for c in state.clients), "Initial clients contain earlier query history"
    )
    for query in queries:
        request = ChatRequest(
            (
                Message(
                    "user",
                    state.memory.prompts.get("classify_use_type", "v2").render(query=query.strip()),
                ),
            ),
            CHAT_MODEL,
            temperature=0.0,
            max_tokens=24,
        )
        embed = EmbedRequest((query,), EMBED_MODEL)
        check(
            request.cache_key("openrouter") in state.memory.use_type.client.chats,
            "Missing frozen classifier; no per-arm API fallback",
        )
        check(
            embed.cache_key("local") in state.memory.embed_client.embeddings,
            "Missing frozen query embedding; no model download/fallback",
        )
    return {
        "unique_query_catalog_checked": len(set(queries)),
        "classifier_misses": 0,
        "embedding_misses": 0,
        "classification_or_retrieval_executed": False,
    }


def cell_contract(row, public, private, pool, order, base_hash):
    validate_episode({**public, "private": private}, pool)
    actual_order = [e["contribution_id"] for e in public["events"] if e["event"] == "ingest"]
    check(actual_order == order, "Store and episode ingestion order differ; rebuild store")
    signature = digest([pool, public["overlay"], public["events"]])
    check(
        public["shared_arm_inputs"] == {a: signature for a in "RCMS"}
        and row["shared_arm_inputs"] == public["shared_arm_inputs"],
        "Unmatched method inputs",
    )
    audits = [e for e in public["events"] if e["event"] == "audit_request_pending"]
    queries = [e for e in public["events"] if e["event"] == "original_query"]
    check(
        len(audits) == len({e["ticket_id"] for e in audits}) == 5
        and [e["contribution_id"] for e in audits] == private["reserved_audit_ids"]
        and all(e["verdict"] is None and e["completed_verifications"] == 0 for e in audits),
        "Pending audits must not become fabricated findings",
    )
    check(
        len(queries) == len({e["query_id"] for e in queries}) == 27
        and set(private["case_targets"]) == {e["query_id"] for e in queries},
        "Changed probe cohort",
    )
    targets = private["case_targets"]
    check(
        {t["contribution_id"] for t in targets.values()} | set(private["reserved_audit_ids"])
        == set(pool)
        and not {t["contribution_id"] for t in targets.values()}
        & set(private["reserved_audit_ids"]),
        "Audited cases entered transfer endpoint",
    )
    common = {
        "initial_snapshot_sha256": base_hash,
        "input_schedule_hash": signature,
        "query_schedule_hash": digest(queries),
        "audit_request_hash": digest(audits),
        "audit_ticket_limit": 5,
        "scheduled_audit_opportunities": 5,
    }
    arms = {
        a: {
            **common,
            "policy": asdict(Policy("R" if a == "static" else a)),
            "effects_enabled": a != "static",
            "consumes_revealed_audits": a != "static",
        }
        for a in ARMS
    }
    runtime = {
        "episode_id": row["episode_token"],
        "overlay": public["overlay"],
        "ingestion_order": order,
        "queries": queries,
        "audit_requests": audits,
        "arms": arms,
        "execution_enabled": False,
    }
    assert_public(runtime)
    check(
        all(
            type(t["Y_case"]) is bool
            and t["Y_case"] == (t["stratum"] == "attack")
            and bool(t["expected_memory"].strip())
            for t in targets.values()
        ),
        "Original case labels/targets changed",
    )
    evaluator = {
        "episode_id": row["episode_token"],
        "group_id": row["bag_id"],
        "scenario": row["scenario"],
        "targets": targets,
        "reserved_audit_ids": private["reserved_audit_ids"],
        "metric_counts": dict(Counter(t["stratum"] for t in targets.values())),
        "scheduled_audits_are_not_verdicts": True,
        "memory_safety_label_basis": "unknown",
        "source_grounded_utility_endpoint": "unavailable_unvalidated_questions_not_used",
    }
    return runtime, evaluator


def cost_estimate(cells, envelopes, pricing, budget):
    inp, out = price_snapshot(pricing)
    check(
        inp <= Decimal("0.15") and out <= Decimal("0.60"),
        "Observed price exceeds existing guard ceilings",
    )
    originals = sum(len(c[0]["queries"]) for c in cells)
    attacks = sum(c[1]["metric_counts"].get("attack", 0) for c in cells)
    controls = {t["contribution_id"] for _, e in cells for t in e["targets"].values()}
    attack_controls = {
        t["contribution_id"] for _, e in cells for t in e["targets"].values() if t["Y_case"]
    }
    counts = {
        "memory_answers": originals * 5,
        "no_memory_answers": len(controls),
        "answer_judgments": originals * 5 + len(controls),
        "retrieved_entry_judgments": attacks * 5,
        "written_entry_judgments": 20 * len({e["group_id"] for _, e in cells}),
    }
    scenarios = {}
    for label, stress in [("working", False), ("stress", True)]:
        profiles = {
            "memory_answers": (8000 if stress else 3500, 200),
            "no_memory_answers": (1500 if stress else 750, 200),
            "answer_judgments": (2500 if stress else 1000, 120),
            "retrieved_entry_judgments": (8000 if stress else 3000, 120),
            "written_entry_judgments": (4000 if stress else 1500, 120),
            "conflict_checks": (2048 if stress else 900, 6),
        }
        calls = {**counts, "conflict_checks": counts["memory_answers"] * (6 if stress else 1)}
        stages, total, full = [], Decimal(0), Decimal(0)
        for stage, (it, ot) in profiles.items():
            n = calls[stage]
            price = Decimal(n) * (it * inp + ot * out) / 1_000_000
            total += price
            full += Decimal(n) * (128000 * inp + ot * out) / 1_000_000
            stages.append(
                {
                    "stage": stage,
                    "cold_calls": n,
                    "assumed_input_tokens_each": it,
                    "output_ceiling_each": ot,
                    "estimated_usd": usd(price),
                }
            )
        estimate = total * Decimal("1.25")
        scenarios[label] = {
            "stages": stages,
            "one_attempt_usd": usd(total),
            "with_25_percent_headroom_usd": usd(estimate),
            "full_context_all_calls_usd": usd(full),
            "fits_remaining_allowance_on_assumptions": estimate <= Decimal(budget["remaining_usd"]),
            "completion_within_cap_guaranteed": False,
        }
    return {
        "schema": "provisional-conditional-cost-v1",
        "pricing": pricing,
        "scenarios": scenarios,
        "exact_scheduled_counts": {
            **counts,
            "unique_no_memory_attack_controls": len(attack_controls),
            "shared_pending_audit_jobs": 5 * len(cells),
            "scheduled_audit_tickets_each_RCMS": 5 * len(cells),
            "scheduled_audit_tickets_all_RCMS": 20 * len(cells),
            "static_completed_audits": 0,
        },
        "native_prompt_envelopes": envelopes,
        "native_token_counts_measured": False,
        "cache_discount_assumed": False,
        "physical_attempts_each": 1,
        "automatic_retries": 0,
        "audit_verifier_inference_cost_usd": None,
        "excluded_costs": [
            "qualifying/freezing audit verdicts and verification-equivalent usage",
            "source-grounded QA validation",
            "any missing/new classifier or embedding catalog",
            "new extraction",
            "human labor",
            "robustness/full-release/tuning studies",
            "provider taxes/fees",
        ],
        "cost_scope": (
            "conditional answer/conflict/target-judge stages; not a complete research-package quote"
        ),
        "unknown_audit_cost_is_not_zero": True,
        "shared_session": budget,
        "new_cost_usd": "0",
        "paid_execution_enabled": False,
    }


def prepare(repo, prepared, stores, session, pricing_path, out, *, bag_ids=("D00",)):
    check(not out.exists(), "Refuse to overwrite provisional execution preparation")
    check(bag_ids and len(bag_ids) == len(set(bag_ids)), "Select distinct development bags")
    manifest = check_manifest(prepared, "provisional_manifest.json")
    native_verification = native.verify(stores)
    bags = [b for b in read(prepared / "private/group_selections.json") if b["bag_id"] in bag_ids]
    check(
        len(bags) == len(bag_ids) and all(b["split_intent"] == "development" for b in bags),
        "This provisional path only prepares existing development bags",
    )
    key_path = repo / "research_data/mpbench_phase1/private/identifier_key.json"
    key = bytes.fromhex(read(key_path)["hex_key"])
    pricing = read(pricing_path)
    budget = budget_snapshot(session)
    deps = {
        str((prepared / "provisional_manifest.json").resolve()): sha_file(
            prepared / "provisional_manifest.json"
        ),
        str((stores / "native_manifest.json").resolve()): sha_file(stores / "native_manifest.json"),
        str(key_path.resolve()): sha_file(key_path),
        str(pricing_path.resolve()): sha_file(pricing_path),
    }
    nmanifest = read(stores / "native_manifest.json")
    deps.update(nmanifest["dependencies"])
    deps.update({str((prepared / n).resolve()): h for n, h in manifest["files"].items()})
    deps.update(
        {
            str((session / n).resolve()): sha_file(session / n)
            for n in ["session.json", "budget.sqlite", "dispatch.sqlite"]
        }
    )
    deps[str(Path(__file__).resolve())] = sha_file(Path(__file__))
    cli = repo / "scripts/prepare_provisional_execution.py"
    deps[str(cli.resolve())] = sha_file(cli)
    rows = read(prepared / "private/episode_index.json")
    checks, cells, envelopes = [], [], []
    for bag in sorted(bags, key=lambda b: b["bag_id"]):
        token = bag["bag_token"]
        pool = read(prepared / "public" / token / "inputs.json")
        cp = stores / "private" / token / "construction_crosswalk.json.gz"
        with gzip.open(cp, "rt") as stream:
            crosswalk = json.load(stream)
        state = native.load_store(stores, token, "R")
        check_info = check_store(state, crosswalk, pool, key)
        base = stores / "private" / token / "initial_state.json.gz"
        for p in [cp, base, base.with_name("arms.json")]:
            deps[str(p.resolve())] = sha_file(p)
        reference = nonpolicy(state.dump())
        graphs = []
        clients = []
        classifiers = []
        loaded = []
        for arm in ARMS:
            copy_state = native.load_store(stores, token, "R" if arm == "static" else arm)
            copy_state.effects_enabled = arm != "static"
            check(
                nonpolicy(copy_state.dump()) == reference,
                "Arms have unequal initial memory/governance state",
            )
            loaded.append(copy_state)
            graphs.append(id(copy_state.memory._graph(crosswalk["session_id"])))
            clients.append(id(copy_state.memory.client))
            classifiers.append(id(copy_state.memory.use_type._cache))
        check(
            len(set(graphs)) == len(set(clients)) == len(set(classifiers)) == 5,
            "Arms share mutable state",
        )
        selected = [r for r in rows if r["bag_id"] == bag["bag_id"] and r["scenario"] in REGIMES]
        check(
            len(selected) == 3 and {r["scenario"] for r in selected} == set(REGIMES),
            "Missing planned regimes",
        )
        queries = []
        for row in sorted(selected, key=lambda r: r["scenario"]):
            cell = cell_contract(
                row,
                read(prepared / row["public_file"]),
                read(prepared / row["private_file"]),
                pool,
                check_info["ingestion_order"],
                sha_file(base),
            )
            cells.append(cell)
            queries.extend(q["text"] for q in cell[0]["queries"])
        check_info.update(
            bag_id=bag["bag_id"],
            bag_token=token,
            initial_nonpolicy_state_hash=reference,
            independent_static_RCMS_instances=True,
            query_catalog=query_coverage(state, queries),
        )
        checks.append(check_info)
        envelopes.append(crosswalk["prompt_envelope"])
    costs = cost_estimate(cells, envelopes, pricing, budget)
    report = {
        "schema": SCHEMA,
        "status": "provisional_preparation_complete_execution_disabled",
        "groups_checked": len(bags),
        "existing_native_bundle_verification": native_verification,
        "overlays_planned": len(cells),
        "arms": list(ARMS),
        "store_checks": checks,
        "basis": "existing_case_intent_development_not_Z_balanced",
        "human_review": "deferred",
        "human_verified_memory_labels": 0,
        "human_validated_questions": 0,
        "new_audit_verdicts": 0,
        "paid_execution_enabled": False,
        "new_API_calls": 0,
        "new_cost_usd": "0",
        "answers_generated": 0,
        "retrieval_experiments": 0,
        "input_and_state_parity_checked": True,
        "retrieved_context_or_answer_parity_claimed": False,
        "remaining_execution_requirements": [
            "frozen shared audit verdicts with explicit non-human basis and exact uses/records",
            "validated synthetic origin bindings; ambiguous claims remain unknown",
            "versioned provisional controller/transport preflight; scientific gate unchanged",
            "equivalent verifier calls/tokens/cost; budget must include new verification",
        ],
        "source_grounded_utility": "not_available; do not infer preservation from restraint alone",
    }
    for n, h in deps.items():
        check(sha_file(Path(n)) == h, "Input changed while preparing provisional execution")
    out.mkdir(parents=True, mode=0o700)
    (out / "public").mkdir(mode=0o700)
    (out / "private").mkdir(mode=0o700)
    new_json(out / "preparation_report.json", report)
    new_json(out / "cost_estimate.json", costs)
    for runtime, evaluator in cells:
        new_json(out / "public" / (runtime["episode_id"] + ".json"), runtime)
        new_json(out / "private" / (runtime["episode_id"] + ".json"), evaluator)
    files = {str(p.relative_to(out)): sha_file(p) for p in out.rglob("*.json")}
    new_json(
        out / "manifest.json",
        {
            "schema": SCHEMA,
            "files": files,
            "hash": digest(files),
            "dependencies": deps,
            "execution_enabled": False,
            "human_validation_deferred": True,
        },
    )
    verify(out)
    return report


def verify(out):
    manifest = read(out / "manifest.json")
    check(
        manifest["schema"] == SCHEMA
        and manifest["execution_enabled"] is False
        and manifest["human_validation_deferred"] is True
        and digest(manifest["files"]) == manifest["hash"],
        "Provisional plan changed or enabled execution",
    )
    for n, h in manifest["files"].items():
        path = out / n
        check(
            path.resolve().is_relative_to(out.resolve()) and sha_file(path) == h,
            "Plan payload changed",
        )
    for n, h in manifest["dependencies"].items():
        check(sha_file(Path(n)) == h, "Plan dependency changed; reprepare")
    report = read(out / "preparation_report.json")
    check(
        report["human_verified_memory_labels"]
        == report["human_validated_questions"]
        == report["new_audit_verdicts"]
        == 0
        and report["paid_execution_enabled"] is False,
        "Preparation promoted annotations or execution",
    )
    for p in (out / "public").glob("*.json"):
        c = read(p)
        assert_public(c)
        check(
            c["execution_enabled"] is False and set(c["arms"]) == set(ARMS), "Changed runtime arms"
        )
        common = [
            {
                k: a[k]
                for k in [
                    "initial_snapshot_sha256",
                    "input_schedule_hash",
                    "query_schedule_hash",
                    "audit_request_hash",
                    "audit_ticket_limit",
                    "scheduled_audit_opportunities",
                ]
            }
            for a in c["arms"].values()
        ]
        check(
            all(v == common[0] for v in common)
            and common[0]["audit_ticket_limit"] == 5
            and common[0]["scheduled_audit_opportunities"] == 5,
            "Unequal inputs/audit budgets",
        )
        check(
            common[0]["query_schedule_hash"] == digest(c["queries"])
            and common[0]["audit_request_hash"] == digest(c["audit_requests"])
            and len(c["queries"]) == 27
            and len(c["audit_requests"]) == 5
            and all(
                a["verdict"] is None and a["completed_verifications"] == 0
                for a in c["audit_requests"]
            ),
            "Changed query cohort or invented audit verdict",
        )
        for arm, a in c["arms"].items():
            check(
                a["policy"] == asdict(Policy("R" if arm == "static" else arm))
                and a["effects_enabled"] is (arm != "static")
                and a["consumes_revealed_audits"] is (arm != "static"),
                "Changed comparison policy",
            )
    return {
        "status": "passed",
        "files_checked": len(manifest["files"]),
        "dependencies_checked": len(manifest["dependencies"]),
        "execution_enabled": False,
        "human_review": "deferred",
        "new_API_calls": 0,
    }
