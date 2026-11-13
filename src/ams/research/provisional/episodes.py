"""Case-intent development groups. Y_case is never a memory/use safety label."""

from __future__ import annotations

import copy
import re
from collections import Counter, defaultdict
from fractions import Fraction

from ams.research.phase1_blinding import keyed_id
from ams.research.phase1_common import ARMS, CONTEXTS, digest, opaque, require, rng, stage_seed
from ams.research.phase1_scenarios import SCENARIOS, policy_sets, weighted_subset

COUNTS = {"attack": 10, "explicit_benign": 1, "suggestive_benign": 5}
FORBIDDEN = {
    "Y_case",
    "Z_bundle",
    "expected_memory",
    "original_case_key",
    "stratum",
    "scenario",
    "profiles",
    "omega_source",
    "omega_batch",
    "verified_verdict",
    "automated_warnings",
    "quality_flags",
    "legacy_entry_id",
    "legacy_source_ids",
}


def validate_bag(bag: list[dict]):
    require(len(bag) == 32, "A provisional bag must contain 32 contributions")
    require(len({r["contribution_id"] for r in bag}) == 32, "Repeated source case")
    require(len({r["group_id"] for r in bag}) == 32, "Repeated input/template component")
    for context in CONTEXTS:
        rows = [r for r in bag if r["context_id"] == context]
        require(Counter(r["stratum"] for r in rows) == Counter(COUNTS), "Wrong case-intent strata")
        require(
            all(r["Y_case"] is (r["stratum"] == "attack") for r in rows),
            "Original case-label/stratum inconsistency",
        )


def select_bags(rows: list[dict], groups: list[dict], n_bags: int = 20) -> list[list[dict]]:
    """Deterministic bipartite matching avoids greedy starvation of scarce strata.

    Each duplicate/template component has capacity one across all bags. No warning,
    question quality, source safety guess or historical attack outcome is an input.
    """
    blocked = {g["group_id"] for g in groups if g["manual_review_required"]}
    pools = defaultdict(list)
    for r in rows:
        if r["review_candidate"] and r["context_id"] in CONTEXTS and r["group_id"] not in blocked:
            pools[(r["context_id"], r["stratum"])].append(r)
    slots, edges, best = [], {}, {}
    for bi in range(n_bags):
        bid = f"D{bi:02d}"
        for context in CONTEXTS:
            for label, count in COUNTS.items():
                for position in range(count):
                    slot = (bid, context, label, position)
                    slots.append(slot)
                    seed = stage_seed(
                        bid, "COMMON", f"provisional-select:{context}:{label}:{position}"
                    )
                    ordered = sorted(
                        pools[(context, label)], key=lambda r: digest([seed, r["contribution_id"]])
                    )
                    choices = {}
                    for r in ordered:
                        choices.setdefault(r["group_id"], r)
                    edges[slot] = list(choices)
                    best[slot] = choices
    slots.sort(key=lambda s: (Fraction(len(edges[s]), n_bags * COUNTS[s[2]]), digest(s)))
    owner = {}

    def augment(slot, seen):
        for gid in edges[slot]:
            if gid in seen:
                continue
            seen.add(gid)
            if gid not in owner or augment(owner[gid], seen):
                owner[gid] = slot
                return True
        return False

    for slot in slots:
        require(
            augment(slot, set()), f"Insufficient independent components for {slot}; no fallback"
        )
    chosen = {slot: best[slot][gid] for gid, slot in owner.items()}
    result = []
    for bi in range(n_bags):
        bid = f"D{bi:02d}"
        bag = [
            chosen[(bid, context, label, p)]
            for context in CONTEXTS
            for label, count in COUNTS.items()
            for p in range(count)
        ]
        validate_bag(bag)
        result.append(bag)
    require(
        len({r["group_id"] for b in result for r in b}) == 32 * n_bags,
        "Template component crosses provisional bags",
    )
    return result


