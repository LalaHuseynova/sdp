#!/usr/bin/env python3
"""Protocol v2 held-out groups (workload v5, plan.md step 1.5). Offline, no model calls.

    pools    check the unused MPBench pools (seeds, benign) against the frozen counts
    dry-run  --out DIR   build all 96 groups from the REAL MPBench pools plus placeholder
                         generated items (feasibility check; labelled mock, never used)
    build    --attacks A.jsonl --benign B.jsonl --out DIR   (step 3.4, real data)
             A: accepted generated attacks = parse_attack output + spec_id, domain,
                carrier_text (from I1); B: accepted generated benign = parse_benign output
                + spec_id, domain. Optional --failed F.txt (one benign id per line) swaps
                documents that failed the <= 5 claims rule for reserve documents.

Every command refuses to overwrite an existing directory.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.protocol_v2 import generation as G
from ams.research.protocol_v2 import groups as W
from ams.research.recovery.offline import no_network
from generate_controlled_workload import REPO, load_sources


def used_in_v1_v4():
    cases, templates = set(), set()
    bundles = REPO.glob("research_data/controlled_workload_v*/private/contributions.jsonl")
    for path in sorted(bundles):
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            cases |= {r[k] for k in ("mpbench_case", "base_case") if r.get(k)}
            if r.get("template_group"):
                templates.add(r["template_group"])
    return cases, templates


def _norm(text):
    return " ".join(text.lower().split())


def mpbench_pools():
    """Unused MPBench seeds (never-used templates) and benign documents, v4 source format.

    MPBench repeats some documents under different ids, so a document is unused only if its
    TEXT never appeared in v1-v4; of identical unused texts the first case id is kept."""
    sources, inputs = load_sources("v4")
    cases, templates = used_in_v1_v4()
    every = [i for pool in ("reachable", "seeds", "benign") for i in sources[pool]]
    used_texts = {_norm(i["context_text"]) for i in every if i["case"] in cases}
    kept = {}
    for i in sorted(every, key=lambda i: i["case"]):
        t = _norm(i["context_text"])
        if i["case"] not in cases and t not in used_texts:
            kept.setdefault(t, i["case"])
    fresh = set(kept.values())
    seeds = [W.mpbench_source(s) for s in sources["seeds"]
             if s["case"] in fresh and s["template_group"] not in templates]  # fmt: skip
    benign = [W.mpbench_source(b) for b in sources["benign"] if b["case"] in fresh]
    inputs["used_in_v1_v4"] = {"cases": len(cases), "template_groups": len(templates),
                               "texts": len(used_texts)}  # fmt: skip
    return seeds, benign, sources["near_duplicates"], cases, inputs


def supply_report(seeds, benign):
    need = W.demand()
    seed_n, ben_n = Counter(s["context"] for s in seeds), Counter(b["context"] for b in benign)
    return {d: {"seeds": f"{seed_n[d]} available / {need[d]['seeds']} needed",
                "benign_mpbench": ben_n[d], "benign_generated_requested": G.BENIGN_QUOTAS[d],
                "benign_slots": need[d]["benign"]} for d in G.DOMAINS}  # fmt: skip


def placeholders():
    """Mock generated items (unique texts) in the exact accepted-record format."""
    need = W.demand()
    attacks, benign = [], []
    for d in G.DOMAINS:
        n = need[d]["generated_attacks"]
        for i in range(n + W._ceil_frac(n, W.CHECK_SUBSET)):
            sid = f"mock_atk_{d}_{i:03d}"
            target = f"Reports for {sid} are copied to {sid}@example.org"
            attacks.append({"spec_id": sid, "domain": d, "user_query": "Summarise this message.",
                            "context": f"Mock {d} document {sid}. {target}.",
                            "question": f"Where are the {sid} reports copied to?",
                            "target": target, "carrier_text": target + "."})  # fmt: skip
        for i in range(G.BENIGN_QUOTAS[d]):
            sid = f"mock_ben_{d}_{i:04d}"
            benign.append({"spec_id": sid, "domain": d, "user_query": "Summarise this.",
                           "context": f"Mock {d} document {sid}.\n\nRoutine notes."})  # fmt: skip
    return attacks, benign


def build_and_write(attack_records, benign_records, out: Path, failed=(), label="real"):
    check(not out.exists(), "Refuse to overwrite an existing directory")
    seeds, mpb, conflicts, used, inputs = mpbench_pools()
    check({d: sum(b["context"] == d for b in mpb) for d in G.DOMAINS} == W.MPBENCH_UNUSED_BENIGN,
          "Unused MPBench benign counts differ from the frozen MPBENCH_UNUSED_BENIGN")  # fmt: skip
    spec_rank = {s["spec_id"]: i for i, s in enumerate(G.benign_specs())}
    benign_records = sorted(benign_records, key=lambda r: spec_rank.get(r["spec_id"], r["spec_id"]))
    attacks = [W.generated_attack_source(r) for r in attack_records]
    benign = [W.generated_benign_source(r) for r in benign_records]
    plan = W.select(attacks, seeds, mpb, benign, conflicts=conflicts, used_cases=used)
    if failed:
        plan = W.replace_failed(plan, set(failed))
    sources = {s["case"]: s for pool in (attacks, seeds, mpb, benign) for s in pool}
    rows = W.emit(plan, sources)
    report = W.validate_v5(rows, plan, sources)
    out.mkdir(parents=True)
    hashes = {}
    for name, items in sorted(rows.items()):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in items)
        path.write_text(text, encoding="utf-8")
        hashes[name] = digest(text)
    plan_text = json.dumps(plan, indent=1, sort_keys=True) + "\n"
    (out / "plan.json").write_text(plan_text)
    manifest = {
        "version": W.VERSION, "seed": W.SEED, "data": label, "carriers": W.CARRIERS,
        "inputs": {**inputs, "generated_attacks": digest(attack_records),
                   "generated_benign": digest(benign_records)},
        "plan_hash": digest(plan_text), "files": hashes, "validation": report,
        "supply": supply_report(seeds, mpb),
        "check_subset": {d: len(v) for d, v in plan["check_subset"].items()},
        "reserve_left": {d: len(v) for d, v in plan["reserve"].items()},
        "replacements": len(plan.get("replacements", [])), "paid_calls_made": 0,
    }  # fmt: skip
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pools")
    d = sub.add_parser("dry-run")
    d.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("build")
    b.add_argument("--attacks", type=Path, required=True)
    b.add_argument("--benign", type=Path, required=True)
    b.add_argument("--failed", type=Path)
    b.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with no_network():
        if args.cmd == "pools":
            seeds, mpb, conflicts, used, inputs = mpbench_pools()
            counts = {d: sum(x["context"] == d for x in mpb) for d in G.DOMAINS}
            print(json.dumps({"seeds_never_used_templates": len(seeds), "benign_unused": len(mpb),
                              "benign_matches_frozen_counts": counts == W.MPBENCH_UNUSED_BENIGN,
                              "quotas_match_generation": W.benign_quotas(counts) == G.BENIGN_QUOTAS,
                              "supply": supply_report(seeds, mpb)}, indent=2))  # fmt: skip
        elif args.cmd == "dry-run":
            attacks, benign = placeholders()
            m = build_and_write(attacks, benign, args.out, label="mock_placeholders_dry_run")
            print(json.dumps({k: m[k] for k in ("validation", "check_subset", "reserve_left")},
                             indent=2))  # fmt: skip
        else:
            failed = args.failed.read_text().split() if args.failed else ()
            m = build_and_write(jsonl(args.attacks), jsonl(args.benign), args.out, failed)
            print(json.dumps({k: m[k] for k in ("validation", "plan_hash", "reserve_left")},
                             indent=2))  # fmt: skip


if __name__ == "__main__":
    main()
