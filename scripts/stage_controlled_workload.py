#!/usr/bin/env python3
"""Controlled workload Stage 1 (PAID, owner-approved dev only) and Stage 2 (free).

    stage1 --bundle research_data/controlled_workload_v1_20261108 --split dev \
           --out research_data/controlled_workload_stage1_dev_v1_20261108 --confirm-paid-dev-stage1
    stage2 --bundle <bundle> --stage1 <stage1 dir> --out <new dir>
    stage3 --bundle <bundle> --stage1 <stage1 dir> --out <dir> --session <dir> \
           (--mock | --confirm-paid-dev-stage3)

Stage 1 builds the real dev stores: frozen reproduction-cache replies first
($0), cache misses through the guarded construction scope on the shared USD 30
session (hard task cap USD 0.15), embeddings with the local MiniLM ($0). Each
group's store is saved as soon as it is built; rerunning reuses saved stores
and already paid replies, never paying twice.

Stage 2 is offline: extraction yield, classification and retrieval exposure.

Stage 3 runs static (original SAFE-Mem), R, C, M, S and no-memory over the
Stage-1 stores: real answers (original typed answer prompt), the original
conflict checker and the original attack judge, through the guarded "stage3"
scope (dev only, hard cap USD 0.70, one attempt per request, an identical
request is answered once and reused). `--mock` runs the identical paid code
path against httpx.MockTransport in a fresh, separate session (mock and live
billing can never share a session). The journal is append-only: rerunning
with the same --out resumes and verifies every saved outcome.
"""

import argparse
import gzip
import json
import os
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import check, digest
from ams.research.recovery.offline import ReadOnlyCache, no_network
from ams.research.workload.generator import read_rows, validate
from ams.research.workload.integration import LayeredClient, build_states
from ams.research.workload.replay import CacheChain, PaidReplayCache
from ams.research.workload.stage2 import classification, extraction_yield, retrieval_exposure
from ams.research.workload.transport import (
    DEFAULT_CAP_USD,
    SHARED_SESSION,
    ConstructionSession,
    LiveConstructionClient,
)

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "reports/safemem_full_mpbench/cache/responses.sqlite"


def role(max_tokens):
    return "classifier" if max_tokens == 24 else "extraction" if max_tokens == 900 else "retention"


def load_store(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def owner_approval(args):
    """Test split only: the owner-approval file, after re-verifying the frozen protocol."""
    if args.split != "test":
        return None
    import subprocess
    import sys

    check(args.owner_approval is not None, "The locked test needs --owner-approval")
    approval = json.loads(args.owner_approval.read_text())
    subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/freeze_locked_protocol.py"),
            "verify",
            "--protocol",
            str(REPO / approval["protocol_path"]),
        ],
        check=True,
    )
    frozen = json.loads((REPO / approval["protocol_path"]).read_text())
    check(frozen["protocol_digest"] == approval["protocol_digest"], "Approval names another freeze")
    return approval


