#!/usr/bin/env python3
"""PAID (owner-approved 12 Nov 2026) evaluation of published defences on the dev split.

    published_paid.py memlineage --out <dir> --confirm-paid             # SensitiveAction, cap $0.05
    published_paid.py amemguard  --out <dir> --groups G-D00 --confirm-paid   # pilot, cap $1.00
    published_paid.py sanitiser  --out <dir> --confirm-paid             # cap $0.50
    (--mock: same guarded code path against an offline httpx mock, separate session)

Every request goes through a guarded `ConstructionSession` scope of its own purpose
(published_memlineage / published_amemguard / published_sanitiser): BudgetGuard
reservation, write-before-dispatch journal, one attempt per request, identical
requests answered once, halt on unknown billing, persisted hard cap. Requests must
match the method's exact shape (`transport.published_stage`).

The published methods are condition-invariant (they filter original SAFE-Mem's
retrieval, identical in all sweep conditions), so each probe is evaluated once;
`analyse_published_paid.py` broadcasts the result over the 66 sweep conditions.
Per-group results are written as soon as a group finishes; rerunning resumes and
reuses already-paid replies.
"""

import argparse
import gzip
import json
import os
from decimal import Decimal
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import check, digest
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import resolve_models
from ams.research.recovery.offline import CHAT_MODEL
from ams.research.workload import published as P
from ams.research.workload.generator import read_rows
from ams.research.workload.integration import group_rows
from ams.research.workload.runner import prepare_state
from ams.research.workload.stage2 import ConflictPlaceholderSession
from ams.research.workload.transport import (
    PUBLISHED_PURPOSES,
    ConstructionSession,
    GuardedPublishedClient,
)

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "research_data/controlled_workload_v3_20261108"
STAGE1 = REPO / "research_data/controlled_workload_stage1_dev_v3_20261108"
SESSION = REPO / "research_data/controlled_workload_session_v2_20261108"
PURPOSE = {"memlineage": "published_memlineage", "amemguard": "published_amemguard",
           "sanitiser": "published_sanitiser"}  # fmt: skip


def load_store(p):
    with gzip.open(p, "rt") as f:
        return json.load(f)


