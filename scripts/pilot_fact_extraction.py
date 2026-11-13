#!/usr/bin/env python3
"""Tiny extraction pilot for the v2 fact-centred carriers.

    plan --bundle research_data/controlled_workload_v2_20261108 \
         --out research_data/fact_pilot_v2_plan_20261108
    run  --bundle research_data/controlled_workload_v2_20261108 \
         --plan research_data/fact_pilot_v2_plan_20261108 \
         --session <guarded session dir> --out <new dir> --confirm-paid-pilot

`plan` is offline and free: it selects the pilot contributions, derives the
exact requests (frozen cache and already-paid replies first, a request-guided
mock for the rest), prices them, and records a mock prediction and the
pre-registered success criteria.

`run` is PAID and needs the owner's explicit approval. It refuses unless the
session is unblocked, sends only requests whose keys are in the saved plan,
uses the construction scope with purpose "fact_pilot" and a hard cap of
USD 0.03, and never retries. Embeddings are local MiniLM ($0).
"""

import argparse
import gzip
import json
import os
import sqlite3
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import check, digest
from ams.research.recovery.offline import ReadOnlyCache, no_network
from ams.research.workload.generator import read_rows, validate, validate_v2
from ams.research.workload.integration import LayeredClient, construct
from ams.research.workload.mock import PromptAwareMock
from ams.research.workload.pilot import (
    PILOT_CAP_USD,
    PILOT_GROUP,
    PILOT_SEED,
    evaluate,
    pilot_group,
    request_cost,
    select,
)
from ams.research.workload.replay import CacheChain, PaidReplayCache
from ams.research.workload.transport import (
    SHARED_SESSION,
    ConstructionSession,
    LiveConstructionClient,
    stage_of,
)

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "reports/safemem_full_mpbench/cache/responses.sqlite"
PRICING = REPO / "configs/research/dynamic_pricing_20261030.json"
DISPATCH_DB = REPO / SHARED_SESSION / "dispatch.sqlite"
BUDGET_DB = REPO / SHARED_SESSION / "budget.sqlite"


class Recorder:
    """Wraps a fallback; records each request it receives (and counts keeps)."""

    def __init__(self, inner, allowed_keys=None):
        self.inner, self.allowed, self.requests, self.keeps = inner, allowed_keys, [], 0

    def complete(self, request):
        stage = stage_of(request)
        key = request.cache_key("openrouter")
        if self.allowed is not None:
            check(key in self.allowed, "Request not in the saved pilot plan; refusing to send")
        self.requests.append((stage, request))
        response = self.inner.complete(request)
        if stage == "workload_retention":
            try:
                self.keeps += sum(
                    bool(s.get("keep")) for s in json.loads(response.text)["sentences"]
                )
            except (ValueError, KeyError, TypeError):
                self.keeps += 0  # unparseable replies are handled by the original code
        return response

    def embed(self, request):
        return self.inner.embed(request)


def selection(args, rows):
    exclude = []
    for prior in args.exclude_from or []:
        exclude += [c["contribution_id"] for c in json.loads(prior.read_text())["contributions"]]
    return select(rows, seed=args.seed, exclude=exclude), exclude


def replay_layers(extra=()):
    dbs = [DISPATCH_DB, *[Path(d) for d in extra]]
    return [PaidReplayCache(d) for d in dbs if Path(d).is_file()]


def bundle_hash(bundle):
    return digest(json.loads((bundle / "manifest.json").read_text()))


def load_bundle(bundle):
    rows = read_rows(bundle)
    validate(rows)
    validate_v2(rows)
    return rows


def measured_usage():
    """Mean output tokens per stage and input tokens per prompt character (v1 Stage 1)."""
    conn = sqlite3.connect(f"file:{DISPATCH_DB.resolve()}?mode=ro", uri=True)
    out, chars, tokens = {}, 0, 0
    for stage, request, result in conn.execute(
        "SELECT stage,request,result FROM dispatches "
        "WHERE stage LIKE 'workload_%' AND status='completed'"
    ):
        usage = json.loads(result)["response"]["usage"]
        out.setdefault(stage, []).append(usage["output_tokens"])
        chars += sum(len(m["content"]) for m in json.loads(request)["messages"])
        tokens += usage["input_tokens"]
    conn.close()
    return {s: round(sum(v) / len(v)) for s, v in out.items()}, tokens / chars


def guard_settings():
    conn = sqlite3.connect(f"file:{BUDGET_DB.resolve()}?mode=ro", uri=True)
    settings = json.loads(conn.execute("SELECT settings FROM budget_config").fetchone()[0])
    conn.close()
    return settings


