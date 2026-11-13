#!/usr/bin/env python3
"""Offline diagnostic of the eight-group provisional comparison (7 Nov 2026).

Answers two questions from saved outcomes only:
1. Which memory records carried each successful attack, and what origin
   (principal / external / unknown) do they have?
2. Which retrieval contexts did S change relative to static SAFE-Mem, why,
   and with what answer effect?

Read-only: verifies every saved outcome hash, blocks networking, makes no
model calls and refuses to overwrite an existing output directory.

    .venv/bin/python scripts/diagnose_provisional_attacks.py \
        --out research_data/attack_carrier_diagnostic_v1_20261107
"""

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.provisional_extension import verify as verify_extension
from ams.research.provisional_run.preparation import read, verify
from ams.research.recovery.offline import no_network

REPO = Path(__file__).resolve().parents[1]
PLANS = [
    REPO / "research_data/provisional_comparison_freeze_v1_20261101",
    REPO / "research_data/provisional_extension_freeze_v1_20261101",
]
DBS = [
    REPO / "research_data/provisional_comparison_results_v1_20261101/queries.sqlite",
    REPO / "research_data/provisional_extension_results_v1_20261101/queries.sqlite",
]
ARMS = ("static", "R", "C", "M", "S")


def load():
    _, spec = verify(PLANS[0])
    _, ext = verify_extension(PLANS[1])
    cells = [*spec["cells"], *ext["cells"]]
    episodes = {f.stem: read(f) for root in PLANS for f in (root / "private").glob("ep_*.json")}
    meta = {}
    for c in cells:
        queries = {q["query_id"]: q for q in episodes[c["episode_id"]]["queries"]}
        for p in c["probes"]:
            q = queries[p["probe_id"]]
            meta[c["episode_id"], p["probe_id"]] = {
                "group": c["group_id"],
                "scenario": c["scenario"],
                "metric": p["metric"],
                "relation": p.get("relation"),
                "input_id": p["input_id"],
                "question": q["text"],
                "expected": q.get("expected_memory"),
            }
    prov = {
        e: {d["record_id"]: d for d in ep["provenance_decisions"]} for e, ep in episodes.items()
    }
    rows = []
    for db in DBS:
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
            for text, h in con.execute("SELECT body,hash FROM outcomes ORDER BY rowid"):
                v = json.loads(text)
                check(digest(v) == h, "Changed saved outcome")
                o = v["observation"]
                m = meta[o["episode_id"], o["probe_id"]]
                trace = v["actual"].get("retrieval", {}).get("trace", {})
                pv = prov[o["episode_id"]]
                cands = []
                for c in trace.get("candidates", []):
                    d = c["decision"]
                    if not (c["selected"] or d["penalty"] > 0 or d["reason"] == "source_risk_gate"):
                        continue
                    p = pv.get(c["record_id"], {})
                    cands.append(
                        {
                            "record_id": c["record_id"],
                            "native_id": c["native_id"],
                            "kind": c["record_kind"],
                            "selected": c["selected"],
                            "origin": p.get("origin_group"),
                            "contribution": p.get("contribution_id"),
                            "reason": d["reason"],
                            "penalty": d["penalty"],
                            "scopes": d.get("active_scopes"),
                            "counts": d.get("counts"),
                        }
                    )
                admitted_ext = sum(
                    c["original_authority_allowed"]
                    and c["original_source_allowed"]
                    and pv.get(c["record_id"], {}).get("origin_group") == "external"
                    for c in trace.get("candidates", [])
                )
                rows.append(
                    {
                        **m,
                        "episode": o["episode_id"],
                        "probe": o["probe_id"],
                        "arm": o["arm"],
                        "outcome": o["outcome"],
                        "answer": v["actual"]["answer"]["text"],
                        "judge_reason": v["judge"].get("reason"),
                        "retrieved_hit": (v.get("retrieved_entry_verdict") or {}).get("hit"),
                        "ctx_hash": digest(trace.get("supplied_context")),
                        "context": trace.get("supplied_context") or [],
                        "cands": cands,
                        "admitted_external": admitted_ext,
                    }
                )
    check(len(rows) == 3888, "Expected 3,888 saved outcomes")
    origins = Counter(
        p["origin_group"] for ep in episodes.values() for p in ep["provenance_decisions"]
    )
    return rows, episodes, origins


