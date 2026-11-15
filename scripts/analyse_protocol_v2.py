#!/usr/bin/env python3
"""Protocol v2 analysis (plan.md step 1.9): metrics, H1-H6, Tables 1-8, appendix, figures.

    analyse_protocol_v2.py --journal J [J ...] --bundle B --label dev --out DIR
        [--mpbench data/mpbench/adversarial_data.jsonl.jsonl] [--resamples 10000]
        [--evidence confirmatory|replication|exploratory|dev]
        [--backbone-journal HJ ... --backbone-label L] [--not-run LABEL ...]

Option B (step 2.1): --evidence replication labels every table "reused MPBench v4 split:
replication evidence, not fresh held-out" and Table 8 "not confirmatory". A Claude Haiku
journal (--backbone-journal) is analysed with the main run's pre-specified Table-7
baselines and rendered as Appendix A13; --not-run lists Table-7 rows not produced.

Reads pipeline / runner journals (queries.sqlite) READ-ONLY and checks every row's hash.
Free: no model call. Refuses held-out rows unless --allow-heldout (only for the single
frozen analysis run after the freeze, plan.md phase 3); until then it runs on dev data.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from ams.data.mpbench import _read_objects
from ams.research.dynamic.models import check, digest
from ams.research.protocol_v2 import analysis as A
from ams.research.protocol_v2.generation import _norm_type
from ams.research.workload.generator import read_rows


def journal_rows(path: Path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        for text, h in db.execute("SELECT body,hash FROM outcomes ORDER BY rowid"):
            row = json.loads(text)
            check(digest(row) == h, f"Saved outcome modified in {path}")
            row.setdefault("method", row.get("arm"))  # v1-v3 runner rows say "arm"
            if row["method"] != "no_memory":
                yield row
    finally:
        db.close()


def families(mpbench: Path | None) -> dict:
    if not mpbench:
        return {}
    return {x["id"]: _norm_type(x["attack_type"]) for x in _read_objects(mpbench)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--journal", type=Path, nargs="+", required=True)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mpbench", type=Path)
    ap.add_argument("--resamples", type=int, default=A.RESAMPLES)
    ap.add_argument("--allow-heldout", action="store_true")
    ap.add_argument("--evidence", choices=sorted(A.EVIDENCE), default="dev")
    ap.add_argument("--backbone-journal", type=Path, nargs="+")
    ap.add_argument("--backbone-label")
    ap.add_argument("--not-run", nargs="*", default=[])
    args = ap.parse_args(argv)
    check(not args.backbone_journal or bool(args.backbone_label),
          "--backbone-journal needs --backbone-label")  # fmt: skip
    check(not args.out.exists(), "Refuse to overwrite an existing directory")
    rows = [r for j in args.journal for r in journal_rows(j / "queries.sqlite"
                                                          if j.is_dir() else j)]  # fmt: skip
    splits = {r.get("split", "heldout") for r in rows}
    check(args.allow_heldout or "heldout" not in splits,
          "Held-out rows: the analysis runs once, after the freeze (--allow-heldout)")
    info = A.probe_info(read_rows(args.bundle), families(args.mpbench))
    res = A.analyse(rows, info, resamples=args.resamples, label=args.label,
                    evidence=args.evidence)  # fmt: skip
    table7 = {args.label: res}
    backbone = None
    if args.backbone_journal:
        brows = [r for j in args.backbone_journal
                 for r in journal_rows(j / "queries.sqlite" if j.is_dir() else j)]  # fmt: skip
        backbone = A.analyse(brows, info, resamples=args.resamples, label=args.backbone_label,
                             evidence=args.evidence, with_covariates=False,
                             selection={k: res["table7"][k]
                                        for k in ("best_published", "best_internal")})  # fmt: skip
        backbone["inputs"] = {"journals": [str(j) for j in args.backbone_journal],
                              "rows": len(brows)}  # fmt: skip
        table7[args.backbone_label] = backbone
    args.out.mkdir(parents=True)
    res["inputs"] = {"journals": [str(j) for j in args.journal], "bundle": str(args.bundle),
                     "rows": len(rows), "splits": sorted(splits)}  # fmt: skip
    (args.out / "analysis.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "tables.md").write_text(A.render_tables(res) + "\n"
                                        + A.render_table7(table7, args.not_run))  # fmt: skip
    (args.out / "appendix.md").write_text(A.render_appendix(res) + (
        "\n" + A.render_backbone(backbone) if backbone else ""))
    if backbone:
        (args.out / "backbone_analysis.json").write_text(json.dumps(backbone, indent=1) + "\n")
    (args.out / "per_cell.md").write_text(A.render_per_cell(res))
    paths = A.figures(res, args.out)
    print(json.dumps({"rows": len(rows), "groups": res["groups"], "methods": res["methods"],
                      "out": str(args.out), "figures": paths}, indent=2))  # fmt: skip


if __name__ == "__main__":
    main()
