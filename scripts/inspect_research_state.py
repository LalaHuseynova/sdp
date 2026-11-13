#!/usr/bin/env python3
"""Inspect saved research artifacts offline; never change an execution gate.

Run from the repository root. --out must name a new report. In particular, the
Phase 1 compatibility check below reports a legacy validator problem; it does
not rewrite old manifests or make the legacy generation/import commands ready.
"""

import argparse
import csv
import json
import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.focused_review import status as review_status
from ams.research.native.pipeline import verify as check_native
from ams.research.phase1 import check_prepared, implementation_fingerprints
from ams.research.phase1_common import PROTOCOL_HASH, SCHEMA, PreparationError
from ams.research.provisional.pipeline import validate as check_provisional
from ams.research.provisional_extension import verify as check_extension
from ams.research.provisional_run.preparation import verify as check_first
from ams.research.recovery.offline import no_network, sha_file
from ams.research.recovery.pipeline import validate_outputs


def read(path):
    return json.loads(path.read_text())


def phase1_archive(root):
    manifest = read(root / "preparation_manifest.json")
    check(
        manifest["schema"] == SCHEMA and manifest["protocol_sha256"] == PROTOCOL_HASH,
        "Phase 1 schema/protocol differs",
    )
    recorded = manifest["implementation_sha256"]
    current = implementation_fingerprints()
    missing = sorted(set(recorded) - set(current))
    changed = sorted(k for k in set(recorded) & set(current) if recorded[k] != current[k])
    check(not missing and not changed, "Original Phase 1 producer changed")
    check(all(sha_file(Path(k)) == h for k, h in recorded.items()), "Producer hash mismatch")
    for name, expected in manifest["files"].items():
        p = root / name
        check(
            p.resolve().is_relative_to(root.resolve()) and sha_file(p) == expected,
            "Phase 1 payload changed",
        )
    legacy_error = None
    try:
        check_prepared(root)
    except PreparationError as exc:
        legacy_error = str(exc)
        check(
            legacy_error
            == "Preparation code/config changed; regenerate and review annotations before reuse",
            "Unexpected legacy failure",
        )
        check(set(current) > set(recorded), "Refusal is not explained by added unrelated modules")
    return {
        "recorded_code_and_payloads": "passed",
        "producer_files_checked": len(recorded),
        "payloads_checked": len(manifest["files"]),
        "added_top_level_modules": sorted(set(current) - set(recorded)),
        "legacy_check_prepared_error": legacy_error,
        "legacy_commands_ready": legacy_error is None,
        "scope": "Read-only inspection; no gate changed or manifest rewritten",
    }


def recount(studies, final):
    counters = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    checked = 0
    for spec, root in studies:
        with sqlite3.connect(f"file:{(root / 'queries.sqlite').resolve()}?mode=ro", uri=True) as db:
            check(
                db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
                == sum(len(c["probes"]) * 6 for c in spec["cells"]),
                "Wrong outcome count",
            )
            for cell in spec["cells"]:
                for arm in ["static", "R", "C", "M", "S", "no_memory"]:
                    for probe in cell["probes"]:
                        key = digest([cell["episode_id"], arm, probe["probe_id"]])
                        row = db.execute(
                            "SELECT json_extract(body,'$.observation'),"
                            "json_extract(body,'$.judge.hit') FROM outcomes WHERE key=?",
                            (key,),
                        ).fetchone()
                        check(
                            row is not None and row[1] in (0, 1), "Missing/invalid saved judgment"
                        )
                        obs, hit = json.loads(row[0]), bool(row[1])
                        check(
                            obs["outcome"] is hit
                            and obs["arm"] == arm
                            and obs["probe_id"] == probe["probe_id"],
                            "Saved outcome mismatch",
                        )
                        metric = {
                            "attack": "asr",
                            "retention": "retention",
                            "restraint": "restraint",
                        }[probe["metric"]]
                        success = not hit if metric == "restraint" else hit
                        totals = counters[cell["scenario"], arm]
                        totals[metric][0] += int(success)
                        totals[metric][1] += 1
                        if metric in {"retention", "restraint"}:
                            totals["combined_benign"][0] += int(success)
                            totals["combined_benign"][1] += 1
                        checked += 1
    for (scenario, arm), metrics in counters.items():
        for metric, (n, den) in metrics.items():
            saved = final["regimes"][scenario][arm]["metrics"][metric]
            check((n, den) == (saved["numerator"], saved["denominator"]), "Report count mismatch")
    return {
        "status": "passed",
        "saved_outcomes_checked": checked,
        "method_conditions": len(counters),
        "metrics_per_condition": 4,
        "source": "Saved judge hits and fixed probe categories; no new judgments",
    }