def mock_transport():
    import httpx

    def handler(request):
        body = json.loads(request.content)
        last = body["messages"][-1]["content"]
        if "SENSITIVE or ORDINARY" in last:
            text = "ORDINARY"
        elif "[STATUS]" in last or "memory log" in body["messages"][0]["content"]:
            text = "[STATUS]: safe"
        else:
            text = '{"consistent_ids": [0], "inconsistent_ids": []}'
        return httpx.Response(200, json={
            "id": "gen-offline-published", "model": "openai/gpt-4o-mini",
            "object": "chat.completion", "created": 1,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                      "cost": 0.0000001}})  # fmt: skip

    return httpx.MockTransport(handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("method", choices=sorted(PURPOSE))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", nargs="*")
    ap.add_argument("--confirm-paid", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--session", type=Path, default=SESSION)
    ap.add_argument("--resume-scope", action="store_true",
                    help="sanitiser only: use the separately capped resume scope")
    ap.add_argument("--new-session", action="store_true",
                    help="create --session if missing (owner-approved replacement session)")
    ap.add_argument("--cap", type=Decimal, help="lower hard cap than the purpose maximum")
    args = ap.parse_args()
    check(args.confirm_paid != args.mock, "Pass exactly one of --confirm-paid / --mock")
    check(not (args.mock and args.session == SESSION), "Mock runs need a separate --session")
    purpose = PURPOSE[args.method] + ("_resume" if args.resume_scope else "")
    cap = PUBLISHED_PURPOSES[purpose]
    if args.cap is not None:
        check(Decimal(0) < args.cap <= cap, "Cap above the purpose maximum")
        cap = args.cap
    rows = read_rows(BUNDLE)
    manifest_hash = digest(json.loads((BUNDLE / "manifest.json").read_text()))
    stores = [load_store(p) for p in sorted((STAGE1 / "stores").glob("*.json.gz"))]
    check(all(s["group_id"].startswith("G-D") for s in stores), "Dev split only")
    if args.groups:
        stores = [s for s in stores if s["group_id"] in args.groups]
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if args.mock or args.new_session:
        from ams.research.execution.session import ExecutionSession

        if not args.session.exists():
            ExecutionSession.create(args.session, plan_hash=manifest_hash).close()
    if not args.mock:
        from ams.core.env import load_env

        load_env()
        check(bool(os.environ.get("OPENROUTER_API_KEY")), "Missing OpenRouter credential")
    prompts = PromptLibrary()
    with ConstructionSession(args.session) as session:
        before = session.summary()["budget"]
        check(not before["blocked"], "Session is blocked (unresolved billing); not running")
        if args.mock:
            session.arm_construction_mock(manifest_hash, "dev", mock_transport(), cap,
                                          purpose=purpose)  # fmt: skip
        else:
            session.arm_construction(manifest_hash, "dev", os.environ["OPENROUTER_API_KEY"],
                                     cap, purpose=purpose)  # fmt: skip
        client = GuardedPublishedClient(session)
        if args.method == "memlineage":
            from ams.baselines.memlineage import SensitiveAction

            sens = SensitiveAction(client=client, model=CHAT_MODEL, prompts=prompts)
            questions = sorted({q["question"] for s in stores
                                for q in group_rows(rows, s["group_id"])["probes"]})  # fmt: skip
            verdicts = {}
            for q in questions:
                sens(q)
                verdicts[q] = client.last_text
            (args.out / "sensitive_action_verdicts.json").write_text(
                json.dumps(verdicts, indent=2, sort_keys=True) + "\n")  # fmt: skip
        else:
            from ams.baselines.amemguard import AMemGuard
            from ams.baselines.amemguard_borrowed import LLMSanitiser

            defence = (AMemGuard(model=CHAT_MODEL, client=client) if args.method == "amemguard"
                       else LLMSanitiser(client, model=CHAT_MODEL))  # fmt: skip
            placeholder = ConflictPlaceholderSession()
            with memoized_evidence_revisions():
                for store in stores:
                    gid = store["group_id"]
                    target = args.out / f"{args.method}_{gid}.jsonl"
                    if target.exists():
                        continue
                    group = group_rows(rows, gid)
                    state = prepare_state(store["snapshots"]["localized"], [], "static")
                    resolve_models(state, placeholder)
                    out = []
                    for probe in group["probes"]:
                        entries = P.retrieve(state, store, probe["question"])
                        res = P.apply(defence, store, group, probe["question"], entries,
                                      text_from_defence=args.method == "sanitiser")  # fmt: skip
                        priv = group["private_probes"][probe["probe_id"]]
                        out.append({
                            "group_id": gid, "probe_id": probe["probe_id"], "kind": priv["kind"],
                            "n_entries": len(entries), "kept": res["kept"],
                            "flagged": res["flagged"], "reason": res["reason"],
                            **P.exposure_row(store, group, probe, res["kept_entries"]),
                            "static": P.exposure_row(store, group, probe, entries)})  # fmt: skip
                    tmp = target.with_suffix(".tmp")
                    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out))
                    tmp.rename(target)
                    print(f"{gid} done; task spend so far {session.task_spend()}", flush=True)
        spend, after = session.task_spend(), session.summary()["budget"]
    summary = {
        "method": args.method, "purpose": purpose, "mode": "mock" if args.mock else "live",
        "cap_usd": str(cap), "task_spend_usd": str(spend),
        "calls_this_run": len(client.paid), "groups": [s["group_id"] for s in stores],
        "budget_before": {k: before[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "budget_after": {k: after[k] for k in ("used_usd", "remaining_usd", "held_usd")},
    }  # fmt: skip
    (args.out / f"{args.method}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    check(Decimal(spend) <= cap, "Cap exceeded")


if __name__ == "__main__":
    main()
