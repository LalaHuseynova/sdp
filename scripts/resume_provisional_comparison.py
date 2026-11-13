#!/usr/bin/env python3
"""Same frozen experiment and responses, with a pinned revision-hash cache amendment."""

import argparse
import json
from pathlib import Path

from ams.research.dynamic.models import check
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import run
from ams.research.recovery.offline import sha_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    args = parser.parse_args()
    amendment = json.loads(args.amendment.read_text())
    check(
        amendment["source_manifest_sha256"] == sha_file(args.plan / "manifest.json")
        and amendment["scientific_method_changes"] == []
        and amendment["spending_limit_changes"] == []
        and amendment["scope"] == "memoize_immutable_evidence_revision_only",
        "Wrong runtime amendment",
    )
    for name, expected in amendment["files"].items():
        check(sha_file(Path(name)) == expected, "Changed amended runtime code")
    with memoized_evidence_revisions() as stats:
        result = run(args.plan, args.out)
    print(json.dumps({**result, "revision_hash_cache": stats}, indent=2))


if __name__ == "__main__":
    main()
