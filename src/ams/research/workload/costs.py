"""GPT-4o-mini cost estimate for the controlled workload (offline arithmetic).

Token averages are *measured* from the completed full reproduction
(`usage.jsonl`), not guessed. Every estimate is an upper bound: no credit is
taken for exact-request reuse across arms, and cached verbatim MPBench
requests are also priced as if they missed the cache.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ams.research.workload import design as D

ARMS_WITH_MEMORY = ("static", "R", "C", "M", "S")
RETRY_ALLOWANCE = Decimal("0.20")
# Conflict checks fire only for retrieved claim pairs sharing a predicate; the
# reproduction did not log them separately. Upper bound: one per memory query.
CONFLICT_TOKENS = (150, 2)


def measured_usage(usage_jsonl: Path) -> dict:
    stats = defaultdict(lambda: [0, 0, 0])
    with open(usage_jsonl, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["provider"] == "local":
                continue
            s = stats[r["stage"]]
            s[0] += 1
            s[1] += r.get("input_tokens") or 0
            s[2] += r.get("output_tokens") or 0
    return {
        k: {"calls": n, "avg_input": round(i / n), "avg_output": round(o / n)}
        for k, (n, i, o) in stats.items()
    }


def estimate(summary: dict, usage: dict, pricing: dict, used_usd: Decimal, cap: Decimal) -> dict:
    pin = Decimal(str(pricing["input_per_million"])) / Decimal(1_000_000)
    pout = Decimal(str(pricing["output_per_million"])) / Decimal(1_000_000)
    writes_per_contribution = Decimal(usage["memory_write"]["calls"]) / Decimal(6240)

    def line(name, calls, tin, tout, paid=True, note=""):
        calls = Decimal(calls)
        cost = calls * (Decimal(tin) * pin + Decimal(tout) * pout)
        return {
            "item": name,
            "paid": paid,
            "calls": int(calls.to_integral_value()),
            "input_tokens": int(calls * tin),
            "output_tokens": int(calls * tout),
            "usd": cost.quantize(Decimal("0.000001")),
            "note": note,
        }

    w, a, j, u = (usage[k] for k in ("memory_write", "agent_answer", "judge", "use_type"))
    stages = {}
    for split in ("dev", "test"):
        s = summary[split]
        new_text = s["contributions_by_extraction"].get("new_text_paid", 0)
        verbatim = s["contributions_by_extraction"].get("verbatim_mpbench_cache_expected", 0)
        probes = s["probes_by_kind"]
        n_probes = sum(probes.values())
        judged = (
            probes.get("attack", 0) + probes.get("copy_linked", 0) + probes.get("copy_unlinked", 0)
        )
        new_q = probes.get("utility", 0) + probes.get("utility_principal", 0)
        mem_queries = n_probes * len(D.CONDITIONS) * len(ARMS_WITH_MEMORY)
        stages[f"stage1_construct_{split}"] = [
            line(
                "memory extraction, new text",
                writes_per_contribution * new_text,
                w["avg_input"],
                w["avg_output"],
                note=f"{new_text} contributions x {writes_per_contribution:.2f} write calls",
            ),
            line(
                "memory extraction, verbatim MPBench (cache expected; priced as miss)",
                writes_per_contribution * verbatim,
                w["avg_input"],
                w["avg_output"],
                note="expected $0 if the frozen reproduction cache hits",
            ),
            line(
                "query-type classification, new questions", new_q, u["avg_input"], u["avg_output"]
            ),
            line(
                "query-type classification, MPBench questions (cache expected)",
                judged,
                u["avg_input"],
                u["avg_output"],
            ),
            line("embeddings (local MiniLM)", 0, 0, 0, paid=False, note="local, $0"),
        ]
        stages[f"stage3_compare_{split}"] = [
            line(
                "answers, memory arms (static,R,C,M,S x 3 conditions)",
                mem_queries,
                a["avg_input"],
                a["avg_output"],
                note="upper bound: no reuse of identical requests across arms",
            ),
            line("answers, no-memory reference", n_probes, a["avg_input"], a["avg_output"]),
            line(
                "attack/copy judges",
                judged * len(D.CONDITIONS) * len(ARMS_WITH_MEMORY) + judged,
                j["avg_input"],
                j["avg_output"],
            ),
            line("conflict checks (upper bound)", mem_queries, *CONFLICT_TOKENS),
            line("utility grading (deterministic alias match)", 0, 0, 0, paid=False, note="$0"),
        ]
    out = {}
    total = Decimal(0)
    for name, items in stages.items():
        sub = sum((i["usd"] for i in items), Decimal(0))
        with_retry = (sub * (1 + RETRY_ALLOWANCE)).quantize(Decimal("0.0001"))
        total += with_retry
        out[name] = {
            "lines": [{**i, "usd": str(i["usd"])} for i in items],
            "subtotal_usd": str(sub.quantize(Decimal("0.0001"))),
            "with_20pct_retry_usd": str(with_retry),
        }
    remaining = cap - used_usd
    return {
        "model": "openai/gpt-4o-mini via OpenRouter",
        "pricing": pricing,
        "measured_token_averages": usage,
        "stages": out,
        "total_upper_bound_usd": str(total),
        "budget": {
            "cap_usd": str(cap),
            "used_usd": str(used_usd),
            "remaining_before_usd": str(remaining),
            "remaining_after_upper_bound_usd": str(remaining - total),
        },
        "caveats": [
            "Upper bound: identical requests shared across arms are priced repeatedly.",
            "Verbatim MPBench extraction/classification is priced "
            "although cache hits are expected.",
            "Rates must be re-checked against OpenRouter before any paid run.",
            "The BudgetGuard additionally reserves full-context holds per in-flight request; "
            "holds are released on settlement and are not spend.",
        ],
    }
