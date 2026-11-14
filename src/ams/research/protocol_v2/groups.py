"""Protocol v2, plan.md step 1.5: the fresh held-out group builder (workload v5).

96 independent groups with exactly the v4 group layout (40 contributions, same roles,
overlays, audits and probes, written by the shared `generator.emit_group`). Only the
SOURCES change, and no document is used by more than one group:

  per block (X, Y)  scored_1, scored_2, seed_a   generated attacks (passed E1-E4, E2, I1)
                    seed_b                       unused MPBench seed case, never-used template
                    13 (X) / 14 (Y) benign       unused MPBench benign first, then generated
seed_a is copied (linked copy) and relayed (unlinked copy), so like v4's seed_a it must
be reachable; MPBench seeds are not (their questions are not 'description').

Everything is assigned by a fixed hash or spec order before any evaluation; nothing
here reads a model outcome. Three steps, all pure:
  select(...)           -> plan  (JSON: which document goes where; check subset; reserve)
  replace_failed(plan)  -> plan  (a generated benign document failing the <= 5 claims rule
                                  after Stage 1 is swapped, in place, for the next reserve
                                  document of its domain)
  emit(plan, sources)   -> rows  (v4 rows via generator.emit_group)
"""

from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict

from ams.research.dynamic.models import check as require
from ams.research.dynamic.models import digest
from ams.research.protocol_v2.generation import DOMAINS
from ams.research.workload import design as D
from ams.research.workload.generator import emit_group, validate, validate_v2
from ams.research.workload.quality_v4 import relay_text

VERSION = "protocol-v2-workload-v5"
SEED = "protocol-v2-workload-v5-20261114"
SPLIT = "heldout"
N_GROUPS = 96
CARRIERS = "v4"  # same carriers and data-quality rules as the v4 test split
GENERATED_PER_BLOCK = 3  # scored_1, scored_2, seed_a
CHECK_SUBSET = 0.10  # generation-check subset, outside the groups (>= 10% per domain)
RESERVE = 0.20

# Unused MPBench benign documents per domain: the load_sources benign pool minus every case
# or copy base used in v1-v4, minus documents whose TEXT was used in v1-v4 (MPBench repeats
# texts under other ids), one per identical text. 963 in total (not the 1,154 counted by id
# on 12 Nov). `scripts/build_workload_v5.py pools` recomputes and checks it.
MPBENCH_UNUSED_BENIGN = {"calendar": 101, "slack": 144, "email": 157, "file_and_doc": 85,
                         "web": 214, "script_execution": 262}  # fmt: skip


def benign_roles(block: str) -> list[str]:
    """The benign roles of a block, in the order v4 fills them."""
    roles = [f"A_benign_{i}" for i in range(D.A_BENIGN[block])]
    roles += [f"B_benign_{i}" for i in range(D.B_BENIGN_PER_CONTEXT)]
    roles += [f"U_benign_{i}" for i, b in enumerate(D.U_BENIGN) if b == block]
    return roles + (["U_copy_base"] if block == "Y" else [])


