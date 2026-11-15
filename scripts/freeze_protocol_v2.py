#!/usr/bin/env python3
"""Protocol v2 freeze manifest (plan.md step 2.2), option B. Offline; no model call.

    prepare --out research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB.json
    verify  --protocol research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB.json

`prepare` writes the SHA-256 manifest (code, prompts, configs, environment lock, v2
scripts, the protocol text, the v4 dataset and Stage-1 stores, the dev data used by the
ablations, MPBench, the RandEC weights and the local Hugging Face snapshots) plus the
protocol built from the code's constants, and prints its digest. It refuses to overwrite.

`verify` recomputes everything and fails on any changed, added or missing file, on an
edited manifest, or when the code's protocol constants differ from the frozen ones.

Preparing a manifest does NOT activate the freeze or approve spending: the freeze binds
only through the owner's approval file naming the digest (`approved_by: owner`).
"""

import argparse
import json
from pathlib import Path

from ams.research.dynamic.models import LedgerError
from ams.research.protocol_v2 import freeze as FZ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare").add_argument("--out", type=Path, required=True)
    sub.add_parser("verify").add_argument("--protocol", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "prepare":
        saved = FZ.prepare(args.out)
        counts = {k: len(v) for k, v in saved["hashes"].items()}
        print(json.dumps({"protocol_v2_digest": saved["protocol_v2_digest"],
                          "path": str(args.out), "files": counts}, indent=2))  # fmt: skip
        return
    saved, diffs = FZ.compare(args.protocol)
    try:
        digest = FZ.verify(args.protocol)
        status = "verified"
    except LedgerError as e:
        digest, status = saved["protocol_v2_digest"], f"FAILED: {e}"
    print(json.dumps({"status": status, "protocol_v2_digest": digest,
                      "files": sum(len(v) for v in saved["hashes"].values()),
                      "diffs": diffs[:50]}, indent=2))  # fmt: skip
    if status != "verified":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
