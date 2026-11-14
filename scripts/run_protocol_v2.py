#!/usr/bin/env python3
"""Protocol v2 evaluation (plan.md step 1.8). Built and tested offline; NOT yet run.

    precompute --bundle B --stage1 S --out DIR [--groups G ...] [--cells ...] [--methods ...]
        FREE, no network: retrieval exposure for every method that needs no paid call
        (internal arms, S2-BS, RandEC) and a hash of every would-be answer prompt
        (step 1.12 counts the distinct ones). Shard with --groups and run shards in
        parallel foreground processes; each shard writes its own --out.
    paid --bundle B --stage1 S --out DIR --sessions ROOT --approval FILE --confirm-paid
         [--backbone haiku] [--cells ...] [--methods ...]
        PAID, one process (each session's own lock makes it the single writer). Refused
        unless the owner's approval file covers EVERY purpose the chosen methods need
        (v2_stage3; v2_published_* for MemLineage/S2-ID, A-MemGuard, LLM sanitiser;
        v2_backbone_answer for Haiku), each with its model and cap, and names the frozen
        protocol-v2 digest. A rerun resumes: paid replies are replayed from the ledger.

Conditions are registry cells (`protocol_v2.registry`); default: every registered cell.
"""

import argparse
import gzip
import json
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.protocol_v2 import pipeline as PL
from ams.research.protocol_v2 import registry as REG
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import read_rows

REPO = Path(__file__).resolve().parents[1]
RANDEC = REPO / "third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt"
FREE_METHODS = ("static", "R", "C", "M", "S", "SL", "S2-BS", "randec", "randec+R")


def conditions_for(cells):
    table = REG.cells()
    return tuple(c for cell in cells for c in table[cell]["conditions"])


def load(bundle: Path, stage1: Path, conditions, groups=None):
    rows = read_rows(bundle)
    stores = []
    for path in sorted((stage1 / "stores").glob("*.json.gz")):
        with gzip.open(path, "rt") as f:
            store = json.load(f)
        if groups and store["group_id"] not in groups:
            continue
        stores.append(AD.extend_store(rows, store, [c for c in conditions
                                                    if c not in D.CONDITIONS]))  # fmt: skip
    check(bool(stores), "No Stage-1 stores selected")
    return rows, stores, digest(json.loads((bundle / "manifest.json").read_text()))


def randec():
    """RandEC loads DistilBERT through Hugging Face: use the local cache only, so the free
    precompute works inside `no_network()` (found at step 1.12; no download is attempted)."""
    import os

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from ams.baselines.amemguard_borrowed import RandECClassifier

    return RandECClassifier(weights=RANDEC)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("precompute", "paid"):
        p = sub.add_parser(name)
        p.add_argument("--bundle", type=Path, required=True)
        p.add_argument("--stage1", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--cells", nargs="*", default=list(REG.cells()))
        p.add_argument("--groups", nargs="*")
    sub.choices["precompute"].add_argument("--methods", nargs="*", default=list(FREE_METHODS))
    paid = sub.choices["paid"]
    paid.add_argument("--methods", nargs="*",
                      default=list(PL.MAIN_METHODS + PL.APPENDIX_METHODS))  # fmt: skip
    paid.add_argument("--sessions", type=Path, required=True)
    paid.add_argument("--approval", type=Path, required=True)
    paid.add_argument("--backbone", choices=["gpt", "haiku"], default="gpt")
    paid.add_argument("--confirm-paid", action="store_true")
    args = ap.parse_args(argv)
    conditions = conditions_for(args.cells)

    if args.cmd == "precompute":
        from ams.research.recovery.offline import no_network
        from ams.research.workload.stage2 import ConflictPlaceholderSession

        check(set(args.methods) <= set(FREE_METHODS),
              "Precompute runs only methods with no paid call")
        check(not args.out.exists(), "Refuse to overwrite an existing directory")
        with no_network():
            rows, stores, _ = load(args.bundle, args.stage1, conditions, args.groups)
            defences = {"randec": randec()} if any("randec" in m for m in args.methods) else {}
            result = PL.evaluate(rows, stores, ConflictPlaceholderSession(), args.out,
                                 conditions=conditions, methods=args.methods,
                                 defences=defences, answer=False)  # fmt: skip
        print(json.dumps(result, indent=2))
        return

    # Paid: every gate is checked before any data or model is loaded.
    check(args.confirm_paid,
          "Paid stages need the explicit --confirm-paid flag (owner confirmation)")
    check(not args.groups, "A paid run covers every group")
    approval = json.loads(args.approval.read_text())
    purposes = PL.required_purposes(args.methods, args.backbone)
    rows, stores, bundle_hash = load(args.bundle, args.stage1, conditions)
    with PL.open_paid(args.sessions, bundle_hash, approval, purposes, confirmed=True) as live:
        from ams.research.recovery.offline import CHAT_MODEL

        defences = {}
        if any(m.startswith("randec") for m in args.methods):
            defences["randec"] = randec()
        if "v2_published_memlineage" in purposes:
            defences["memlineage"] = PL.memlineage(live.sensitive)
        if "v2_published_amemguard" in purposes:
            from ams.baselines.amemguard import AMemGuard

            client = live.client("v2_published_amemguard")
            defences["a_memguard"] = AMemGuard(model=CHAT_MODEL, client=client)
        if "v2_published_sanitiser" in purposes:
            from ams.baselines.amemguard_borrowed import LLMSanitiser

            defences["llm_sanitiser"] = LLMSanitiser(live.client("v2_published_sanitiser"),
                                                     model=CHAT_MODEL)  # fmt: skip
        result = PL.evaluate(rows, stores, live.stage3, args.out, conditions=conditions,
                             methods=args.methods, defences=defences,
                             sensitive=live.sensitive)  # fmt: skip
        result["spend_usd"] = live.spend()
    (args.out / "paid_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
