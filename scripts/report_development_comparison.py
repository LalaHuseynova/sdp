#!/usr/bin/env python3
"""Combine every fixed development group and preserve paired denominators/uncertainty."""

import argparse
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.research import comparison
from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.provisional_extension import verify as verify_extension
from ams.research.provisional_run.preparation import read, verify
from ams.research.recovery.offline import no_network


def load_rows(root):
    result = []
    with sqlite3.connect(f"file:{(root / 'queries.sqlite').resolve()}?mode=ro", uri=True) as db:
        for text, h in db.execute("SELECT body,hash FROM outcomes ORDER BY rowid"):
            value = json.loads(text)
            check(digest(value) == h, "Changed saved outcome")
            # Verify the full saved row, then retain just the reporting fields.
            # Candidate traces remain on disk rather than accumulating gigabytes
            # of identical denied-candidate dictionaries in the report process.
            trace = value["actual"].get("retrieval", {}).get("trace", {})
            candidates = trace.get("candidates", [])
            retrieved = value.get("retrieved_entry_verdict")
            result.append(
                {
                    "observation": value["observation"],
                    "answer_text": value["actual"]["answer"]["text"],
                    "raw_finish_reason": value["actual"]["answer"]["raw_finish_reason"],
                    "judge_fallback": value["judge"]["fallback"],
                    "selected_ids": trace.get("selected_ids", []),
                    "supplied_context_hash": digest(trace.get("supplied_context")),
                    "selected_records": [c["record_id"] for c in candidates if c["selected"]],
                    "originally_admitted_records": [
                        c["record_id"]
                        for c in candidates
                        if c["original_authority_allowed"] and c["original_source_allowed"]
                    ],
                    "source_penalty_candidate_occurrences": sum(
                        c["decision"]["penalty"] > 0 for c in candidates
                    ),
                    "source_gate_candidate_occurrences": sum(
                        c["decision"]["reason"] == "source_risk_gate" for c in candidates
                    ),
                    "written_entry_diagnostics": value.get("written_entry_diagnostics", []),
                    "retrieved_entry_hit": retrieved["hit"] if retrieved is not None else None,
                }
            )
    return result


def f(k, n):
    return {"numerator": k, "denominator": n, "value": k / n if n else None}