def domain_pairs(n_groups: int = N_GROUPS) -> list[tuple[str, str]]:
    """(X, Y) domains per group. With 96 groups every domain is X 16 times and Y 16 times,
    and X != Y: group 6m+d has X = d and Y = d + 1 + (m mod 5)."""
    names = list(DOMAINS)
    k = len(names)
    return [(names[g % k], names[(g % k + 1 + (g // k) % (k - 1)) % k]) for g in range(n_groups)]


def demand(n_groups: int = N_GROUPS) -> dict:
    """Per domain: blocks, generated attacks, MPBench seeds and benign slots needed."""
    out = {d: Counter() for d in DOMAINS}
    for x, y in domain_pairs(n_groups):
        for block, d in (("X", x), ("Y", y)):
            out[d]["blocks"] += 1
            out[d]["generated_attacks"] += GENERATED_PER_BLOCK
            out[d]["seeds"] += 1
            out[d]["benign"] += len(benign_roles(block))
    return {d: dict(c) for d, c in out.items()}


def _ceil_frac(n: int, frac: float) -> int:
    return -(-round(n * frac * 1000) // 1000)


def benign_quotas(mpbench_unused: dict = MPBENCH_UNUSED_BENIGN, n_groups: int = N_GROUPS) -> dict:
    """Generated benign documents to request per domain: shortfall + 20% reserve, rounded up."""
    need = demand(n_groups)
    return {d: _ceil_frac(max(need[d]["benign"] - mpbench_unused[d], 0), 1 + RESERVE)
            for d in DOMAINS}  # fmt: skip


def _hash_order(items, tag):
    return sorted(items, key=lambda i: digest([SEED, tag, i["case"]]))


def _take(queue, n, tag, questions, members, conflicts, used_templates=None):
    """Take the first n eligible items of `queue` (removed from it). An item is skipped (and
    stays queued) if its question is already probed in the group or it near-duplicates a
    member; an MPBench seed whose template was already used is dropped for good."""
    out, i = [], 0
    while len(out) < n and i < len(queue):
        item = queue[i]
        if used_templates is not None and item["template_group"] in used_templates:
            queue.pop(i)
            continue
        q = (item.get("question") or "").strip().lower()
        if (q and q in questions) or any(c in members for c in conflicts.get(item["case"], ())):
            i += 1
            continue
        out.append(queue.pop(i))
        questions.add(q)
        members.add(item["case"])
        if used_templates is not None:
            used_templates.add(item["template_group"])
    require(len(out) == n, f"Insufficient supply for {tag}: stop and report (no top-up)")
    return out


def select(attacks, seeds, benign_mpbench, benign_generated, *, conflicts=None,
           used_cases=frozenset(), n_groups: int = N_GROUPS) -> dict:  # fmt: skip
    """The full assignment. Inputs are generator-format sources with `case` (unique id) and
    `context` (domain). `attacks`: generated attacks that passed every rule; `benign_generated`:
    accepted generated benign documents in spec order (the order fixes use vs reserve);
    `conflicts`: case -> near-duplicate cases (v4 rule); `used_cases`: every v1-v4 case."""
    conflicts = conflicts or {}
    pools = [attacks, seeds, benign_mpbench, benign_generated]
    ids = [i["case"] for pool in pools for i in pool]
    require(len(ids) == len(set(ids)), "A document id appears twice in the input pools")
    require(not set(ids) & set(used_cases), "An input document was already used in v1-v4")

    def by_domain(items):
        out = {d: [] for d in DOMAINS}
        for i in items:
            out[i["context"]].append(i)
        return out

    need = demand(n_groups)
    atk, check_subset = {}, {}
    for d, items in by_domain(attacks).items():
        ordered, n = _hash_order(items, "attack"), need[d]["generated_attacks"]
        require(len(ordered) >= n, f"Only {len(ordered)} accepted attacks for {d}; {n} needed: "
                "stop and report (no top-up)")  # fmt: skip
        atk[d], check_subset[d] = ordered[:n], ordered[n : n + _ceil_frac(n, CHECK_SUBSET)]
    sd = {d: _hash_order(v, "seed") for d, v in by_domain(seeds).items()}
    mpb = {d: _hash_order(v, "benign") for d, v in by_domain(benign_mpbench).items()}
    gen = by_domain(benign_generated)  # spec order
    # Spread each domain's MPBench benign documents evenly over that domain's blocks.
    n_mpb = {d: min(len(mpb[d]), need[d]["benign"]) for d in DOMAINS}
    seen_blocks, used_templates, groups = Counter(), set(), []
    for g, (x, y) in enumerate(domain_pairs(n_groups)):
        gid = f"G-H{g:02d}"
        questions, members, items = set(), set(), []
        for block, d in (("X", x), ("Y", y)):
            scored_1, scored_2, seed_a = _take(atk[d], 3, f"{gid}{block} attacks", questions,
                                               members, conflicts)  # fmt: skip
            (seed_b,) = _take(sd[d], 1, f"{gid}{block} seed", questions, members, conflicts,
                              used_templates)  # fmt: skip
            j, nb = seen_blocks[d], need[d]["blocks"]
            seen_blocks[d] += 1
            roles = benign_roles(block)
            k = (j + 1) * n_mpb[d] // nb - j * n_mpb[d] // nb
            require(len(gen[d]) >= len(roles) - k, f"Insufficient generated benign for {d}: "
                    "stop and report")  # fmt: skip
            docs = [mpb[d].pop(0) for _ in range(k)] + [gen[d].pop(0) for _ in roles[k:]]
            random.Random(digest([SEED, "benign-roles", gid, block])).shuffle(docs)
            items += [[block, "scored_1", "attack", scored_1["case"]],
                      [block, "scored_2", "attack", scored_2["case"]],
                      [block, "seed_a", "attack", seed_a["case"]],
                      [block, "seed_b", "attack", seed_b["case"]]]  # fmt: skip
            items += [[block, r, "benign", doc["case"]] for r, doc in zip(roles, docs, strict=True)]
        groups.append({"group_id": gid, "blocks": {"X": x, "Y": y}, "items": items})
    return {
        "version": VERSION, "seed": SEED, "n_groups": n_groups, "groups": groups,
        "check_subset": {d: [i["case"] for i in v] for d, v in check_subset.items()},
        "reserve": {d: [i["case"] for i in v] for d, v in gen.items()},
        "unused_mpbench_benign": {d: [i["case"] for i in v] for d, v in mpb.items()},
    }  # fmt: skip


def replace_failed(plan: dict, failed: set) -> dict:
    """Swap each failed generated benign document, in place, for the next reserve document
    of its domain (fixed order). Only the affected slots change."""
    plan = copy.deepcopy(plan)
    reserve = plan["reserve"]
    replaced = []
    for group in plan["groups"]:
        for item in group["items"]:
            if item[3] in failed:
                domain = group["blocks"][item[0]]
                require(item[2] == "benign", f"Only benign documents are replaceable: {item[3]}")
                require(reserve[domain], f"Reserve exhausted for {domain}: stop and report")
                new = reserve[domain].pop(0)
                replaced.append({"group_id": group["group_id"], "slot": item[:2],
                                 "old": item[3], "new": new})  # fmt: skip
                item[3] = new
    require(len(replaced) == len(failed), "A failed document is not in any group")
    plan.setdefault("replacements", []).extend(replaced)
    return plan


def generated_attack_source(record: dict) -> dict:
    """An accepted generated attack -> generator source. `record` = parse_attack output +
    `spec_id`, `domain` and I1's `carrier_text` (the v4 relay rule replaces a bare fragment)."""
    return {
        "case": record["spec_id"], "context": record["domain"], "template_group": None,
        "user_query": record["user_query"], "context_text": record["context"],
        "question": record["question"], "target": record["target"],
        "carrier_text": relay_text(record["carrier_text"], record["context"], record["target"]),
        "private_extra": {"mpbench_case": None, "generated_id": record["spec_id"],
                          "source": "generated_v2", "extraction": "new_text_paid"},
    }  # fmt: skip


def generated_benign_source(record: dict) -> dict:
    return {"case": record["spec_id"], "context": record["domain"],
            "user_query": record["user_query"], "context_text": record["context"],
            "private_extra": {"mpbench_case": None, "generated_id": record["spec_id"],
                              "source": "generated_v2"}}  # fmt: skip


def mpbench_source(item: dict) -> dict:
    return {**item, "private_extra": {"source": "mpbench"}}


def emit(plan: dict, sources: dict) -> dict:
    """v4-format rows for every group. `sources`: case -> generator source."""
    rows = defaultdict(list)
    for group in plan["groups"]:
        items = {(b, r): (kind, sources[case]) for b, r, kind, case in group["items"]}
        emit_group(rows, SPLIT, group["group_id"], group["blocks"], items, SEED, CARRIERS)
    return dict(rows)


def validate_v5(rows: dict, plan: dict, sources: dict) -> dict:
    """v4 invariants + independence: no document id or text in two groups or two slots."""
    validate(rows)
    validate_v2(rows)
    where, texts = {}, {}
    for group in plan["groups"]:
        require(len(group["items"]) == 2 * 4 + sum(len(benign_roles(b)) for b in "XY"),
                f"{group['group_id']} size")  # fmt: skip
        for *_, case in group["items"]:
            require(case not in where, f"{case} in {where.get(case)} and {group['group_id']}")
            where[case] = group["group_id"]
            text = " ".join(sources[case]["context_text"].lower().split())
            require(text not in texts, f"Same text in {case} and {texts.get(text)}")
            texts[text] = case
    outside = {c for v in plan["check_subset"].values() for c in v}
    outside |= {c for v in plan["reserve"].values() for c in v}
    require(not outside & set(where), "A check-subset or reserve document is inside a group")
    roles = ("benign_with_fact", "attack_seed", "attack_scored")
    by_source = Counter(r.get("source", "mpbench") for r in rows["private/contributions.jsonl"]
                        if r["role"] in roles)  # fmt: skip
    return {"groups": len(plan["groups"]), "documents": len(where),
            "contributions_by_source": dict(by_source), "status": "valid"}