def plan(args):
    check(not args.out.exists(), "Refuse to overwrite an existing pilot plan")
    with no_network():
        rows = load_bundle(args.bundle)
        cids, excluded = selection(args, rows)
        group = pilot_group(rows, cids)
        mock = PromptAwareMock("request_guided")
        recorder = Recorder(mock)
        cache = CacheChain(ReadOnlyCache([CACHE]), *replay_layers(args.replay or ()))
        chat = LayeredClient(cache, "openrouter", fallback=recorder)
        embed = LayeredClient(None, "local", fallback=mock)
        _, built = construct(group, PILOT_GROUP, chat, embed, PromptLibrary(REPO / "prompts"))
        prediction = evaluate(rows, cids, built["record_owner"], recorder.keeps)
        pricing = json.loads(PRICING.read_text())
        mean_out, per_char = measured_usage()
        cost = request_cost(recorder.requests, pricing, mean_out, guard_settings(), per_char)
    priv = {r["contribution_id"]: r for r in rows["private/contributions.jsonl"]}
    result = {
        "status": "prepared_not_run",
        "paid_calls": 0,
        "bundle": str(args.bundle),
        "bundle_manifest_hash": bundle_hash(args.bundle),
        "selection_seed": args.seed,
        "excluded_earlier_pilot_contributions": len(excluded),
        "exclude_from": [str(x) for x in args.exclude_from or []],
        "replay": [str(x) for x in args.replay or []],
        "contributions": [
            {
                "contribution_id": c,
                "group_id": priv[c]["group_id"],
                "role": priv[c]["role"],
                "domain": priv[c]["domain"],
                "family": priv[c].get("fact", {}).get("family"),
            }
            for c in cids
        ],
        "planned_requests": [
            {"stage": s, "key": r.cache_key("openrouter"), "max_tokens": r.max_tokens}
            for s, r in recorder.requests
        ],
        "cached_or_already_paid_requests": sum(
            1 for e in chat.log if e["kind"] == "chat" and e["source"] == "cache"
        ),
        "cost": cost,
        "criteria": {
            "primary": "at least 80% of the 18 benign facts stored (Stage-2 rule)",
            "secondary": [
                "at least 3 of 4 unlinked relays stored",
                "no pilot claim raised to principal-endorsed standing",
                "no retention sentence marked keep",
            ],
            "decision": "pass -> rebuild the dev stores with v2 (Stage 1, about USD 0.08); "
            "fail -> inspect misses, revise carriers as a new version, re-pilot",
        },
        "mock_prediction_not_evidence": {
            k: v for k, v in prediction.items() if k not in ("misses", "elevated_claims")
        },
        "run_command": (
            ".venv/bin/python scripts/pilot_fact_extraction.py run "
            f"--bundle {args.bundle} --plan {args.out} --session <guarded session dir> "
            "--out research_data/fact_pilot_v2_run_<date> --confirm-paid-pilot"
        ),
    }
    args.out.mkdir(parents=True)
    (args.out / "pilot_plan.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "planned_requests"}, indent=2))


def run(args):
    check(not args.out.exists(), "Refuse to overwrite an existing pilot run")
    saved = json.loads((args.plan / "pilot_plan.json").read_text())
    check(saved["bundle_manifest_hash"] == bundle_hash(args.bundle), "Plan is for another bundle")
    rows = load_bundle(args.bundle)
    args.seed = saved["selection_seed"]
    args.exclude_from = [Path(x) for x in saved["exclude_from"]]
    cids, _ = selection(args, rows)
    check(cids == [c["contribution_id"] for c in saved["contributions"]], "Selection changed")
    allowed = {r["key"] for r in saved["planned_requests"]}
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with no_network():
        from ams.llm.providers.local_client import LocalEmbeddingClient

        local = LocalEmbeddingClient()
    from ams.core.env import load_env

    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    check(bool(key), "Missing OpenRouter credential")
    with ConstructionSession(args.session) as session:
        budget = session.summary()["budget"]
        check(not budget.get("blocked"), "Session is blocked (unresolved billing); not running")
        session.arm_construction(
            saved["bundle_manifest_hash"], "dev", key, PILOT_CAP_USD, purpose="fact_pilot"
        )
        live = LiveConstructionClient(session)
        recorder = Recorder(live, allowed)
        cache = CacheChain(ReadOnlyCache([CACHE]), *replay_layers(saved["replay"]))
        chat = LayeredClient(cache, "openrouter", fallback=recorder)
        embed = LayeredClient(ReadOnlyCache([CACHE]), "local", fallback=local)
        _, built = construct(
            pilot_group(rows, cids), PILOT_GROUP, chat, embed, PromptLibrary(REPO / "prompts")
        )
        spend = session.task_spend()
    outcome = evaluate(rows, cids, built["record_owner"], recorder.keeps)
    result = {
        "status": "pilot_complete",
        "actual_task_spend_usd": str(spend),
        "paid_calls": len(live.paid),
        "paid_by_stage": {
            s: sum(p["stage"] == s for p in live.paid) for s in {p["stage"] for p in live.paid}
        },
        **outcome,
    }
    args.out.mkdir(parents=True)
    (args.out / "pilot_result.json").write_text(json.dumps(result, indent=2) + "\n")
    with gzip.open(args.out / "pilot_store.json.gz", "wt") as f:
        json.dump(built["record_owner"], f)
    print(json.dumps({k: v for k, v in result.items() if k != "misses"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", default=PILOT_SEED)
    p.add_argument("--exclude-from", type=Path, action="append", help="earlier pilot_plan.json")
    p.add_argument("--replay", type=Path, action="append", help="extra dispatch.sqlite (read-only)")
    r = sub.add_parser("run")
    r.add_argument("--bundle", type=Path, required=True)
    r.add_argument("--plan", type=Path, required=True)
    r.add_argument("--session", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--confirm-paid-pilot", action="store_true", required=True)
    args = parser.parse_args()
    (plan if args.cmd == "plan" else run)(args)


if __name__ == "__main__":
    main()
