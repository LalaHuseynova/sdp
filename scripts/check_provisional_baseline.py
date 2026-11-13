#!/usr/bin/env python3
"""Compare saved static contexts with Original SAFE-Mem using exact offline replies."""

import argparse
import gzip
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.provisional_run.preparation import read, verify
from ams.research.provisional_run.runner import mutation_hash
from ams.research.recovery.offline import no_network
from ams.research.sequential.state import RuntimeState


def audit(plan, results, verifier=verify):
    cfg, spec = verifier(plan)
    scope = digest([cfg, spec])
    with sqlite3.connect(
        f"file:{(Path(cfg['session_directory']) / 'dispatch.sqlite').resolve()}?mode=ro", uri=True
    ) as responses:
        responses.row_factory = sqlite3.Row
        with sqlite3.connect(
            f"file:{(results / 'queries.sqlite').resolve()}?mode=ro", uri=True
        ) as outcomes:
            checks = []
            for cell in spec["cells"]:
                eid = cell["episode_id"]
                episode = read(plan / "private" / (eid + ".json"))
                with gzip.open(plan / "private" / (eid + ".json.gz"), "rt") as stream:
                    state = RuntimeState.load(json.load(stream))
                for client in state.clients:

                    def resolve(record, lookup, client=client):
                        if record["kind"] == "chat" and record["request"]["max_tokens"] == 6:
                            call_id = digest([scope, "conflict", record["request_key"]])
                            row = responses.execute(
                                "SELECT * FROM dispatches WHERE call_id=?", (call_id,)
                            ).fetchone()
                            check(
                                row is not None and row["status"] == "completed",
                                "No saved conflict reply; offline audit stops",
                            )
                            value = json.loads(row["result"])
                            check(
                                dispatch_hash(row, value) == row["result_hash"]
                                and value["error"] is None,
                                "Changed conflict reply",
                            )
                            client.chats[record["request_key"]] = value["response"]
                        return lookup()

                    client.resolver = resolve
                for q in episode["queries"]:
                    key = digest([eid, "static", q["query_id"]])
                    row = outcomes.execute(
                        "SELECT body,hash FROM outcomes WHERE key=?", (key,)
                    ).fetchone()
                    check(row is not None, "Static result not yet available")
                    saved = json.loads(row[0])
                    check(digest(saved) == row[1], "Static output modified")
                    original = state.memory.retrieve(
                        session_id=episode["session_id"], query=q["text"], principal="user", k=4
                    )
                    check(
                        json.loads(canonical(asdict(original)))
                        == saved["actual"]["retrieval"]["retrieval"],
                        "Static context differs from Original SAFE-Mem",
                    )
                    check(
                        mutation_hash(state) == saved["actual"]["after_state_hash"],
                        "Static governance history differs",
                    )
                    checks.append(
                        {
                            "episode_id": eid,
                            "probe_id": q["query_id"],
                            "exact_context_and_governance_match": True,
                        }
                    )
    return {
        "status": "passed",
        "original_retrieval_parity_questions": len(checks),
        "checks": checks,
        "API_calls": 0,
        "paid_cost_usd": "0",
        "answers_resampled": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--extension", action="store_true")
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite baseline audit")
    with no_network():
        if args.extension:
            from ams.research.provisional_extension import verify as extension_verify

            result = audit(args.plan, args.results, extension_verify)
        else:
            result = audit(args.plan, args.results)
        new_json(args.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, indent=2))


if __name__ == "__main__":
    main()
