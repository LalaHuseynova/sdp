#!/usr/bin/env python3
"""Offline integration of the controlled workload with SAFE-Mem and R/C/M/S.

    dry-run  --bundle research_data/controlled_workload_v1_20261108 --split dev --out <new>
    analyse  --bundle <bundle> --run <dry-run dir>

`dry-run` builds native SAFE-Mem stores for every group of the split with the
ORIGINAL write path, using real frozen reproduction-cache replies wherever they
exist and the deterministic mock only for cache misses. It then runs static,
R, C, M, S and no-memory with mock answers/judges, analyses the outcomes and
writes a Stage-1 request audit: the exact construction requests a paid Stage 1
would send (every mock-filled miss), with a token/cost estimate.

There is deliberately NO live/paid mode here. Paid stages need the owner's
explicit approval and a separately reviewed transport.
"""

import argparse
import gzip
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import check, digest
from ams.research.recovery.offline import ReadOnlyCache, no_network
from ams.research.workload.analysis import analyse, markdown
from ams.research.workload.generator import read_rows, validate
from ams.research.workload.integration import LayeredClient, build_states
from ams.research.workload.mock import MockSession, PromptAwareMock
from ams.research.workload.replay import CacheChain, PaidReplayCache
from ams.research.workload.runner import run

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "reports/safemem_full_mpbench/cache/responses.sqlite"
PRICING = REPO / "configs/research/dynamic_pricing_20261030.json"
MEASURED_OUTPUT = {"classifier": 4, "extraction": 120, "retention": 120}  # full-run averages
BUDGET_USED, BUDGET_CAP = Decimal("2.09412345"), Decimal("30")


def role(max_tokens):
    return "classifier" if max_tokens == 24 else "extraction" if max_tokens == 900 else "retention"


def stage1_audit(stores, rows, split):
    """Exact would-be-paid construction requests (cache misses) for this split."""
    pricing = json.loads(PRICING.read_text())
    pin = Decimal(pricing["input_usd_per_million"]) / 1_000_000
    pout = Decimal(pricing["output_usd_per_million"]) / 1_000_000
    hits, misses = Counter(), Counter()
    tokens_in, tokens_out = Counter(), Counter()
    verbatim = {
        r["contribution_id"]
        for r in rows["private/contributions.jsonl"]
        if r["split"] == split and r["extraction"] == "verbatim_mpbench_cache_expected"
    }
    for s in stores:
        for e in s["construction_log"]["chat"]:
            r = role(e["max_tokens"])
            if e["source"] == "cache":
                hits[r] += 1
            else:
                misses[r] += 1
                tokens_in[r] += -(-e["chars"] // 4)  # ~4 characters per token
                tokens_out[r] += MEASURED_OUTPUT[r]
    cost = sum(
        (Decimal(tokens_in[r]) * pin + Decimal(tokens_out[r]) * pout for r in misses), Decimal(0)
    )
    with_retry = (cost * Decimal("1.2")).quantize(Decimal("0.0001"))
    return {
        "split": split,
        "chat_requests_cache_hits": dict(hits),
        "chat_requests_would_be_paid": dict(misses),
        "would_be_paid_input_tokens_est": dict(tokens_in),
        "would_be_paid_output_tokens_est": dict(tokens_out),
        "verbatim_contributions": len(verbatim),
        "estimated_cost_usd": str(cost.quantize(Decimal("0.0001"))),
        "estimated_cost_with_20pct_retry_usd": str(with_retry),
        "budget_remaining_before_usd": str(BUDGET_CAP - BUDGET_USED),
        "budget_remaining_after_usd": str(BUDGET_CAP - BUDGET_USED - with_retry),
        "embeddings": "local MiniLM in the paid stage ($0); mock vectors in this dry run",
        "token_method": "input = rendered prompt characters / 4; output = full-run measured mean",
        "pricing_checked_on": pricing["checked_on"],
    }


def journal_rows(out):
    with sqlite3.connect(f"file:{(out / 'queries.sqlite').resolve()}?mode=ro", uri=True) as db:
        return [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes ORDER BY rowid")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run")
    d.add_argument("--bundle", type=Path, required=True)
    d.add_argument("--split", choices=["dev", "test"], default="dev")
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--groups", type=int, default=None, help="limit to the first N groups")
    d.add_argument(
        "--mock-extraction",
        choices=["salient", "request_guided"],
        default="salient",
        help="request_guided mimics the real extractor seen in dev Stage 2",
    )
    d.add_argument(
        "--paid-replay",
        type=Path,
        default=None,
        help="read-only dispatch ledger whose completed construction replies count as cached",
    )
    a = sub.add_parser("analyse")
    a.add_argument("--bundle", type=Path, required=True)
    a.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()

    with no_network():
        rows = read_rows(args.bundle)
        validate(rows)
        if args.cmd == "analyse":
            groups = sorted({r["group_id"] for r in journal_rows(args.run)})
            print(json.dumps(analyse(journal_rows(args.run), groups)["integrity"], indent=2))
            return
        check(not args.out.exists(), "Refuse to overwrite an existing dry run")
        groups = sorted(
            {r["group_id"] for r in rows["private/contributions.jsonl"] if r["split"] == args.split}
        )[: args.groups]
        replay = PaidReplayCache(args.paid_replay) if args.paid_replay else None
        mock, prompts, cache = (
            PromptAwareMock(args.mock_extraction),
            PromptLibrary(REPO / "prompts"),
            CacheChain(ReadOnlyCache([CACHE]), replay),
        )
        stores = []
        for gid in groups:
            chat = LayeredClient(cache, "openrouter", fallback=mock)
            embed = LayeredClient(None, "local", fallback=mock)  # one consistent mock vector space
            stores.append(build_states(rows, gid, chat, embed, prompts))
            print(f"built {gid}", flush=True)
        args.out.mkdir(parents=True)
        session = MockSession(mock)
        summary = run(rows, stores, session, args.out, split=args.split)
        outcomes = journal_rows(args.out)
        result = analyse(outcomes, groups)
        audit = stage1_audit(stores, rows, args.split)
        construction = {
            s["group_id"]: {
                "contributions": s["contributions"],
                "contributions_without_external_records": sum(
                    1 for c in s["contributions"] if c["claims"] + c["chunks"] == 0
                ),
                "records": len(s["record_owner"]),
            }
            for s in stores
        }
        meta = {
            "status": "mock_dry_run_complete",
            "paid_calls": 0,
            "bundle_manifest_hash": digest(json.loads((args.bundle / "manifest.json").read_text())),
            "split": args.split,
            "groups": groups,
            "outcome_rows": summary["rows"],
            "mock_dispatches": len(session.dispatches),
            "mock_extraction": args.mock_extraction,
            "cache_layers": {"frozen_reproduction_cache": True, "paid_replay": bool(replay)},
            "cache_hits": dict(cache.counts),
            "warning": "Mock answers/judges: outcomes test the software path only.",
        }
        (args.out / "dry_run.json").write_text(json.dumps(meta, indent=2) + "\n")
        (args.out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
        (args.out / "analysis.md").write_text(markdown(result) + "\n")
        (args.out / "stage1_request_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        with gzip.open(args.out / "construction.json.gz", "wt") as f:
            json.dump(construction, f)
        print(markdown(result))
        print(json.dumps({"integrity": result["integrity"], "stage1": audit}, indent=2))


if __name__ == "__main__":
    main()
