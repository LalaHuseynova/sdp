#!/usr/bin/env python3
"""Offline authority-admission capacity in existing bags; no retrieval/model inference."""

import argparse
import json
from collections import Counter
from pathlib import Path

from ams.core.lattice import Rung, coarsen
from ams.core.lattice import principal as principal_domain
from ams.research.dynamic.models import check
from ams.research.execution.session import new_json
from ams.research.native.pipeline import load_store, verify
from ams.research.phase1_common import read_jsonl
from ams.research.recovery.offline import no_network


def audit(prepared, stores):
    integrity = verify(stores)
    bags = json.loads((prepared / "private/group_selections.json").read_text())
    cases = {
        r["contribution_id"]: r for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
    }
    results, required_counts = [], Counter()
    for bag in bags:
        state = load_store(stores, bag["bag_token"], "R")
        session = next(iter(state.memory._graphs))
        graph = state.memory._graphs[session]
        records = {r.native_id: r for r in state.bindings.records}
        source = {s.source_id: s for s in state.bindings.sources}
        for pid in bag["source_ids"]:
            query = cases[pid]["retrieval_query"]
            required = coarsen(state.memory.use_type.required(query), state.memory.granularity)
            about = state.memory.use_type.subject(query)
            counts = Counter()
            for claim in graph.claims():
                if state.memory._admits(
                    claim.claim_type, claim.standing, required, principal_domain("user"), about
                ):
                    origin = (
                        "principal"
                        if source[claim.source_id].principal_id is not None
                        else "external_structural_parent"
                    )
                    counts[origin] += 1
            for chunk in state.memory._chunks[session]:
                if (
                    state.memory.external_evidence or chunk.standing.level > Rung.DESCRIPTION
                ) and state.memory._admits(
                    chunk.standing.level, chunk.standing, required, principal_domain("user"), about
                ):
                    origin = (
                        "principal"
                        if records[chunk.chunk_id].origin_class == "principal"
                        else "external_structural_parent"
                    )
                    counts[origin] += 1
            required_counts[required.name.lower()] += 1
            results.append(
                {
                    "bag_id": bag["bag_id"],
                    "contribution_id": pid,
                    "required": required.name.lower(),
                    "case_stratum": cases[pid]["stratum"],
                    "eligible_record_counts_before_relevance_and_reputation": dict(counts),
                }
            )
        print(f"Checked authority capacity {bag['bag_id']}: 32 original questions", flush=True)
    check(len(results) == 640, "Unexpected existing provisional coverage")
    return {
        "scope": "existing 20 case-intent provisional bags, not all MPBench",
        "status": "complete_offline_admission_audit",
        "native_bundle_integrity": integrity,
        "original_questions_checked": len(results),
        "required_type_counts": dict(required_counts),
        "questions_with_any_structural_external_candidate": sum(
            r["eligible_record_counts_before_relevance_and_reputation"].get(
                "external_structural_parent", 0
            )
            > 0
            for r in results
        ),
        "queries": results,
        "paid_API_calls": 0,
        "new_cost_usd": "0",
        "retrieval_or_answer_experiments": 0,
        "human_annotations_created": 0,
        "attribution": "structural origin only; no natural-identity claim",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    parser.add_argument(
        "--stores", type=Path, default=Path("research_data/dynamic_native_stores_v1_20261031")
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite admission audit")
    with no_network():
        value = audit(args.prepared, args.stores)
        new_json(args.out, value)
    print(json.dumps({k: v for k, v in value.items() if k != "queries"}, indent=2))


if __name__ == "__main__":
    main()
