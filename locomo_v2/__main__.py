"""LoCoMo v2 CLI (run under WSL via research_data/locomo_v2/run.sh -m locomo_v2 <stage>).

  build      [--convs ...] [--families ...] [--randec]   free, deterministic
  mechanism  [--convs ...]                              free, retrieval level (no LLM)
  estimate   [--convs ...]                              free, cost of the answer stage
  mock       [--convs ...]                              free, full answer+judge path with a mock model
  freeze     prepare | verify                           free, hashes code, data, prompts, build
  paid       [--convs ...]                              PAID: refuses without owner_approval.json naming the digest
  analyse    --run DIR [--convs ...]                    free, once, after the paid run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from locomo_v2 import config as K

OUT = K.REPO / "research_data" / "locomo_v2"
BUILD = OUT / "build"
FREEZE = OUT / "freeze"
STATE = Path.home() / ".locomo_v2_state"


def _convs(a):
    return tuple(a.convs) if a.convs else K.CONVS


def freeze_files():
    pats = ["locomo_v2/*.py", "locomo_v1/*.py", "research_data/locomo_feasibility_20261119/feasibility.py",
            "minja_v2/adapter.py", "src/ams/research/dynamic/*.py", "src/ams/research/workload/lineage.py",
            "src/ams/research/workload/sv2.py", "src/ams/research/workload/published.py",
            "src/ams/baselines/memlineage.py", "src/ams/baselines/amemguard_borrowed.py",
            "src/ams/eval/locomo.py", "src/ams/data/locomo.py", "prompts/locomo_qa/*", "prompts/locomo_judge/*",
            "prompts/locomo_memory_start/*", "research_data/locomo_v1_freeze/sensitive_verdicts.json",
            "data/locomo/locomo10.json", "reports/PROTOCOL_LOCOMO_V2.md", "research_data/locomo_v2/build/*"]
    files = sorted({p for pat in pats for p in K.REPO.glob(pat) if p.is_file()})
    return {str(p.relative_to(K.REPO)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage")
    ap.add_argument("sub", nargs="?")
    ap.add_argument("--convs", nargs="*")
    ap.add_argument("--families", nargs="*")
    ap.add_argument("--randec", action="store_true")
    ap.add_argument("--run", type=Path)
    ap.add_argument("--build", type=Path, default=BUILD)
    a = ap.parse_args(argv)

    if a.stage == "build":
        from locomo_v1 import build as B1
        from locomo_v2 import build as B

        verdicts = B1.load_verdicts()
        randec = None
        if a.randec:
            from ams.baselines.amemguard_borrowed import RandECClassifier

            randec = RandECClassifier(upstream_root=Path("/mnt/c/Users/HP/Documents/sdp"))
        pub = B.Published(verdicts, randec=randec)
        enc = B1.Encoder()
        fams = tuple(a.families) if a.families else ("loc", "fn20", "sybil", "shift", "relay", "frame")
        for cid in _convs(a):
            print(json.dumps(B.build_conversation(cid, a.build, fams, enc, verdicts, pub)), flush=True)
    elif a.stage == "mechanism":
        from locomo_v2.analysis import mechanism

        res = mechanism(a.build, _convs(a))
        (OUT / f"mechanism_{'_'.join(_convs(a))}.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({k: v for k, v in list(res["curves"].items())[:5]}, indent=1))
    elif a.stage == "estimate":
        from locomo_v1 import execute as E

        print(json.dumps(E.estimate(a.build, K.DRAWS, _convs(a)), indent=1))
    elif a.stage == "mock":
        import locomo_v1.config as V1
        from locomo_v1 import execute as E

        V1.PROTOCOL_ID = K.PROTOCOL_ID
        run = a.run or OUT / "mock"
        run.mkdir(parents=True, exist_ok=True)
        print(json.dumps(E.run(a.build, run, "mock", K.DRAWS, workers=8, convs=_convs(a))))
    elif a.stage == "freeze":
        FREEZE.mkdir(parents=True, exist_ok=True)
        man = FREEZE / "freeze_manifest.json"
        files = freeze_files()
        digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        if a.sub == "prepare":
            man.write_text(json.dumps({"protocol": K.PROTOCOL_ID, "digest": digest, "files": files}, indent=1))
            print(digest, len(files))
        else:
            ref = json.loads(man.read_text())
            bad = [f for f in set(ref["files"]) | set(files) if ref["files"].get(f) != files.get(f)]
            print(json.dumps({"status": "verified" if not bad else "differs", "digest": digest, "diffs": bad[:20]}))
            sys.exit(0 if not bad else 3)
    elif a.stage == "paid":
        appr = FREEZE / "owner_approval.json"
        man = FREEZE / "freeze_manifest.json"
        if not appr.exists() or not man.exists():
            sys.exit("refused: no owner approval / freeze manifest (protocol §11)")
        ref = json.loads(man.read_text())
        files = freeze_files()
        if json.loads(appr.read_text()).get("digest") != ref["digest"] or files != ref["files"]:
            sys.exit("refused: approval does not name the verified freeze digest")
        import locomo_v1.config as V1
        from locomo_v1 import execute as E

        V1.PROTOCOL_ID, V1.CAP_USD = K.PROTOCOL_ID, K.CAP_USD
        run = OUT / "run"
        run.mkdir(parents=True, exist_ok=True)
        print(json.dumps(E.run(a.build, run, "paid", K.DRAWS, workers=16, convs=_convs(a), state_dir=STATE)))
    elif a.stage == "analyse":
        from locomo_v2.analysis import analyse

        res = analyse(a.build, a.run, _convs(a) if a.convs else K.HELDOUT)
        out = a.run / "analysis.json"
        if out.exists() and a.run.name != "mock":
            sys.exit("refused: the analysis runs once")
        out.write_text(json.dumps(res, indent=1, default=str))
        print(json.dumps({h: {k: v for k, v in r.items() if k != "parts"} for h, r in res["hypotheses"].items()}, indent=1))
    else:
        sys.exit(f"unknown stage {a.stage}")


if __name__ == "__main__":
    main()
