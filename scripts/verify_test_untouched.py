#!/usr/bin/env python3
"""Verify that the controlled workload's held-out test split was never processed.

Offline and read-only. Checks, for every workload bundle version present:

1. No paid or mock request in any guarded session ledger contains test-only
   text (a test probe question or a test benign fact sentence that never
   occurs in dev).
2. No workload output directory (Stage 1/2/3 stores, journals, summaries,
   pilots, dry runs) holds a test group ID.
3. Every Stage-1/2/3 summary lists dev groups only.

Usage: verify_test_untouched.py --out <new json path>
"""

import argparse
import gzip
import json
import sqlite3
from pathlib import Path

from ams.research.workload.generator import read_rows

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "research_data"
LEDGERS = [
    DATA / "dynamic_execution_prep_v1_20261031/session/dispatch.sqlite",
    DATA / "controlled_workload_session_v2_20261108/dispatch.sqlite",
]
BUNDLES = sorted(DATA.glob("controlled_workload_v[0-9]_20261108"))
OUTPUT_GLOBS = [
    "controlled_workload_stage*_20261108",
    "controlled_workload_*dryrun*",
    "controlled_workload_dryrun_*",
    "fact_pilot_*",
]


def test_only_strings(rows):
    dev_text, test_text = set(), set()
    probes = {p["probe_id"]: p for p in rows["private/probes.jsonl"]}
    for p in rows["public/probes.jsonl"]:
        (dev_text if probes[p["probe_id"]]["split"] == "dev" else test_text).add(p["question"])
    for r in rows["private/contributions.jsonl"]:
        if r["role"] == "benign_with_fact":
            (dev_text if r["split"] == "dev" else test_text).add(r["fact"]["sentence"])
    return test_text - dev_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), "Refuse to overwrite"
    needles = set()
    for bundle in BUNDLES:
        needles |= test_only_strings(read_rows(bundle))
    ledger_hits, scanned = [], 0
    for ledger in LEDGERS:
        if not ledger.is_file():
            continue
        conn = sqlite3.connect(f"file:{ledger.resolve()}?mode=ro", uri=True)
        for call_id, stage, request in conn.execute(
            "SELECT call_id,stage,request FROM dispatches WHERE stage LIKE 'workload_%'"
        ):
            scanned += 1
            body = " ".join(m["content"] for m in json.loads(request)["messages"])
            if any(n in body for n in needles):
                ledger_hits.append({"ledger": str(ledger), "call_id": call_id, "stage": stage})
        conn.close()
    output_hits, files = [], 0
    for pattern in OUTPUT_GLOBS:
        for d in sorted(DATA.glob(pattern)):
            for f in sorted(p for p in d.rglob("*") if p.is_file()):
                files += 1
                if f.suffix == ".gz":
                    text = gzip.open(f, "rt").read()
                elif f.suffix == ".sqlite":
                    conn = sqlite3.connect(f"file:{f.resolve()}?mode=ro", uri=True)
                    tables = [
                        r[0]
                        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    ]
                    text = " ".join(
                        str(row)
                        for t in tables
                        if t != "sqlite_sequence"
                        for row in conn.execute(f'SELECT * FROM "{t}"')  # noqa: S608
                    )
                    conn.close()
                else:
                    text = f.read_text(errors="ignore")
                if '"G-T' in text or "'G-T" in text or any(n in text for n in needles):
                    output_hits.append(str(f.relative_to(REPO)))
    summaries = {}
    for f in sorted(DATA.glob("controlled_workload_stage*_20261108/stage*_summary.json")):
        s = json.loads(f.read_text())
        summaries[str(f.relative_to(REPO))] = sorted(s.get("groups") or s.get("groups_completed"))
    dev_only = all(all(g.startswith("G-D") for g in v) for v in summaries.values())
    result = {
        "status": "test_untouched" if not ledger_hits and not output_hits and dev_only else "FAIL",
        "bundles_checked": [str(b.relative_to(REPO)) for b in BUNDLES],
        "test_only_strings": len(needles),
        "ledger_requests_scanned": scanned,
        "ledger_requests_with_test_text": ledger_hits,
        "output_files_scanned": files,
        "output_files_with_test_ids_or_text": output_hits,
        "stage_summaries_groups": summaries,
        "note": "The frozen MPBench reproduction cache predates this project and holds the "
        "original SAFE-Mem reproduction of every MPBench case; it contains no workload "
        "test outcome (workload test texts are new and never sent).",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "stage_summaries_groups"}, indent=2))


if __name__ == "__main__":
    main()