def text(value):
    return (
        "N/A"
        if not value["denominator"]
        else f"{value['numerator']}/{value['denominator']} ({100 * value['value']:.2f}%)"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite development results")
    repo = Path(__file__).resolve().parents[1]
    first_plan = repo / "research_data/provisional_comparison_freeze_v1_20261101"
    second_plan = repo / "research_data/provisional_extension_freeze_v1_20261101"
    first_rows = repo / "research_data/provisional_comparison_results_v1_20261101"
    second_rows = repo / "research_data/provisional_extension_results_v1_20261101"
    with no_network():
        cfg, spec = verify(first_plan)
        _, ext = verify_extension(second_plan)
        spec = {**spec, "cells": [*spec["cells"], *ext["cells"]]}
        comparison.validate_spec(spec)
        rows = load_rows(first_rows) + load_rows(second_rows)
        result = comparison.analyse(spec, [r["observation"] for r in rows])
        check(
            result["status"] == "complete_saved_outcomes" and len(rows) == 3888,
            "Incomplete eight-group comparison",
        )
        lookup = {
            (
                r["observation"]["episode_id"],
                r["observation"]["arm"],
                r["observation"]["probe_id"],
            ): r
            for r in rows
        }
        check(len(lookup) == len(rows), "Duplicate saved episode/arm/probe")
        diagnostics = {}
        by_episode = {}
        for root in [first_plan, second_plan]:
            for file in (root / "private").glob("ep_*.json"):
                by_episode[file.stem] = read(file)
        for scenario in sorted({c["scenario"] for c in spec["cells"]}):
            cells = [c for c in spec["cells"] if c["scenario"] == scenario]
            diagnostics[scenario] = {}
            for arm in comparison.ARMS:
                selected = []
                writes = []
                retrieved = []
                counts = Counter()
                origins = Counter()
                for c in cells:
                    subset = [lookup[c["episode_id"], arm, p["probe_id"]] for p in c["probes"]]
                    selected.extend(subset)
                    if arm == "no_memory":
                        continue
                    writes.extend(subset[0]["written_entry_diagnostics"])
                    provenance = {
                        d["record_id"]: d
                        for d in by_episode[c["episode_id"]]["provenance_decisions"]
                    }
                    audited_roots = {a["root_id"] for a in by_episode[c["episode_id"]]["audits"]}
                    for p, row in zip(c["probes"], subset, strict=True):
                        if p["metric"] == "attack":
                            retrieved.append(row["retrieved_entry_hit"])
                        original = lookup[c["episode_id"], "static", p["probe_id"]]
                        counts["changed_context_queries_vs_static"] += int(
                            row["supplied_context_hash"] != original["supplied_context_hash"]
                        )
                        counts["changed_selection_queries_vs_static"] += int(
                            row["selected_ids"] != original["selected_ids"]
                        )
                        for record_id in row["selected_records"]:
                            origin = provenance[record_id]
                            origins[origin["origin_group"]] += 1
                            if origin["origin_group"] == "external":
                                key = (
                                    "selected_external_audited_root_occurrences"
                                    if origin["root_id"] in audited_roots
                                    else "selected_external_unaudited_root_occurrences"
                                )
                                counts[key] += 1
                        admitted_external = sum(
                            provenance[r]["origin_group"] == "external"
                            for r in row["originally_admitted_records"]
                        )
                        counts["originally_admitted_external_queries"] += int(admitted_external > 0)
                        counts["originally_admitted_external_candidate_occurrences"] += (
                            admitted_external
                        )
                        for metric in [
                            "source_penalty_candidate_occurrences",
                            "source_gate_candidate_occurrences",
                        ]:
                            counts[metric] += row[metric]
                diagnostics[scenario][arm] = {
                    "write_target_present": f(
                        sum(w["verdict"]["hit"] for w in writes), len(writes)
                    ),
                    "retrieved_target_present": f(sum(retrieved), len(retrieved)),
                    "trace_counts": dict(counts),
                    "selected_origins": dict(origins),
                    "empty_outputs": sum(not r["answer_text"].strip() for r in selected),
                    "length_finishes": sum(
                        r["raw_finish_reason"] in {"length", "max_tokens"} for r in selected
                    ),
                    "judge_fallbacks": sum(r["judge_fallback"] for r in selected),
                }
        costs = read(second_rows / "costs.json")
        total_new = Decimal(costs["project_used_usd"]) - Decimal(cfg["budget_start_used_usd"])
        result.update(
            feedback_basis=cfg["basis"],
            human_verified_memory_labels=0,
            source_grounded_QA_validated=False,
            scope="D00 followed by all pre-existing D01-D07 bags; no locked confirmation",
            task_new_cost_usd=str(total_new),
            project_costs=costs,
            diagnostics=diagnostics,
            feedback_by_cell=[
                {
                    "group_id": c["group_id"],
                    "scenario": c["scenario"],
                    "root_feedback": by_episode[c["episode_id"]]["audits"][0]["outcome"],
                    "all_feedback": dict(
                        Counter(a["outcome"] for a in by_episode[c["episode_id"]]["audits"])
                    ),
                    "equivalent_verification": by_episode[c["episode_id"]][
                        "equivalent_verification"
                    ],
                }
                for c in spec["cells"]
            ],
            refusal_annotation="not performed; zero displayed refusals is not a measured true rate",
        )
        args.out.mkdir(parents=True, mode=0o700)
        new_json(args.out / "comparison.json", result)
        new_json(args.out / "study.json", spec)
        lines = [
            "# Eight-group provisional dynamic-defense results",
            "",
            "**Real model outputs, AI-simulated feedback, eight existing development groups "
            "(256 inputs). Human validation pending.**",
            "",
            "D00 was an initial run with no eligible external records. The extension included "
            "every remaining pre-existing development bag D01-D07, with unchanged methods "
            "and parameters. Case selection did not depend on outcomes. These are "
            "exploratory development results, not a locked confirmatory test.",
            "",
            "The bags retain the earlier provisional composition: 16 Email and 16 "
            "File/Document inputs, 20 attack cases and 12 benign cases each. They were "
            "not selected to satisfy the protocol's independently verified 16-unsafe/"
            "16-safe bundle quota. Regime names describe the existing case-label "
            "metadata construction; they do not establish actual memory-risk correlation.",
            "",
        ]
        for scenario, arms in result["regimes"].items():
            lines += [
                f"## {scenario}",
                "",
                "| Method | Write target present | Retrieved target | Answer ASR ↓ "
                "| Retention ↑ | Restraint ↑ | Combined benign ↑ | Audits |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for arm, a in arms.items():
                d = diagnostics[scenario][arm]
                m = a["metrics"]
                lines.append(
                    f"| {arm} | {text(d['write_target_present'])} "
                    f"| {text(d['retrieved_target_present'])} | {text(m['asr'])} "
                    f"| {text(m['retention'])} | {text(m['restraint'])} "
                    f"| {text(m['combined_benign'])} | {a['logical_audit_tickets']} |"
                )
        lines += [
            "",
            "## Limits and interpretation",
            "",
            "Three overlays of a bag are paired sensitivity conditions, not independent "
            "new datasets. Pointwise paired bag-bootstrap intervals (10,000 resamples) "
            "and all S-versus-baseline contrasts are in comparison.json; they are "
            "exploratory and not multiplicity-adjusted. No equivalence or utility "
            "noninferiority is established by a null point estimate.",
            "",
            "Feedback is replayed from saved AI proposals, not verified memory truth or "
            "human reviews. Provenance combines exact construction relationships with "
            "controlled synthetic contributors and AI span-backed claim origins. Principal "
            "records stay separate; unresolved origins cannot propagate. Case labels never "
            "become memory findings, and target judges never update trust.",
            "",
            "The original first audit ticket is preserved even when its AI assessment "
            "is safe or unresolved. feedback_by_cell in comparison.json reports all "
            "ticket outcomes. These runs therefore do not implement the primary "
            "protocol's study conditional on an independently confirmed unsafe seed.",
            "",
            "Source-grounded benign QA remains unavailable. Original retention/restraint "
            "alone cannot establish preservation of useful external contributions. Refusals "
            "are not independently annotated; nonempty generated outputs do not prove "
            "usefulness. Empty outputs, token-limit finishes, fallbacks and actual "
            "source-policy selection changes are logged in diagnostics.",
            "",
            "Audit roots are excluded from query cohorts, but foreign root records can "
            "still be retrieved. An answer difference does not by itself identify transfer "
            "to uninspected siblings. All R/C/M/S methods receive the same B=5 feedback "
            "and equivalent verifier resources within each regime; static/no-memory "
            "references consume no audits.",
            "",
            f"Additional API spend across both runs: **${total_new}**. "
            f"Total project spend: ${costs['project_used_usd']}; "
            f"remaining under the original $30 limit: ${costs['project_remaining_usd']}.",
            "",
            "Historical Original SAFE-Mem ASR 176/2,999 (5.87%) is a separate full-pool "
            "reproduction and is not the comparator for this new workload.",
            "",
        ]
        (args.out / "RESULTS.md").write_text("\n".join(lines))
    print(
        json.dumps(
            {
                "status": result["status"],
                "groups": result["independent_base_groups"],
                "outcomes": len(rows),
                "new_cost_usd": str(total_new),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
