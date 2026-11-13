#!/usr/bin/env python3
"""Offline cost estimate for the locked test evaluation (no API call, no outcome).

Stage 1 (construction): the real SAFE-Mem write path runs over every test group
with the frozen reproduction cache and already-paid replies first; any other
request is answered by a mock *only so construction can proceed* and is counted
as a request that would be paid. No answer, judge or outcome is produced, so no
test result exists or is inspected; the mock stores are discarded.

Stage 3 (answers, conflict checks, judges): scaled from the measured dev Stage 3
(unique requests and USD per group).

Usage: estimate_locked_test_cost.py --bundle <v4> --split test --out <new json>
"""

import argparse
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import check
from ams.research.recovery.offline import ReadOnlyCache, no_network
from ams.research.workload.generator import read_rows, validate, validate_v2
from ams.research.workload.integration import LayeredClient, build_states
from ams.research.workload.mock import PromptAwareMock
from ams.research.workload.replay import CacheChain, PaidReplayCache
from ams.research.workload.transport import stage_of

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "reports/safemem_full_mpbench/cache/responses.sqlite"
PRICING = REPO / "configs/research/dynamic_pricing_20261030.json"
LEDGERS = [
    REPO / "research_data/dynamic_execution_prep_v1_20261031/session/dispatch.sqlite",
    REPO / "research_data/controlled_workload_session_v2_20261108/dispatch.sqlite",
]
DEV_STAGE3 = REPO / "research_data/controlled_workload_stage3_dev_v3_20261108/stage3_summary.json"


class Counting:
    def __init__(self, inner):
        self.inner, self.requests = inner, []

    def complete(self, request):
        self.requests.append((stage_of(request), request))
        return self.inner.complete(request)

    def embed(self, request):
        return self.inner.embed(request)


def measured():
    """Output tokens per stage and input tokens per character (both ledgers)."""
    out, chars, tokens = {}, 0, 0
    for ledger in LEDGERS:
        conn = sqlite3.connect(f"file:{ledger.resolve()}?mode=ro", uri=True)
        for stage, request, result in conn.execute(
            "SELECT stage,request,result FROM dispatches WHERE status='completed' AND stage IN "
            "('workload_extraction','workload_retention','workload_classifier')"
        ):
            usage = json.loads(result)["response"]["usage"]
            out.setdefault(stage, []).append(usage["output_tokens"])
            chars += sum(len(m["content"]) for m in json.loads(request)["messages"])
            tokens += usage["input_tokens"]
        conn.close()
    return {s: sum(v) / len(v) for s, v in out.items()}, tokens / chars


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite")
    rows = read_rows(args.bundle)
    validate(rows)
    validate_v2(rows)
    groups = sorted(
        {r["group_id"] for r in rows["private/contributions.jsonl"] if r["split"] == args.split}
    )
    pricing = json.loads(PRICING.read_text())
    pin = Decimal(str(pricing["input_usd_per_million"])) / 1_000_000
    pout = Decimal(str(pricing["output_usd_per_million"])) / 1_000_000
    out_mean, per_char = measured()
    by_stage, cost, free = Counter(), Decimal(0), 0
    with no_network():
        cache = CacheChain(ReadOnlyCache([CACHE]), *[PaidReplayCache(x) for x in LEDGERS])
        for gid in groups:
            mock = PromptAwareMock("request_guided")
            counting = Counting(mock)
            chat = LayeredClient(cache, "openrouter", fallback=counting)
            build_states(rows, gid, chat, LayeredClient(None, "local", mock), PromptLibrary())
            free += sum(1 for e in chat.log if e["source"] == "cache")
            for stage, req in counting.requests:
                by_stage[stage] += 1
                tin = Decimal(sum(len(m.content) for m in req.messages)) * Decimal(per_char)
                cost += tin * pin + Decimal(str(out_mean[stage])) * pout
    dev3 = json.loads(DEV_STAGE3.read_text())
    dev_groups = len(dev3["groups"])
    dev_usd = Decimal(dev3["actual_task_spend_usd"])
    unique = sum(n for stage, status, n in dev3["dispatches_by_stage_and_status"])
    s3 = dev_usd / dev_groups * len(groups)
    result = {
        "status": "estimate_only_no_api_call_no_outcome",
        "bundle": str(args.bundle),
        "split": args.split,
        "groups": len(groups),
        "stage1": {
            "requests_free_from_cache_or_paid_replay": free,
            "requests_to_pay_by_stage": dict(by_stage),
            "expected_usd": str(cost.quantize(Decimal("0.0001"))),
            "method": f"chars x {per_char:.4f} tokens/char; measured mean output per stage",
        },
        "stage3": {
            "dev_measured": {"groups": dev_groups, "usd": str(dev_usd), "unique_requests": unique},
            "expected_usd": str(s3.quantize(Decimal("0.0001"))),
            "expected_unique_requests": round(unique / dev_groups * len(groups)),
            "method": "dev Stage 3 USD per group x test groups",
        },
        "total_expected_usd": str((cost + s3).quantize(Decimal("0.0001"))),
        "total_with_20pct_allowance_usd": str(
            ((cost + s3) * Decimal("1.2")).quantize(Decimal("0.0001"))
        ),
        "stage2": "free (offline)",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