def stage1(args):
    check(
        (args.split == "dev" and args.confirm_paid_dev_stage1)
        or (args.split == "test" and args.confirm_locked_test),
        "Pass --confirm-paid-dev-stage1 (dev) or --confirm-locked-test (test)",
    )
    rows = read_rows(args.bundle)
    validate(rows)
    manifest_hash = digest(json.loads((args.bundle / "manifest.json").read_text()))
    groups = sorted(
        {r["group_id"] for r in rows["private/contributions.jsonl"] if r["split"] == args.split}
    )
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with no_network():  # the local embedding model must load from disk only
        from ams.llm.providers.local_client import LocalEmbeddingClient

        local = LocalEmbeddingClient()
    from ams.core.env import load_env

    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    check(bool(key), "Missing OpenRouter credential")
    out = args.out
    (out / "stores").mkdir(parents=True, exist_ok=True)
    frozen, prompts = ReadOnlyCache([CACHE]), PromptLibrary(REPO / "prompts")
    replays = [PaidReplayCache(d) for d in args.replay or [] if d.is_file()]
    cache = CacheChain(frozen, *replays)
    per_group = {}
    with ConstructionSession(args.session) as session:
        before = session.summary()["budget"]
        session.arm_construction(
            manifest_hash, args.split, key, Decimal(args.cap), approval=owner_approval(args)
        )
        live = LiveConstructionClient(session)
        for gid in groups:
            path = out / "stores" / f"{gid}.json.gz"
            if path.exists():
                store = load_store(path)
            else:
                chat = LayeredClient(cache, "openrouter", fallback=live)
                embed = LayeredClient(frozen, "local", fallback=local)
                store = build_states(rows, gid, chat, embed, prompts)
                tmp = path.with_suffix(".tmp")
                with gzip.open(tmp, "wt") as f:
                    json.dump(store, f)
                tmp.rename(path)
            log = store["construction_log"]
            per_group[gid] = {
                "chat": dict(
                    Counter(f"{role(e['max_tokens'])}:{e['source']}" for e in log["chat"])
                ),
                "embed": dict(Counter(e["source"] for e in log["embed"])),
            }
            print(
                f"stage1 {gid}: {per_group[gid]['chat']} spend {session.task_spend()}", flush=True
            )
        after = session.summary()["budget"]
        task_spend = session.task_spend()
        rows_paid = session.db.execute(
            "SELECT stage,COUNT(*),SUM(CAST(json_extract(result,'$.actual_paid_usd') AS REAL)) "
            "FROM dispatches WHERE stage LIKE 'workload_%' AND status='completed' GROUP BY stage"
        ).fetchall()
        failed = session.db.execute(
            "SELECT COUNT(*) FROM dispatches WHERE stage LIKE 'workload_%' AND status!='completed'"
        ).fetchone()[0]
    summary = {
        "status": "stage1_complete",
        "bundle": str(args.bundle),
        "split": args.split,
        "groups": groups,
        "bundle_manifest_hash": manifest_hash,
        "task_cap_usd": args.cap,
        "actual_task_spend_usd": str(task_spend),
        "paid_dispatches_by_stage": {
            s: {"calls": n, "usd": round(c or 0, 8)} for s, n, c in rows_paid
        },
        "failed_or_unresolved_dispatches": failed,
        "paid_this_run_by_stage": dict(Counter(x["stage"] for x in live.paid)),
        "note": "paid_dispatches_by_stage counts every workload dispatch in the session "
        "(including pilots); actual_task_spend_usd is this Stage-1 scope only",
        "budget_before": {k: before[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "budget_after": {k: after[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "per_group_requests": per_group,
        "embeddings": "local MiniLM (cache first); no paid embeddings",
        "session": str(args.session),
        "replayed_paid_replies_from": [str(d) for d in args.replay or []],
        "cache_hits": dict(cache.counts),
    }
    (out / "stage1_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))


def _mock_transport():
    from types import SimpleNamespace

    import httpx

    from ams.research.workload.mock import PromptAwareMock

    mock = PromptAwareMock("request_guided")

    def handler(request):
        body = json.loads(request.content)
        fake = SimpleNamespace(messages=[SimpleNamespace(content=body["messages"][-1]["content"])])
        text = mock.complete(fake).text
        return httpx.Response(
            200,
            json={
                "id": "gen-offline-stage3",
                "model": "openai/gpt-4o-mini",
                "object": "chat.completion",
                "created": 1,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": text},
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": "0.00001",
                },
            },
        )

    return httpx.MockTransport(handler)


def stage3(args):
    from ams.research.execution.session import ExecutionSession
    from ams.research.workload.analysis import analyse, markdown
    from ams.research.workload.generator import validate_v2
    from ams.research.workload.runner import run

    check(
        args.mock or args.confirm_paid_dev_stage3 or args.confirm_locked_test,
        "Pass --mock, --confirm-paid-dev-stage3 or --confirm-locked-test",
    )
    check(args.split == "dev" or args.confirm_locked_test, "Test split needs --confirm-locked-test")
    check(not (args.mock and args.split == "test"), "No mock runs on the held-out test split")
    rows = read_rows(args.bundle)
    validate(rows)
    manifest = json.loads((args.bundle / "manifest.json").read_text())
    if manifest["version"] != "controlled-workload-v1":
        validate_v2(rows)
    manifest_hash = digest(manifest)
    built = json.loads((args.stage1 / "stage1_summary.json").read_text())
    check(built["bundle_manifest_hash"] == manifest_hash, "Stage-1 stores are from another bundle")
    check(built["split"] == args.split, "Stage-1 stores are from another split")
    stores = [load_store(p) for p in sorted((args.stage1 / "stores").glob("*.json.gz"))]
    check(sorted(s["group_id"] for s in stores) == built["groups"], "Incomplete Stage-1 stores")
    if args.groups:
        stores = stores[: args.groups]
    groups = [s["group_id"] for s in stores]
    if args.mock:
        if not args.session.exists():
            ExecutionSession.create(args.session, plan_hash=manifest_hash).close()
    else:
        from ams.core.env import load_env

        load_env()
        key = os.environ.get("OPENROUTER_API_KEY")
        check(bool(key), "Missing OpenRouter credential")
    with ConstructionSession(args.session) as session:
        before = session.summary()["budget"]
        check(not before["blocked"], "Session is blocked (unresolved billing); not running")
        if args.mock:
            session.arm_construction_mock(
                manifest_hash, "dev", _mock_transport(), Decimal(args.cap), purpose="stage3"
            )
        else:
            session.arm_construction(
                manifest_hash,
                args.split,
                key,
                Decimal(args.cap),
                purpose="stage3",
                approval=owner_approval(args),
            )
        run(rows, stores, session, args.out, split=args.split)
        spend = session.task_spend()
        after = session.summary()["budget"]
        by_stage = session.db.execute(
            "SELECT stage,status,COUNT(*) FROM dispatches "
            "WHERE stage IN ('workload_answer','workload_no_memory_answer',"
            "'workload_conflict','workload_judge') GROUP BY stage,status"
        ).fetchall()
    with sqlite3.connect(f"file:{(args.out / 'queries.sqlite').resolve()}?mode=ro", uri=True) as db:
        outcomes = [
            json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes ORDER BY rowid")
        ]
    targets = {p["probe_id"]: p.get("target") for p in rows["private/probes.jsonl"]}
    result = analyse(outcomes, groups, targets)
    summary = {
        "status": "stage3_complete",
        "mode": "mock" if args.mock else "live",
        "bundle": str(args.bundle),
        "bundle_manifest_hash": manifest_hash,
        "groups": groups,
        "outcome_rows": len(outcomes),
        "task_cap_usd": args.cap,
        "actual_task_spend_usd": "0 (mock)" if args.mock else str(spend),
        "dispatches_by_stage_and_status": [list(r) for r in by_stage],
        "budget_before": {k: before[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "budget_after": {k: after[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "session": str(args.session),
        "integrity": result["integrity"],
    }
    (args.out / "stage3_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (args.out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.out / "analysis.md").write_text(markdown(result) + "\n")
    print(markdown(result))
    print(json.dumps(summary, indent=2, default=str))


def stage2(args):
    check(not args.out.exists(), "Refuse to overwrite an existing Stage-2 report")
    with no_network():
        rows = read_rows(args.bundle)
        validate(rows)
        stores = [load_store(p) for p in sorted((args.stage1 / "stores").glob("*.json.gz"))]
        check(bool(stores), "No Stage-1 stores")
        yields, misses = extraction_yield(rows, stores)
        classes = classification(rows, stores)
        exposure, conflicts = retrieval_exposure(rows, stores)
    result = {
        "status": "stage2_complete",
        "paid_calls": 0,
        "groups": [s["group_id"] for s in stores],
        "extraction_yield": yields,
        "extraction_miss_examples": misses,
        "classification_by_probe_kind": classes,
        "retrieval_exposure": exposure,
        "conflict_checks_answered_by_placeholder": conflicts,
    }
    args.out.mkdir(parents=True)
    (args.out / "stage2_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in result.items() if k != "extraction_miss_examples"}, indent=2)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("stage1")
    s1.add_argument("--bundle", type=Path, required=True)
    s1.add_argument("--split", choices=["dev", "test"], required=True)
    s1.add_argument("--owner-approval", type=Path, default=None)
    s1.add_argument("--out", type=Path, required=True)
    s1.add_argument("--cap", default=str(DEFAULT_CAP_USD))
    s1.add_argument("--confirm-paid-dev-stage1", action="store_true")
    s1.add_argument("--confirm-locked-test", action="store_true")
    s1.add_argument("--session", type=Path, default=REPO / SHARED_SESSION)
    s1.add_argument(
        "--replay", type=Path, action="append", help="dispatch.sqlite of already-paid replies"
    )
    s2 = sub.add_parser("stage2")
    s2.add_argument("--bundle", type=Path, required=True)
    s2.add_argument("--stage1", type=Path, required=True)
    s2.add_argument("--out", type=Path, required=True)
    s3 = sub.add_parser("stage3")
    s3.add_argument("--bundle", type=Path, required=True)
    s3.add_argument("--stage1", type=Path, required=True)
    s3.add_argument("--out", type=Path, required=True)
    s3.add_argument("--session", type=Path, required=True)
    s3.add_argument("--cap", default="0.70")
    s3.add_argument("--groups", type=int, default=None)
    s3.add_argument("--mock", action="store_true")
    s3.add_argument("--confirm-paid-dev-stage3", action="store_true")
    s3.add_argument("--split", choices=["dev", "test"], default="dev")
    s3.add_argument("--owner-approval", type=Path, default=None)
    s3.add_argument("--confirm-locked-test", action="store_true")
    args = parser.parse_args()
    {"stage1": stage1, "stage2": stage2, "stage3": stage3}[args.cmd](args)


if __name__ == "__main__":
    main()
