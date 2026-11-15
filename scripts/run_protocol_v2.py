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
         [--contexts DIR ...] reads the internal arms' verified contexts (step 2 below)
         instead of recomputing retrieval (step-1.12 runtime fix 2; identical rows).

Runtime fix 2, three steps (owner-approved; `protocol_v2.two_phase`):
    1. precompute ...            FREE; also writes DIR/conflict_requests.json
       conflicts --bundle B --requests FILE ... --sessions ROOT --approval FILE --out FILE
                 --confirm-paid  PAID, tiny: only those conflict checks (v2_stage3)
    2. contexts --bundle B --stage1 S --replies FILE --out DIR [--groups G ...]
                                 FREE, shardable: the precompute with the real replies
    3. paid ... --contexts DIR ...

Every run uses PYTHONHASHSEED=0 (owner decision; `protocol_v2.hashseed`).

Step 2.2 (freeze): `conflicts` and `paid` need --freeze MANIFEST. Before anything is read
or opened, the manifest must verify (`protocol_v2.freeze`: every frozen file unchanged),
the owner's approval must name its digest, and --bundle / --stage1 must be the frozen ones.
`paid --backbone haiku` runs on the original path (no --contexts).

Old Stage-1 stores (dev v3, v4 test; 8 Nov) checkpoint the 35 prompt files that existed
then; protocol v2 later added 4 generator prompts. Every command that loads stores serves
the checkpointed files from a verified mirror next to --out (`ablations.checkpoint_prompts`,
plan.md step 2.1 decision); the frozen load check itself is unchanged.

Conditions are registry cells (`protocol_v2.registry`); default: every registered cell.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.protocol_v2 import ablations as AB
from ams.research.protocol_v2 import freeze as FZ
from ams.research.protocol_v2 import hashseed
from ams.research.protocol_v2 import pipeline as PL
from ams.research.protocol_v2 import registry as REG
from ams.research.protocol_v2 import two_phase as TP
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import read_rows

REPO = Path(__file__).resolve().parents[1]
RANDEC = REPO / "third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt"
FREE_METHODS = ("static", "R", "C", "M", "S", "SL", "S2-BS", "randec", "randec+R")


def conditions_for(cells):
    table = REG.cells()
    return tuple(c for cell in cells for c in table[cell]["conditions"])


def mirror_for(out: Path) -> Path:
    """The verified prompt mirror of a run: a sibling of --out (step 2 refuses an existing
    --out, so the mirror cannot live inside it)."""
    return out.parent / f"{out.name}.prompt_mirror"


def prepare_store(rows, store, conditions, mirror: Path):
    """Checkpointed prompts from the verified mirror, then the adaptive conditions."""
    store = AB.checkpoint_prompts(store, mirror)
    return AD.extend_store(rows, store, [c for c in conditions if c not in D.CONDITIONS])


def load(bundle: Path, stage1: Path, conditions, groups=None, *, mirror: Path):
    rows = read_rows(bundle)
    stores = []
    for path in sorted((stage1 / "stores").glob("*.json.gz")):
        with gzip.open(path, "rt") as f:
            store = json.load(f)
        if groups and store["group_id"] not in groups:
            continue
        stores.append(prepare_store(rows, store, conditions, mirror))
    check(bool(stores), "No Stage-1 stores selected")
    return rows, stores, digest(json.loads((bundle / "manifest.json").read_text()))


def inputs(bundle: Path, stage1: Path) -> dict:
    """What step-2 contexts were built from; step 3 refuses anything else."""
    stores = sorted((stage1 / "stores").glob("*.json.gz"))
    return {"bundle": digest(json.loads((bundle / "manifest.json").read_text())),
            "stage1": digest([[p.name, hashlib.sha256(p.read_bytes()).hexdigest()]
                              for p in stores])}  # fmt: skip


