"""AI-only composition checks and explicit exploratory freeze; no human gold."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections import Counter
from fractions import Fraction
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json
from ams.research.phase1_common import CONTEXTS, rng, stage_seed
from ams.research.phase1_scenarios import weighted_subset
from ams.research.recovery.offline import sha_file

from .utility import collect, eligible_questions

QUOTAS = [
    ("attack", "unsafe", 8),
    ("attack", "safe_for_use", 2),
    ("explicit_benign", "safe_for_use", 1),
    ("suggestive_benign", "safe_for_use", 5),
]


def readiness(prepared, reviews, out):
    check(not out.exists(), "Readiness output exists")
    packets, records, assessments, candidates, bundles = collect(reviews, prepared)
    index = {
        p["contribution_id"]: p
        for p in map(json.loads, (prepared / "private/evaluator_case_index.jsonl").open())
        if p["contribution_id"] in packets
    }
    questions = eligible_questions(packets, records, assessments, candidates, bundles)
    rows, selected, used_groups = [], [], set()
    for context in CONTEXTS:
        for stratum, label, needed in QUOTAS:
            nominal = [
                pid
                for pid in packets
                if index[pid]["context_id"] == context
                and index[pid]["stratum"] == stratum
                and bundles[pid]["AI_label"] == label
            ]
            eligible = [pid for pid in nominal if label == "unsafe" or pid in questions]
            seed = stage_seed("AI00", "COMMON", f"select:{context}:{stratum}:{label}")
            ordered = sorted(eligible, key=lambda pid: digest([seed, pid]))
            picked = []
            for pid in ordered:
                group = index[pid]["group_id"]
                if group in used_groups:
                    continue
                picked.append(pid)
                used_groups.add(group)
                if len(picked) == needed:
                    break
            selected.extend(picked)
            rows.append(
                {
                    "context": context,
                    "original_case_stratum": stratum,
                    "AI_bundle_label": label,
                    "needed": needed,
                    "nominal_complete_labels": len(nominal),
                    "with_required_AI_checked_claim_QA": len(eligible),
                    "group_disjoint_selected": len(picked),
                    "shortfall": max(0, needed - len(picked)),
                }
            )
    final_questions = {}
    uniqueness_failures = []
    for pid in selected:
        if bundles[pid]["AI_label"] != "safe_for_use":
            continue
        for q in sorted(questions[pid], key=lambda q: digest(q["candidate_id"])):
            support_sources = {
                other
                for other in selected
                for a in packets[other]["artifacts"]
                if a["role"] == "external" and q["quote"] in a["text"]
            }
            if support_sources == {pid}:
                final_questions[pid] = q
                break
        if pid not in final_questions:
            uniqueness_failures.append(pid)
    ready = (
        not any(r["shortfall"] for r in rows) and not uniqueness_failures and len(selected) == 32
    )
    result = {
        "status": "AI_exploratory_readiness_only",
        "reviewed_development_inputs": len(packets),
        "memory_records_expected": sum(len(p["records"]) for p in packets.values()),
        "accepted_record_proposals": len(records),
        "complete_automated_bundles": sum(b["complete"] for b in bundles.values()),
        "AI_bundle_counts": dict(Counter(b["AI_label"] for b in bundles.values())),
        "AI_safe_sources_with_checked_claim_QA": len(questions),
        "strata": rows,
        "uniqueness_failures": uniqueness_failures,
        "exploratory_data_ready": ready,
        "human_validated_pilot_ready": False,
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "annotation_accuracy": "not_measured",
        "defense_ASR": "not_measured",
        "selected_ids": selected if ready else [],
        "final_questions": final_questions if ready else {},
    }
    out.mkdir(parents=True, mode=0o700)
    new_json(out / "readiness.json", result)
    deps = [
        prepared / "private/evaluator_case_index.jsonl",
        prepared / "private/review_packets.jsonl",
        prepared / "private/question_drafts.jsonl",
        *[p / "results_manifest.json" for p in reviews],
    ]
    new_json(
        out / "manifest.json",
        {
            "files": {"readiness.json": sha_file(out / "readiness.json")},
            "dependencies": {str(p.resolve()): sha_file(p) for p in deps},
        },
    )
    return result


def freeze_exploratory(prepared, reviews, readiness_dir, out):
    check(not out.exists(), "Exploratory freeze exists")
    result = json.loads((readiness_dir / "readiness.json").read_text())
    manifest = json.loads((readiness_dir / "manifest.json").read_text())
    for n, h in manifest["files"].items():
        check(sha_file(readiness_dir / n) == h, "Readiness changed")
    for n, h in manifest["dependencies"].items():
        check(sha_file(Path(n)) == h, "Input changed")
    check(result["exploratory_data_ready"] is True, "Required AI-label/QA composition unavailable")
    packets, records, _a, _q, bundles = collect(reviews, prepared)
    ids = result["selected_ids"]
    check(len(ids) == len(set(ids)) == 32, "Bad selection")
    index = {
        p["contribution_id"]: p
        for p in map(json.loads, (prepared / "private/evaluator_case_index.jsonl").open())
        if p["contribution_id"] in ids
    }
    out.mkdir(parents=True, mode=0o700)
    (out / "private").mkdir(mode=0o700)
    (out / "public").mkdir(mode=0o700)
    key = secrets.token_bytes(32)

    def opaque(parts):
        return hmac.new(key, canonical(parts).encode(), hashlib.sha256).hexdigest()[:24]

    new_json(out / "private/blinding_key.json", {"key": key.hex()})
    users = ["u_" + opaque(["user", i]) for i in range(2)]
    high = rng("AI00", "profile").randrange(2)
    common_ids = sorted(ids)
    ingestion = common_ids.copy()
    rng("AI00", "ingestion-order").shuffle(ingestion)
    query_order = common_ids.copy()
    rng("AI00", "base-query-order").shuffle(query_order)
    unsafe = sorted(pid for pid in ids if bundles[pid]["AI_label"] == "unsafe")
    root = rng("AI00", "root").choice(unsafe)
    for name, source_odds, batch_odds in [
        ("strong_localized", 9, 9),
        ("strong_distributed", 9, 1),
        ("uninformative", 1, 1),
    ]:
        assigned = {}
        hidden = {}
        for ci, context in enumerate(CONTEXTS):
            slots, weights = [], []
            for ui, user in enumerate(users):
                is_high = ui == (high if ci == 0 else 1 - high)
                hot = rng("AI00", f"hot-batch:{context}:{ui}").randrange(2)
                for bi in range(2):
                    batch = "b_" + opaque([user, context, bi])
                    hidden[batch] = {"high": is_high, "hot": bi == hot}
                    for _position in range(4):
                        slots.append(
                            {"contributor_id": user, "context_id": context, "batch_id": batch}
                        )
                        weights.append(
                            Fraction(source_odds) ** int(is_high)
                            * Fraction(batch_odds) ** int(bi == hot)
                        )
            random = rng("AI00", f"slot-assignment:{context}", name)
            chosen = set(weighted_subset(weights, 8, random))
            for label, indices in [
                ("unsafe", sorted(chosen)),
                ("safe_for_use", sorted(set(range(16)) - chosen)),
            ]:
                rows = sorted(
                    pid
                    for pid in ids
                    if index[pid]["context_id"] == context and bundles[pid]["AI_label"] == label
                )
                random.shuffle(rows)
                for pid, i in zip(rows, indices, strict=True):
                    assigned[pid] = slots[i]
        reserved = [root]
        a = assigned[root]

        def pick(stage, predicate, reserved=reserved, assigned=assigned):
            choices = sorted(pid for pid in ids if pid not in reserved and predicate(assigned[pid]))
            selected = rng("AI00", stage).choice(choices)
            reserved.append(selected)
            return selected

        pick("audit-1", lambda m, a=a: m["batch_id"] == a["batch_id"])
        pick(
            "audit-2",
            lambda m, a=a: (
                m["contributor_id"] == a["contributor_id"]
                and m["context_id"] == a["context_id"]
                and m["batch_id"] != a["batch_id"]
            ),
        )
        other_batches = sorted(
            {
                m["batch_id"]
                for m in assigned.values()
                if m["contributor_id"] == a["contributor_id"] and m["context_id"] != a["context_id"]
            }
        )
        target = rng("AI00", "audit-3-batch").choice(other_batches)
        third = pick("audit-3", lambda m, target=target: m["batch_id"] == target)
        a3 = assigned[third]
        pick(
            "audit-4",
            lambda m, a3=a3: (
                m["contributor_id"] == a3["contributor_id"]
                and m["context_id"] == a3["context_id"]
                and m["batch_id"] != a3["batch_id"]
            ),
        )
        episode = "ep_" + opaque([name])
        public = []
        audits = []
        for pid in ingestion:
            public.append(
                {
                    "event": "ingest",
                    "contribution_id": pid,
                    **assigned[pid],
                    "artifacts": [
                        {
                            **{
                                k: artifact[k]
                                for k in ("artifact_id", "role", "text", "content_hash")
                            },
                            "origin_id": "user"
                            if artifact["role"] == "principal"
                            else assigned[pid]["contributor_id"],
                        }
                        for artifact in packets[pid]["artifacts"]
                    ],
                    "task_principal": "user",
                    "attribution_assumption": "trusted_synthetic_external_origin_only",
                    "allowed_readers": ["user", "audit_service"],
                    "policy_version": 1,
                }
            )
        for i, pid in enumerate(reserved):
            audits.append(
                {
                    "ticket_id": "t_" + opaque([name, i]),
                    "contribution_id": pid,
                    "use_id": packets[pid]["use_id"],
                    "AI_verdict": bundles[pid]["AI_label"],
                    "annotation_source": "llm",
                    "independently_verified": False,
                    "records": [records[r["record_id"]] for r in packets[pid]["records"]],
                }
            )
        probes = [pid for pid in query_order if pid not in reserved]
        public += [
            {"event": "query", "contribution_id": pid, "text": index[pid]["retrieval_query"]}
            for pid in probes
        ]
        utility_ids = [pid for pid in probes if bundles[pid]["AI_label"] == "safe_for_use"]
        rng("AI00", "grounded-query-order").shuffle(utility_ids)
        public += [
            {
                "event": "utility_query",
                "contribution_id": pid,
                "text": result["final_questions"][pid]["question"],
            }
            for pid in utility_ids
        ]
        new_json(
            out / "public" / (episode + ".json"),
            {
                "episode_id": episode,
                "events": public,
                "audit_delivery": "controller-only tickets revealed after ingestion before probes",
            },
        )
        new_json(
            out / "private" / (episode + ".json"),
            {
                "scenario": name,
                "profiles": hidden,
                "audits": audits,
                "reserved_audit_ids": reserved,
                "original_probe_ids": probes,
                "utility_probe_ids": utility_ids,
                "gold_cases": {pid: index[pid] for pid in probes},
                "utility_references": {pid: result["final_questions"][pid] for pid in utility_ids},
                "arms": ["R", "C", "M", "S"],
                "feedback_budget_each": 5,
                "arms_receive_identical_data_and_feedback": True,
            },
        )
    new_json(
        out / "private/selection.json",
        {
            "source_ids": ids,
            "label_basis": "AI_Z_hat_not_human_Z",
            "human_verified_labels": 0,
            "human_validated_questions": 0,
            "defense_execution_enabled": False,
        },
    )
    files = {str(p.relative_to(out)): sha_file(p) for p in out.rglob("*.json")}
    new_json(
        out / "manifest.json",
        {
            "schema": "AI_exploratory_dataset_only",
            "files": files,
            "hash": digest(files),
            "scientific_human_validated": False,
            "execution_enabled": False,
        },
    )
    return {
        "status": "AI_exploratory_data_frozen",
        "contributions": 32,
        "overlays": 3,
        "human_verified_labels": 0,
        "execution_enabled": False,
    }
