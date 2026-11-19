"""CLI: python -m locomo_v1 <stage> (run under WSL with PYTHONPATH=src:.:<nltk overlay>).

  build                free: every scenario/decision/context, per conversation (parallel)
  estimate             free: unique prompts and the calibrated cost; applies the draws rule
  mock                 free: the full matrix through the evaluator with a fake LLM, analysed
  freeze-prepare       free: writes the manifest (never overwrites); checks Option B
  freeze-verify        free
  paid                 PAID: refuses unless the freeze verifies and the owner's approval names
                       the digest and the cap
  judge-check          PAID (separate $1 guard), after `paid`
  analyse              free: once, after the run
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from importlib import metadata
from pathlib import Path

from . import config as K

FREEZE_DIR = K.REPO / "research_data" / "locomo_v1_freeze"
BUILD = FREEZE_DIR / "build"
MANIFEST = FREEZE_DIR / "freeze_manifest.json"
APPROVAL = FREEZE_DIR / "owner_approval.json"
DRAWS_FILE = FREEZE_DIR / "draws.json"


def environment() -> dict:
    pk = sorted(f"{d.metadata['Name'].lower()}=={d.version}" for d in metadata.distributions()
                if d.metadata["Name"])
    return {"python": sys.version.split()[0], "packages": pk}


def _build_one(cid):
    import os
    import torch

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    torch.set_num_threads(2)
    from .build import build_conversation

    return build_conversation(cid, BUILD)


def draws() -> int:
    return json.loads(DRAWS_FILE.read_text())["draws"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--run", default=None)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=5)
    a = ap.parse_args()
    if a.stage == "build":
        BUILD.mkdir(parents=True, exist_ok=True)
        todo = [c for c in K.CONVS if not (BUILD / f"{c}.scenarios.json").exists()]
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for r in ex.map(_build_one, todo):
                print(json.dumps(r), flush=True)
    elif a.stage == "estimate":
        from .execute import estimate

        e5 = estimate(BUILD, K.DRAWS_MAX)
        chosen = K.DRAWS_MAX if e5["calibrated_usd"] <= K.DRAWS_RULE_USD else K.DRAWS_MIN
        e = e5 if chosen == K.DRAWS_MAX else estimate(BUILD, chosen)
        out = {"rule": f"{K.DRAWS_MAX} draws if calibrated estimate <= ${K.DRAWS_RULE_USD}",
               "estimate_5_draws": e5, "draws": chosen, "estimate": e}
        if DRAWS_FILE.exists() and json.loads(DRAWS_FILE.read_text())["draws"] != chosen:
            raise SystemExit("draws already fixed differently; refusing")
        DRAWS_FILE.write_text(json.dumps(out, indent=1))
        print(json.dumps(out, indent=1))
    elif a.stage == "mock":
        from .analysis import analyse
        from .execute import judge_check, run

        rd = Path(a.run)
        rd.mkdir(parents=True, exist_ok=True)
        print(json.dumps(run(BUILD, rd, "mock", draws(), a.workers)))
        print(json.dumps(judge_check(rd, "mock")))
        res = analyse(BUILD, rd, draws())
        print(json.dumps({h: {k: v[k] for k in ("p_iut", "reject")}
                          for h, v in res["confirmatory"]["hypotheses"].items()}))
        print(json.dumps(res["validity"]))
    elif a.stage == "freeze-prepare":
        from .freeze import prepare

        print(prepare(BUILD, MANIFEST, environment()))
    elif a.stage == "freeze-verify":
        from .freeze import verify

        print(json.dumps(verify(BUILD, MANIFEST, environment()), indent=1))
    elif a.stage in ("paid", "judge-check"):
        from .freeze import verify

        v = verify(BUILD, MANIFEST, environment())
        if not v["verified"]:
            raise SystemExit(f"freeze does not verify: {v['diffs']} {v['option_b']}")
        if not APPROVAL.exists():
            raise SystemExit("no signed owner approval; refusing")
        ap_ = json.loads(APPROVAL.read_text())
        if ap_.get("freeze_digest") != v["digest"] or ap_.get("cap_usd") != K.CAP_USD:
            raise SystemExit("approval does not name this digest and cap; refusing")
        from .execute import judge_check, run

        rd = Path(a.run)
        rd.mkdir(parents=True, exist_ok=True)
        if a.stage == "paid":
            print(json.dumps(run(BUILD, rd, "paid", draws(), a.workers)))
        else:
            print(json.dumps(judge_check(rd, "paid")))
    elif a.stage == "analyse":
        from .analysis import analyse

        res = analyse(BUILD, Path(a.run), draws())
        print((Path(a.run) / "RESULTS.md").read_text())
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