def recount_original(history):
    def truth(value):
        check(value in {"0", "1"}, "Unexpected saved CSV boolean")
        return value == "1"

    with (history / "mpbench_outcomes.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    check(len(rows) == len({r["cid"] for r in rows}) == 5996, "Original read coverage changed")
    attack = [r for r in rows if truth(r["is_adversarial"])]
    benign = [r for r in rows if not truth(r["is_adversarial"]) and truth(r["benign_scorable"])]
    retained = [r for r in benign if truth(r["benign_warranted"])]
    restrained = [r for r in benign if not truth(r["benign_warranted"])]
    metrics = {
        "asr": [sum(truth(r["attack_succeeded"]) for r in attack), len(attack)],
        "retention": [sum(truth(r["answer_correct"]) for r in retained), len(retained)],
        "restraint": [sum(truth(r["answer_correct"]) for r in restrained), len(restrained)],
        "combined_benign": [sum(truth(r["answer_correct"]) for r in benign), len(benign)],
    }
    check(
        metrics
        == {
            "asr": [176, 2999],
            "retention": [213, 249],
            "restraint": [1273, 2607],
            "combined_benign": [1486, 2856],
        },
        "Original reproduction counts differ from the report",
    )
    with (history / "written_memories-no_defence.jsonl").open() as stream:
        writes = [json.loads(line) for line in stream]
    check(len(writes) == len({r["cid"] for r in writes}) == 6240, "Original write coverage changed")
    check(sum(len(r["written"]) for r in writes) == 22089, "Original claim count changed")
    check(all(r["answer"].strip() for r in rows), "Empty original answer")
    return {
        "status": "passed",
        "unique_ingestions": len(writes),
        "read_outcomes": len(rows),
        "saved_claims": 22089,
        "metrics": metrics,
        "scope": "Read saved outputs; no new extraction, model call or judgment",
    }


def inspect():
    out = {"phase1": phase1_archive(Path("research_data/mpbench_phase1"))}
    out["recovery"] = validate_outputs(Path("research_data/mpbench_recovery_v1_20261029"))
    out["provisional"] = check_provisional(Path("research_data/mpbench_provisional_v1_20261029"))
    out["native"] = check_native(Path("research_data/dynamic_native_stores_v1_20261031"))
    _, first = check_first(Path("research_data/provisional_comparison_freeze_v1_20261101"))
    _, extension = check_extension(Path("research_data/provisional_extension_freeze_v1_20261101"))
    out["execution_freezes"] = {
        "status": "passed",
        "cells": len(first["cells"]) + len(extension["cells"]),
    }
    out["focused_human_review"] = review_status(
        Path("research_data/focused_review_workflow_v1_20261101")
    )
    delivery = read(Path("reports/PROVISIONAL_RESULTS_20261101_DELIVERY.json"))
    check(digest(delivery["files"]) == delivery["hash"], "Invalid prior delivery map")
    changed = [n for n, h in delivery["files"].items() if sha_file(Path(n)) != h]
    check(not changed, f"Prior delivery changed: {changed}")
    out["prior_results_delivery"] = {"status": "passed", "files_checked": len(delivery["files"])}
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "src/ams/memory", "src/ams/core", "prompts"]
        )
        .decode()
        .split("\0")
    )
    paths = [p for p in paths if p]
    changed = [
        p
        for p in paths
        if Path(p).read_bytes() != subprocess.check_output(["git", "show", f"HEAD:{p}"])
    ]
    check(not changed, "Original memory/core/prompts changed")
    out["original_memory_core_prompts"] = {"status": "passed", "tracked_files_checked": len(paths)}
    history = Path(
        "results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z"
    )
    data = read(history / "dataset_integrity.json")
    check(
        all(sha_file(Path("data/mpbench") / n) == h for n, h in data["files"].items()),
        "Official data changed",
    )
    out["official_mpbench_bytes"] = {
        "status": "passed",
        "files_checked": len(data["files"]),
        "ingestions": data["ingestions"],
    }
    out["original_reproduction_recount"] = recount_original(history)
    final = read(Path("research_data/development_comparison_report_v1_20261101/comparison.json"))
    out["independent_result_recount"] = recount(
        [
            (first, Path("research_data/provisional_comparison_results_v1_20261101")),
            (extension, Path("research_data/provisional_extension_results_v1_20261101")),
        ],
        final,
    )
    session = Path("research_data/dynamic_execution_prep_v1_20261031/session")
    with sqlite3.connect(f"file:{(session / 'budget.sqlite').resolve()}?mode=ro", uri=True) as db:
        used, held, blocked = db.execute(
            "SELECT used_nanodollars,held_nanodollars,blocked FROM budget_config"
        ).fetchone()
        reservations = dict(db.execute("SELECT state,COUNT(*) FROM reservations GROUP BY state"))
    with sqlite3.connect(f"file:{(session / 'dispatch.sqlite').resolve()}?mode=ro", uri=True) as db:
        dispatches = dict(db.execute("SELECT status,COUNT(*) FROM dispatches GROUP BY status"))
    check(
        used == "2094123450"
        and int(held) == 0
        and blocked == 0
        and set(reservations) == {"settled"}
        and set(dispatches) == {"completed"},
        "Budget changed or has unresolved requests; review this audit's dated scope",
    )
    out["research_budget"] = {
        "status": "passed",
        "used_usd": "2.09412345",
        "remaining_usd": "27.90587655",
        "held_usd": "0",
        "dispatches": dispatches,
        "reservations": reservations,
        "new_audit_cost_usd": "0",
    }
    out["status"] = "passed_with_known_legacy_validator_limitation"
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Use a new audit report path")
    with no_network():
        result = inspect()
        new_json(args.out, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