def assignments(bag: list[dict], bid: str, scenario: str) -> tuple[dict, dict]:
    validate_bag(bag)
    require(scenario in SCENARIOS, "Unknown scenario")
    source_weight, batch_weight = map(Fraction, SCENARIOS[scenario])
    users = [opaque("u", "provisional", bid, n) for n in range(2)]
    high_email = rng(bid, "provisional-profile").randrange(2)
    result, hidden = {}, {}
    for ci, context in enumerate(CONTEXTS):
        slots, weights = [], []
        for ui, user in enumerate(users):
            high = ui == (high_email if ci == 0 else 1 - high_email)
            hot = rng(bid, f"provisional-hot:{context}:{ui}").randrange(2)
            for batch in range(2):
                batch_id = opaque("b", "provisional", bid, user, context, batch)
                hidden[batch_id] = {"high_case_intent_profile": high, "hot_batch": batch == hot}
                for _ in range(4):
                    slots.append(
                        {
                            "contributor_id": user,
                            "context_id": context,
                            "batch_id": batch_id,
                            "role": "collaborator",
                        }
                    )
                    weights.append(source_weight ** int(high) * batch_weight ** int(batch == hot))
        random = rng(bid, f"provisional-assignment:{context}", scenario)
        # Ten attack INPUTS per context, not eight unsafe-memory bundles.
        selected = set(weighted_subset(weights, 10, random))
        for attack, positions in (
            (True, sorted(selected)),
            (False, sorted(set(range(16)) - selected)),
        ):
            cases = sorted(
                [r for r in bag if r["context_id"] == context and r["Y_case"] is attack],
                key=lambda r: r["contribution_id"],
            )
            random.shuffle(cases)
            for row, pos in zip(cases, positions, strict=True):
                result[row["contribution_id"]] = slots[pos]
    return result, {
        "scenario": scenario,
        "omega_source": str(source_weight),
        "omega_batch": str(batch_weight),
        "profiles": hidden,
        "controlled_unit": "original_input_case_intent; actual_memory_safety_unknown",
    }


def pending_audits(mapping: dict, bid: str) -> list[str]:
    """Label-independent targets only: no unsafe seed and no invented verdict."""
    random = rng(bid, "provisional-audit-requests")
    root = random.choice(sorted(mapping))
    selected, a = [root], mapping[root]

    def pick(predicate):
        pool = sorted(pid for pid, m in mapping.items() if pid not in selected and predicate(m))
        require(pool, "Missing relational audit target")
        pid = random.choice(pool)
        selected.append(pid)
        return pid

    pick(lambda m: m["batch_id"] == a["batch_id"])
    pick(
        lambda m: (
            m["contributor_id"] == a["contributor_id"]
            and m["context_id"] == a["context_id"]
            and m["batch_id"] != a["batch_id"]
        )
    )
    batches = sorted(
        {
            m["batch_id"]
            for m in mapping.values()
            if m["contributor_id"] == a["contributor_id"] and m["context_id"] != a["context_id"]
        }
    )
    other = random.choice(batches)
    third = pick(lambda m: m["batch_id"] == other)
    a3 = mapping[third]
    pick(
        lambda m: (
            m["contributor_id"] == a3["contributor_id"]
            and m["context_id"] == a3["context_id"]
            and m["batch_id"] != a3["batch_id"]
        )
    )
    return selected


def recode(value, key: bytes, field=""):
    if field in {
        "text",
        "context",
        "user_query",
        "quote",
        "question",
        "answers",
        "expected_memory",
        "retrieval_query",
        "intended_use",
    }:
        return copy.deepcopy(value)
    if isinstance(value, str) and re.fullmatch(r"[a-z]+_[0-9a-f]{24}", value):
        return keyed_id(value, key)
    if isinstance(value, dict):
        return {recode(k, key): recode(v, key, k) for k, v in value.items()}
    if isinstance(value, list):
        return [recode(v, key) for v in value]
    return value


def assert_public(value):
    if isinstance(value, dict):
        require(not set(value) & FORBIDDEN, "Private label/profile in public provisional data")
        for v in value.values():
            assert_public(v)
    elif isinstance(value, list):
        for v in value:
            assert_public(v)


def source_pool(bag: list[dict], catalog: dict, packets: dict, parent_roles: dict) -> dict:
    result = {}
    for row in bag:
        pid = row["contribution_id"]
        base = copy.deepcopy(catalog[pid])
        base["task_principal"] = "user"
        base["validation_status"] = "provisional_unverified"
        base["records"] = []
        for r in packets[pid]["records"]:
            role = parent_roles.get(r["record_id"])
            if r["record_kind"] == "evidence_chunk":
                aids = {s["artifact_id"] for s in r["construction_source_spans"]}
                roles = {a["role"] for a in base["artifacts"] if a["artifact_id"] in aids}
                role = next(iter(roles)) if len(roles) == 1 else None
            base["records"].append(
                {
                    "record_id": r["record_id"],
                    "record_kind": r["record_kind"],
                    "text": r["text"],
                    "content_hash": r["content_hash"],
                    "source_role": role,
                    "construction_source_spans": r["construction_source_spans"],
                    "semantic_attribution_status": "unverified",
                }
            )
        result[pid] = base
    assert_public(result)
    return result


