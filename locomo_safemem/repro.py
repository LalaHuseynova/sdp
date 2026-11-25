"""Reproducibility check (free): recompute one mock shard from scratch into a separate folder and
compare jobs, contexts and store metadata with the mock pass's shard (timings and process-global
counters excluded).

    python -m locomo_safemem.repro [--conv conv-48 --pidx 0 --draw 0]
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil

from locomo_safemem import run as R

FIELDS = ("jobs", "ctxs", "metas", "static_loc")


def _strip(metas):
    return [{k: v for k, v in m.items() if k != "timing"} for m in metas]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--conv", default="conv-48")
    ap.add_argument("--pidx", type=int, default=0)
    ap.add_argument("--draw", type=int, default=0)
    a = ap.parse_args(argv)
    out = R.ROOT / "repro"
    shutil.rmtree(out, ignore_errors=True)
    res = R.work({"conv": a.conv, "pidx": a.pidx, "draw": a.draw, "mode": "mock", "out": str(out)})
    assert "error" not in res, res
    name = f"{a.conv}_o{a.pidx}_d{a.draw}.json.gz"
    with gzip.open(R.ROOT / "mock" / "shards" / name, "rt") as fh:
        ref = json.load(fh)
    with gzip.open(out / "shards" / name, "rt") as fh:
        new = json.load(fh)
    same = {f: (_strip(ref[f]) == _strip(new[f])) if f == "metas" else ref[f] == new[f] for f in FIELDS}
    rep = {"shard": name, "identical": all(same.values()), "fields": same, "jobs": len(new["jobs"])}
    (R.ROOT / "repro_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