def randec():
    """RandEC loads DistilBERT through Hugging Face: use the local cache only, so the free
    precompute works inside `no_network()` (found at step 1.12; no download is attempted).
    Its per-text decisions are cached exactly (step 1.12 runtime fix 1, owner-approved):
    identical verdicts and global random state; the frozen classifier is unchanged."""
    import os

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from ams.baselines.amemguard_borrowed import RandECClassifier
    from ams.research.protocol_v2.randec_cache import cached_randec

    return cached_randec(RandECClassifier(weights=RANDEC))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("precompute", "paid", "contexts"):
        p = sub.add_parser(name)
        p.add_argument("--bundle", type=Path, required=True)
        p.add_argument("--stage1", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--cells", nargs="*", default=list(REG.cells()))
        p.add_argument("--groups", nargs="*")
    sub.choices["precompute"].add_argument("--methods", nargs="*", default=list(FREE_METHODS))
    ctx = sub.choices["contexts"]
    ctx.add_argument("--replies", type=Path, required=True)
    ctx.add_argument("--methods", nargs="*", default=list(TP.CONTEXT_METHODS))
    con = sub.add_parser("conflicts")
    con.add_argument("--bundle", type=Path, required=True)
    con.add_argument("--requests", type=Path, nargs="+", required=True)
    con.add_argument("--out", type=Path, required=True)
    for p in (con, sub.choices["paid"]):
        p.add_argument("--sessions", type=Path, required=True)
        p.add_argument("--approval", type=Path, required=True)
        p.add_argument("--freeze", type=Path, required=True)
        p.add_argument("--confirm-paid", action="store_true")
    paid = sub.choices["paid"]
    paid.add_argument("--methods", nargs="*",
                      default=list(PL.MAIN_METHODS + PL.APPENDIX_METHODS))  # fmt: skip
    paid.add_argument("--backbone", choices=["gpt", "haiku"], default="gpt")
    paid.add_argument("--contexts", type=Path, nargs="*")
    args = ap.parse_args(argv)
    conditions = conditions_for(getattr(args, "cells", []))

    if args.cmd == "conflicts":  # step 1, PAID: every gate before anything is read
        check(args.confirm_paid,
              "Paid stages need the explicit --confirm-paid flag (owner confirmation)")
        check(not args.out.exists(), "Refuse to overwrite an existing file")
        approval = json.loads(args.approval.read_text())
        FZ.check_paid(args.freeze, approval, bundle=args.bundle)
        hashseed.require()
        requests = TP.load_requests(args.requests)
        bundle_hash = digest(json.loads((args.bundle / "manifest.json").read_text()))
        with PL.open_paid(args.sessions, bundle_hash, approval, {"v2_stage3"},
                          confirmed=True) as live:  # fmt: skip
            replies = TP.send_conflicts(requests, live.stage3)
            spend = live.spend()
        TP.save_replies(args.out, replies)
        print(json.dumps({"conflict_checks": len(replies), "spend_usd": spend}, indent=2))
        return

    if args.cmd == "contexts":  # step 2, FREE
        from ams.research.recovery.offline import no_network

        check(not args.out.exists(), "Refuse to overwrite an existing directory")
        hashseed.require()
        with no_network():
            rows, stores, _ = load(args.bundle, args.stage1, conditions, args.groups,
                                   mirror=mirror_for(args.out))  # fmt: skip
            result = TP.build_contexts(rows, stores, TP.load_replies(args.replies), args.out,
                                       conditions=conditions, methods=args.methods,
                                       inputs=inputs(args.bundle, args.stage1))  # fmt: skip
        print(json.dumps(result, indent=2))
        return

    if args.cmd == "precompute":
        from ams.research.recovery.offline import no_network

        check(set(args.methods) <= set(FREE_METHODS),
              "Precompute runs only methods with no paid call")
        check(not args.out.exists(), "Refuse to overwrite an existing directory")
        hashseed.require()
        with no_network():
            rows, stores, _ = load(args.bundle, args.stage1, conditions, args.groups,
                                   mirror=mirror_for(args.out))  # fmt: skip
            defences = {"randec": randec()} if any("randec" in m for m in args.methods) else {}
            recorder = TP.ConflictRecorder()  # = ConflictPlaceholderSession, plus requests
            result = PL.evaluate(rows, stores, recorder, args.out,
                                 conditions=conditions, methods=args.methods,
                                 defences=defences, answer=False)  # fmt: skip
            TP.save_requests(args.out / TP.REQUESTS, recorder)  # fix 2, step 1
        print(json.dumps(result, indent=2))
        return

    # Paid: every gate is checked before any data or model is loaded.
    check(args.confirm_paid,
          "Paid stages need the explicit --confirm-paid flag (owner confirmation)")
    check(not args.groups, "A paid run covers every group")
    check(not (args.contexts and args.backbone == "haiku"),
          "Claude Haiku answers run on the original path: omit --contexts")  # fmt: skip
    approval = json.loads(args.approval.read_text())
    FZ.check_paid(args.freeze, approval, bundle=args.bundle, stage1=args.stage1)
    hashseed.require()
    purposes = PL.required_purposes(args.methods, args.backbone)
    rows, stores, bundle_hash = load(args.bundle, args.stage1, conditions,
                                     mirror=mirror_for(args.out))  # fmt: skip
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
        contexts = None
        if args.contexts:  # fix 2, step 3: verified step-2 contexts
            contexts = TP.Contexts(args.contexts, inputs=inputs(args.bundle, args.stage1))
        result = PL.evaluate(rows, stores, live.stage3, args.out, conditions=conditions,
                             methods=args.methods, defences=defences,
                             sensitive=live.sensitive, contexts=contexts)  # fmt: skip
        result["spend_usd"] = live.spend()
    (args.out / "paid_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    hashseed.ensure()
    main()
