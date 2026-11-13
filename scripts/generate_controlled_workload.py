#!/usr/bin/env python3
"""Generate, check and cost the controlled MPBench-derived workload (offline).

    generate --out research_data/controlled_workload_v1_20261108
    generate --carriers v2 --out research_data/controlled_workload_v2_20261108
    generate --carriers v3 --out research_data/controlled_workload_v3_20261108
    generate --carriers v4 --out research_data/controlled_workload_v4_20261108
    check    --bundle research_data/controlled_workload_v1_20261108

`--carriers v2` (8 Nov 2026) makes benign utility facts and the unlinked relay
the main content of their notes; everything else is identical to v1.

`generate` builds the workload from existing local files, validates it, writes a
new bundle (refuses to overwrite) and a GPT-4o-mini cost estimate. `check`
re-validates a saved bundle and confirms it regenerates byte-identically.
No network access, no model calls, no paid step is started.
"""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from ams.data.mpbench import _read_objects
from ams.research.dynamic.models import check, digest
from ams.research.recovery.offline import no_network
from ams.research.workload import design as D
from ams.research.workload.costs import estimate, measured_usage
from ams.research.workload.generator import (
    VERSIONS,
    build,
    read_rows,
    validate,
    validate_v2,
    write,
)
from ams.research.workload.quality_v4 import (
    EMBED_MODEL,
    NEAR_DUPLICATE_COSINE,
    near_duplicate_pairs,
    relay_text,
)

REPO = Path(__file__).resolve().parents[1]
RUN = (
    REPO / "results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/"
    "full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z"
)
FEASIBILITY = REPO / "research_data/propagation_feasibility_v1_20261108/attack_cases.jsonl"
CASE_INDEX = REPO / "research_data/mpbench_recovery_v1_20261029/private/evaluator_case_index.jsonl"
PRICING = REPO / "configs/research/dynamic_pricing_20261030.json"
BUDGET_CAP = Decimal("30")
BUDGET_USED = Decimal("2.09412345")  # research-session ledger, rechecked 7 Nov 2026


def jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_sources(design: str = "v1") -> tuple[dict, dict]:
    adv = {a["id"]: a for a in _read_objects(REPO / "data/mpbench/adversarial_data.jsonl.jsonl")}
    ben = {b["id"]: b for b in _read_objects(REPO / "data/mpbench/benign_data.jsonl.jsonl")}
    index = {r["original_case_key"]: r for r in jsonl(CASE_INDEX)}
    claim_text = {}
    for row in jsonl(RUN / "written_memories-no_defence.jsonl"):
        for w in row["written"]:
            claim_text[w["entry_id"]] = w["metadata"]["raw_text"]
    feas = jsonl(FEASIBILITY)

    def overlap(text, target):
        words = lambda s: {w.strip(".,;:'\"()").lower() for w in s.split() if len(w) > 2}  # noqa: E731
        return len(words(text) & words(target)), -len(text)

    def attack(r):
        a = adv[r["case"].split(":", 1)[1]]
        # The relayed copy uses the carrier claim that best restates the target.
        carriers = sorted(
            r["external_carriers"],
            key=lambda e: overlap(claim_text[e], a["expected_memory"]),
            reverse=True,
        )
        carrier = claim_text[carriers[0]] if carriers else a["expected_memory"]
        return {
            "case": r["case"],
            "context": r["context"],
            "template_group": r["template_group"],
            "user_query": a["user_query"],
            "context_text": a["context"],
            "question": a["retrieval_query"],
            "target": a["expected_memory"],
            "carrier_text": relay_text(carrier, a["context"], a["expected_memory"])
            if quality
            else carrier,
        }

    quality = design == "v4"
    reachable = [attack(r) for r in feas if r["tier"].startswith("attributable")]
    seeds = [
        attack(r)
        for r in feas
        if not r["tier"].startswith("attributable") and r["repro_poison_written"]
    ]
    benign = []
    for key, r in index.items():
        if r["stratum"] == "attack":
            continue
        b = ben[r["original_id"]]
        if (
            D.BENIGN_MIN_CHARS < len(b["context"]) <= D.BENIGN_MAX_CHARS
            and len(r["records"]) <= D.BENIGN_MAX_CLAIMS
        ):
            benign.append(
                {
                    "case": key,
                    "context": r["context_id"],
                    "user_query": b["user_query"],
                    "context_text": b["context"],
                }
            )
    inputs = {
        "adversarial_data": digest(
            (REPO / "data/mpbench/adversarial_data.jsonl.jsonl").read_text()
        ),
        "benign_data": digest((REPO / "data/mpbench/benign_data.jsonl.jsonl").read_text()),
        "feasibility_attack_cases": digest(FEASIBILITY.read_text()),
        "case_index": digest(CASE_INDEX.read_text()),
        "pool_sizes": {
            "reachable": len(reachable),
            "seeds": len(seeds),
            "benign_bases": len(benign),
        },
    }
    sources = {"reachable": reachable, "seeds": seeds, "benign": benign}
    if quality:
        sources["near_duplicates"] = near_duplicate_pairs(reachable + seeds, minilm_embed)
        inputs["near_duplicate_rule"] = {
            "embedding_model": EMBED_MODEL,
            "cosine_threshold": NEAR_DUPLICATE_COSINE,
            "cases_with_near_duplicates": len(sources["near_duplicates"]),
            "pairs_hash": digest(sources["near_duplicates"]),
        }
    return sources, inputs


def minilm_embed(texts):
    """Local MiniLM (offline, $0), unit-normalised, deterministic on CPU."""
    import os

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return [list(map(float, v)) for v in model.encode(texts, normalize_embeddings=True)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--carriers", choices=["v1", "v2", "v3", "v4"], default="v1")
    c = sub.add_parser("check")
    c.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "generate":
        carriers = args.carriers
    else:
        saved_manifest = json.loads((args.bundle / "manifest.json").read_text())
        carriers = {v: k for k, v in VERSIONS.items()}[saved_manifest["version"]]
    with no_network():
        sources, inputs = load_sources(carriers)
        rows, pools = build(sources, carriers=carriers)
        validate(rows)
        if carriers != "v1":
            validate_v2(rows)
        if args.cmd == "generate":
            manifest = write(rows, pools, args.out, inputs, carriers)
            p = json.loads(PRICING.read_text())
            pricing = {
                "input_per_million": p["input_usd_per_million"],
                "output_per_million": p["output_usd_per_million"],
                "checked_on": p["checked_on"],
            }
            cost = estimate(
                manifest["summary"],
                measured_usage(RUN / "usage.jsonl"),
                pricing,
                BUDGET_USED,
                BUDGET_CAP,
            )
            (args.out / "cost_estimate.json").write_text(json.dumps(cost, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "summary": manifest["summary"],
                        "cost": cost["stages"]
                        and {k: v["with_20pct_retry_usd"] for k, v in cost["stages"].items()},
                        "total_upper_bound_usd": cost["total_upper_bound_usd"],
                        "budget": cost["budget"],
                    },
                    indent=2,
                )
            )
        else:
            manifest = json.loads((args.bundle / "manifest.json").read_text())
            saved = read_rows(args.bundle)
            validate(saved)
            for name, items in rows.items():
                text = "".join(
                    json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in items
                )
                check(digest(text) == manifest["files"][name], f"{name} does not regenerate")
            print(json.dumps({"status": "valid_and_regenerates", "files": len(rows)}))


if __name__ == "__main__":
    main()
