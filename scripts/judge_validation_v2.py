#!/usr/bin/env python3
"""Protocol v2 human judge validation (plan.md step 1.11). Free; no model call.

    sample  --journal J [J ...] --bundle B --seed S --out KIT [--allow-heldout]
        Draw 150 judge hits + 150 misses (stratified, design-weighted) and write two
        blind annotator sheets, a private key and a manifest. On held-out data this runs
        once, AFTER the held-out run, with the seed fixed at the freeze (--allow-heldout).
    adjudicate --kit KIT --a1 FILE --a2 FILE
        Check both returned sheets (complete, binary, each annotator's own) and write
        the blind adjudication sheet with only the disagreements.
    analyse --kit KIT --a1 FILE --a2 FILE [--adjudicated FILE] --journal J [J ...]
            --bundle B --label L
        Kappa, weighted judge precision/NPV/recall/specificity, and the pre-declared
        judge-error-corrected ASR (sensitivity only).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from ams.research.dynamic.models import check
from ams.research.protocol_v2 import analysis as A
from ams.research.protocol_v2 import judge_validation as J
from ams.research.workload.generator import read_rows

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_protocol_v2 import families, journal_rows  # noqa: E402


def check_split(splits, allow):
    check(allow or "heldout" not in splits,
          "Held-out judge decisions are sampled once, after the held-out run "
          "(--allow-heldout)")  # fmt: skip


def load(args):
    rows = [r for j in args.journal for r in journal_rows(j / "queries.sqlite"
                                                          if j.is_dir() else j)]  # fmt: skip
    check_split({r.get("split", "heldout") for r in rows}, args.allow_heldout)
    bundle = read_rows(args.bundle)
    questions = {p["probe_id"]: p["question"] for p in bundle["public/probes.jsonl"]}
    return rows, A.probe_info(bundle, families(args.mpbench)), questions


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--out", type=Path, required=True)
    for name in ("adjudicate", "analyse"):
        p = sub.add_parser(name)
        p.add_argument("--kit", type=Path, required=True)
        p.add_argument("--a1", type=Path, required=True)
        p.add_argument("--a2", type=Path, required=True)
    an = sub.choices["analyse"]
    an.add_argument("--adjudicated", type=Path)
    an.add_argument("--label", required=True)
    for p in (s, an):
        p.add_argument("--journal", type=Path, nargs="+", required=True)
        p.add_argument("--bundle", type=Path, required=True)
        p.add_argument("--allow-heldout", action="store_true")
        p.add_argument("--mpbench", type=Path, help="MPBench file: attack family per case")
    args = ap.parse_args(argv)

    if args.cmd == "sample":
        check(not args.out.exists(), "Refuse to overwrite an existing directory")
        rows, info, questions = load(args)
        manifest = J.write_kit(args.out, J.sample(J.frame(rows, info, questions), args.seed),
                               args.seed)  # fmt: skip
        print(json.dumps({k: manifest[k] for k in ("items", "frame_size", "shortfall")}))
        return
    a = J.read_labels(args.a1, args.kit, J.ANNOTATORS[0])
    b = J.read_labels(args.a2, args.kit, J.ANNOTATORS[1])
    if args.cmd == "adjudicate":
        print(json.dumps({"disagreements": J.write_adjudication_sheet(args.kit, a, b)}))
        return
    adj = {}
    if args.adjudicated:
        adj = {r["item_id"]: r["final_label"].strip().lower()
               for r in csv.DictReader(open(args.adjudicated))}  # fmt: skip
    key = json.loads((args.kit / "key_PRIVATE.json").read_text())
    truth = J.truth(a, b, adj)
    metrics = J.judge_metrics(key["items"], truth, seed=key["seed"])
    rows, info, _ = load(args)
    corrected = J.corrected_asr(J.method_rates(rows, info), metrics)
    kap = J.kappa(a, b)
    res = {"kappa": kap, "metrics": J.public(metrics), "corrected": J.public(corrected)}
    (args.kit / "judge_validation.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.kit / "judge_validation.md").write_text(J.render(kap, metrics, corrected, args.label))
    print(json.dumps({"kappa": kap}))


if __name__ == "__main__":
    main()