def make_episode(
    bag: list[dict], mapping: dict, hidden: dict, pool: dict, bid: str, key: bytes
) -> dict:
    rows = {r["contribution_id"]: r for r in bag}
    ids = sorted(rows)
    ingestion = ids.copy()
    rng(bid, "provisional-ingestion").shuffle(ingestion)
    order = ids.copy()
    rng(bid, "provisional-original-questions").shuffle(order)
    reserved = pending_audits(mapping, bid)
    events = [{"event": "ingest", "contribution_id": pid} for pid in ingestion]
    for n, pid in enumerate(reserved):
        events.append(
            {
                "event": "audit_request_pending",
                "ticket_id": opaque("t", bid, n),
                "contribution_id": pid,
                "verdict": None,
                "status": "awaiting_genuine_review",
                "completed_verifications": 0,
            }
        )
    gold = {}
    for pid in order:
        if pid in reserved:
            continue
        qid = opaque("q", "provisional-original", bid, pid)
        events.append(
            {
                "event": "original_query",
                "query_id": qid,
                "text": rows[pid]["retrieval_query"],
                "requester": "user",
                "operation": "read",
            }
        )
        gold[qid] = {
            "contribution_id": pid,
            "Y_case": rows[pid]["Y_case"],
            "expected_memory": rows[pid]["expected_memory"],
            "original_case_key": rows[pid]["original_case_key"],
            "stratum": rows[pid]["stratum"],
        }
    overlay = {
        pid: {
            **m,
            "allowed_readers": ["user", "audit_service"],
            "allowed_operations": ["read", "describe", "audit"],
            "write_allowed": True,
            "policy_version": 1,
            "identity_assumption": "synthetic_direct_origin",
        }
        for pid, m in mapping.items()
    }
    counts = defaultdict(Counter)
    for pid, m in mapping.items():
        counts[m["batch_id"]]["attack_input" if rows[pid]["Y_case"] else "benign_input"] += 1
    data = {
        "overlay": overlay,
        "events": events,
        "private": {
            "bag_id": bid,
            "construction": hidden,
            "case_targets": gold,
            "case_labels": {pid: rows[pid]["Y_case"] for pid in ids},
            "reserved_audit_ids": reserved,
            "case_intent_counts_by_batch": dict(counts),
            "permission_plan": policy_sets(mapping, bid),
        },
    }
    data = recode(data, key)
    signature = digest([recode(pool, key), data["overlay"], data["events"]])
    data["shared_arm_inputs"] = {arm: signature for arm in ARMS}
    data["status"] = {
        "development_dataset_ready": True,
        "validated_safety_pilot_ready": False,
        "scientific_evaluation_allowed": False,
        "planned_audit_requests": 5,
        "completed_verifications": 0,
        "human_verified_labels": 0,
    }
    validate_episode(data, recode(pool, key))
    return data