def carrier_class(row):
    """Origin class of the record(s) that literally contain the attack target.

    If the retrieval-entry judge found the target in supplied memory, the
    carrier is the selected claim whose text contains the target's
    distinguishing tokens; otherwise the target was absent from memory and the
    answer was produced from the remaining (here always principal) context.
    """
    selected = [c for c in row["cands"] if c["selected"]]
    if not row["retrieved_hit"]:
        kinds = sorted({c["origin"] for c in selected})
        return "target_absent_from_context", kinds, []
    tokens = [t.strip(".,'\"$").lower() for t in (row["expected"] or "").split()]
    tokens = [t for t in tokens if len(t) > 3 or any(ch.isdigit() for ch in t)]
    texts = {}
    for entry in row["context"]:
        head = entry.split("entry_id=", 1)[1].split()[0] if "entry_id=" in entry else ""
        texts[head] = entry.lower()
    # A numeric target (budget, identifier) must match a numeric token, so a
    # claim that merely names the same project is not counted as the carrier.
    # Compare the number itself ("$3.2M" vs "$3.2 million").
    numeric = [n.strip(".,") for t in tokens for n in re.findall(r"\d[\d.,]*", t)]
    carriers = []
    for c in selected:
        text = texts.get(c["native_id"], "")
        score = sum(t in text for t in tokens)
        if numeric and not any(t in text for t in numeric):
            continue
        if c["kind"] == "claim" and score >= 2:
            carriers.append((c["native_id"], c["origin"], c["contribution"]))
    return "target_in_context", sorted({x[1] for x in carriers}), carriers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite an existing diagnostic")
    with no_network():
        rows, episodes, origins = load()
    idx = {(r["episode"], r["probe"], r["arm"]): r for r in rows}
    static = [r for r in rows if r["arm"] == "static"]
    attacks = [r for r in static if r["metric"] == "attack"]

    # 1. Attack successes and their carriers.
    arm_sets = defaultdict(set)
    for r in rows:
        if r["metric"] == "attack" and r["outcome"]:
            arm_sets[r["episode"], r["probe"]].add(r["arm"])
    successes = []
    for r in (r for r in attacks if r["outcome"]):
        status, classes, carriers = carrier_class(r)
        per_arm = {}
        for arm in ("C", "M", "S"):
            other = idx[r["episode"], r["probe"], arm]
            per_arm[arm] = [
                {k: c[k] for k in ("native_id", "origin", "reason", "penalty", "scopes", "counts")}
                for c in other["cands"]
                if c["selected"] and any(c["native_id"] == x[0] for x in carriers)
            ]
        successes.append(
            {
                "group": r["group"],
                "scenario": r["scenario"],
                "input_id": r["input_id"],
                "relation": r["relation"],
                "question": r["question"],
                "expected": r["expected"],
                "answer": r["answer"],
                "judge_reason": r["judge_reason"],
                "retrieved_target_in_context": r["retrieved_hit"],
                "carrier_status": status,
                "carrier_origins": classes,
                "carriers": [
                    {"native_id": a, "origin": b, "contribution_id": c} for a, b, c in carriers
                ],
                "carrier_from_probe_input": any(x[2] == r["input_id"] for x in carriers),
                "selected_origins": dict(Counter(c["origin"] for c in r["cands"] if c["selected"])),
                "carrier_decisions_by_arm": per_arm,
                "arms_with_success": sorted(arm_sets[r["episode"], r["probe"]]),
            }
        )

    def bucket(s):
        if s["carrier_status"] == "target_absent_from_context":
            return "principal_context_target_absent"
        return "+".join(s["carrier_origins"]) or "unidentified"

    # 2. Contexts changed vs static.
    changed = {}
    for arm in ("R", "C", "M", "S"):
        changed[arm] = [
            r
            for r in rows
            if r["arm"] == arm
            and r["ctx_hash"] != idx[r["episode"], r["probe"], "static"]["ctx_hash"]
        ]
    keys = {a: {(r["episode"], r["probe"]) for r in v} for a, v in changed.items()}
    s_changes = []
    reasons, removed_origin, added_origin, flips = Counter(), Counter(), Counter(), Counter()
    for r in changed["S"]:
        st = idx[r["episode"], r["probe"], "static"]
        ssel = {c["record_id"]: c for c in r["cands"] if c["selected"]}
        tsel = {c["record_id"]: c for c in st["cands"] if c["selected"]}
        scand = {c["record_id"]: c for c in r["cands"]}
        removed = []
        for k, c in tsel.items():
            if k in ssel:
                continue
            sc = scand.get(k)
            reason = sc["reason"] if sc else "ranked_out"
            reasons[reason] += 1
            removed_origin[c["origin"]] += 1
            removed.append(
                {
                    "native_id": c["native_id"],
                    "origin": c["origin"],
                    "reason": reason,
                    "penalty": sc["penalty"] if sc else None,
                    "scopes": sc["scopes"] if sc else None,
                }
            )
        added = [
            {"native_id": c["native_id"], "origin": c["origin"]}
            for k, c in ssel.items()
            if k not in tsel
        ]
        for c in added:
            added_origin[c["origin"]] += 1
        flips[f"{r['metric']}:{st['outcome']}->{r['outcome']}"] += 1
        s_changes.append(
            {
                "group": r["group"],
                "scenario": r["scenario"],
                "metric": r["metric"],
                "relation": r["relation"],
                "question": r["question"],
                "static_outcome": st["outcome"],
                "S_outcome": r["outcome"],
                "C_outcome": idx[r["episode"], r["probe"], "C"]["outcome"],
                "M_outcome": idx[r["episode"], r["probe"], "M"]["outcome"],
                "order_only_change": not removed and not added,
                "removed": removed,
                "added": added,
                "same_context_as_C": r["ctx_hash"]
                == idx[r["episode"], r["probe"], "C"]["ctx_hash"],
                "same_context_as_M": r["ctx_hash"]
                == idx[r["episode"], r["probe"], "M"]["ctx_hash"],
            }
        )

    selected_attack = Counter(
        f"{c['kind']}:{c['origin']}" for r in attacks for c in r["cands"] if c["selected"]
    )
    summary = {
        "status": "complete_offline_diagnostic",
        "paid_api_calls": 0,
        "saved_outcomes_verified": len(rows),
        "attack_successes": {
            "static_events": len(successes),
            "distinct_group_inputs": len({(s["group"], s["input_id"]) for s in successes}),
            "identical_success_set_across_static_R_C_M_S": all(
                set(v) == set(ARMS) for v in arm_sets.values()
            ),
            "by_carrier_bucket": dict(Counter(bucket(s) for s in successes)),
            "carrier_from_probe_input": sum(s["carrier_from_probe_input"] for s in successes),
        },
        "workload_reachability": {
            "static_attack_probes": len(attacks),
            "attack_probes_with_admitted_attributed_external_candidate": sum(
                r["admitted_external"] > 0 for r in attacks
            ),
            "static_attack_selected_occurrences_by_kind_origin": dict(selected_attack),
            "attack_probes_with_target_in_retrieved_context": sum(
                bool(r["retrieved_hit"]) for r in attacks
            ),
            "record_origin_distribution_all_episodes": dict(origins),
        },
        "changed_contexts_vs_static": {
            **{arm: len(v) for arm, v in changed.items()},
            "S_subset_of_M": keys["S"] <= keys["M"],
            "S_in_C": len(keys["S"] & keys["C"]),
            "S_identical_context_to_C": sum(c["same_context_as_C"] for c in s_changes),
            "S_identical_context_to_M": sum(c["same_context_as_M"] for c in s_changes),
            "S_order_only_changes": sum(c["order_only_change"] for c in s_changes),
            "S_removed_by_reason": dict(reasons),
            "S_removed_by_origin": dict(removed_origin),
            "S_added_by_origin": dict(added_origin),
            "S_outcome_transitions": dict(flips),
        },
    }
    args.out.mkdir(parents=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.out / "attack_successes.json").write_text(json.dumps(successes, indent=2) + "\n")
    (args.out / "s_changed_contexts.json").write_text(json.dumps(s_changes, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