def validate_episode(episode: dict, pool: dict):
    require(
        len(pool) == 32 and set(pool) == set(episode["overlay"]), "Wrong provisional source pool"
    )
    assert_public(pool)
    assert_public(episode["overlay"])
    assert_public(episode["events"])
    for pid, row in pool.items():
        require(
            set(row)
            == {
                "contribution_id",
                "context_id",
                "user_query",
                "context",
                "artifacts",
                "payload_hash",
                "task_principal",
                "validation_status",
                "records",
            },
            "Unexpected public source field",
        )
        require(
            row["contribution_id"] == pid and row["task_principal"] == "user",
            "Source identity/principal mismatch",
        )
        require(row["validation_status"] == "provisional_unverified", "Invented source validation")
        artifacts = {a["artifact_id"]: a for a in row["artifacts"]}
        for a in artifacts.values():
            require(
                set(a) == {"artifact_id", "field", "role", "start", "end", "text", "content_hash"},
                "Unexpected public artifact field",
            )
            require(
                a["field"] in {"context", "user_query"}
                and row[a["field"]][a["start"] : a["end"]] == a["text"],
                "Invalid source offsets",
            )
            require(digest(a["text"]) == a["content_hash"], "Source hash mismatch")
        for r in row["records"]:
            require(
                set(r)
                == {
                    "record_id",
                    "record_kind",
                    "text",
                    "content_hash",
                    "source_role",
                    "construction_source_spans",
                    "semantic_attribution_status",
                },
                "Unexpected public memory field",
            )
            require(digest(r["text"]) == r["content_hash"], "Memory hash mismatch")
            require(r["semantic_attribution_status"] == "unverified", "Invented attribution review")
            for s in r["construction_source_spans"]:
                require(
                    set(s) == {"artifact_id", "start", "end", "quote"}, "Extra parent-span fields"
                )
                require(
                    artifacts[s["artifact_id"]]["text"][s["start"] : s["end"]] == s["quote"],
                    "Broken construction source span",
                )
        overlay = episode["overlay"][pid]
        require(
            set(overlay)
            == {
                "contributor_id",
                "context_id",
                "batch_id",
                "role",
                "allowed_readers",
                "allowed_operations",
                "write_allowed",
                "policy_version",
                "identity_assumption",
            },
            "Unexpected public policy/source profile",
        )
        require(
            overlay["context_id"] == row["context_id"] and overlay["role"] == "collaborator",
            "Context or role encoding differs",
        )
    require(
        Counter(r["context_id"] for r in pool.values()) == Counter({c: 16 for c in CONTEXTS}),
        "Unbalanced source contexts",
    )
    require(
        set(Counter(m["batch_id"] for m in episode["overlay"].values()).values()) == {4},
        "Wrong submission-batch size",
    )
    require(
        set(
            Counter(
                (m["contributor_id"], m["context_id"]) for m in episode["overlay"].values()
            ).values()
        )
        == {8},
        "Wrong contributor/context size",
    )
    seen, tickets, queries = set(), set(), set()
    for e in episode["events"]:
        if e["event"] == "ingest":
            require(set(e) == {"event", "contribution_id"}, "Extra ingest metadata")
            require(
                e["contribution_id"] in pool and e["contribution_id"] not in seen,
                "Invalid ingestion",
            )
            seen.add(e["contribution_id"])
        elif e["event"] == "audit_request_pending":
            require(
                set(e)
                == {
                    "event",
                    "ticket_id",
                    "contribution_id",
                    "verdict",
                    "status",
                    "completed_verifications",
                },
                "Extra pending audit fields",
            )
            require(
                e["contribution_id"] in seen and e["ticket_id"] not in tickets,
                "Invalid audit target",
            )
            require(
                e["verdict"] is None and e["completed_verifications"] == 0,
                "Invented audit feedback",
            )
            tickets.add(e["ticket_id"])
        elif e["event"] == "original_query":
            require(
                set(e) == {"event", "query_id", "text", "requester", "operation"},
                "Extra query fields",
            )
            require(len(seen) == 32 and e["query_id"] not in queries, "Invalid query order")
            queries.add(e["query_id"])
        else:
            require(False, "Unsupported development event")
    require(len(tickets) == 5 and len(queries) == 27, "Wrong planned verification/query cohort")
    require(set(episode["private"]["case_labels"]) == set(pool), "Incomplete private case labels")
    require(set(episode["private"]["case_targets"]) == queries, "Query/evaluator join mismatch")
    require(
        all(
            r["contribution_id"] not in episode["private"]["reserved_audit_ids"]
            for r in episode["private"]["case_targets"].values()
        ),
        "Audit case included as transfer probe",
    )
    expected = digest([pool, episode["overlay"], episode["events"]])
    require(
        episode["shared_arm_inputs"] == {arm: expected for arm in ARMS},
        "Unmatched arm input digests",
    )
    require(sum(episode["private"]["case_labels"].values()) == 20, "Wrong attack-input count")
    require(
        not episode["status"]["scientific_evaluation_allowed"],
        "Unvalidated data cannot unlock evaluation",
    )


def view(pool: dict, episode: dict, cursor: int, requester="user") -> dict:
    validate_episode(episode, pool)
    require(0 <= cursor <= len(episode["events"]), "Invalid development event cursor")
    visible, pending, query = {}, [], None
    for e in episode["events"][:cursor]:
        query = None
        if e["event"] == "ingest":
            pid = e["contribution_id"]
            policy = episode["overlay"][pid]
            if requester in policy["allowed_readers"]:
                row = copy.deepcopy(pool[pid])
                row["synthetic_source_metadata"] = copy.deepcopy(policy)
                for r in row["records"]:
                    r["synthetic_origin_id"] = (
                        policy["contributor_id"] if r["source_role"] == "external" else None
                    )
                    r["principal_id"] = "user" if r["source_role"] == "principal" else None
                visible[pid] = row
        elif e["event"] == "audit_request_pending" and e["contribution_id"] in visible:
            pending.append(copy.deepcopy(e))
        elif e["event"] == "original_query" and e["requester"] == requester:
            query = {k: e[k] for k in ("query_id", "text", "requester", "operation")}
    result = {
        "visible_contributions": visible,
        "pending_audit_requests": pending,
        "revealed_audit_results": [],
        "current_query": query,
    }
    assert_public(result)
    return result
