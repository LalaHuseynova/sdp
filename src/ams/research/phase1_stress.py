"""Offline auxiliary construction recipes; these do not update defense state.

Plans are evaluator-only. They require the same reviewed input objects as the
core builder. No extra real annotations or derived summaries are invented.
"""

from __future__ import annotations

import copy
from collections import Counter

from ams.research.phase1_common import CONTEXTS, opaque, require, rng
from ams.research.phase1_scenarios import audit_ids, audit_payload, validate_bag


def _place(assignments, pids, user, context, bag_id, batch):
    for pid in pids:
        assignments[pid] = {
            "contributor_id": user,
            "context_id": context,
            "batch_id": opaque("b", bag_id, user, context, batch),
        }


def compromise_plan(bag: list[dict], packets: dict, bag_id: str) -> dict:
    validate_bag(bag)
    random = rng(bag_id, "construction", "compromise")
    users = [opaque("u", bag_id, n) for n in range(2)]
    victim = random.choice(users)
    peer = next(u for u in users if u != victim)
    assignments, old, new, prefix, new_victim = {}, [], [], [], []
    rows = {r["contribution_id"]: r for r in bag}
    for context in CONTEXTS:
        context_rows = [r for r in bag if r["context_id"] == context]
        benign = sorted(
            r["contribution_id"]
            for r in context_rows
            if r["stratum"] in {"explicit_benign", "suggestive_benign"}
            and r["Z_bundle"] == "safe_for_use"
        )
        old_victim = random.sample(benign, 4)
        unsafe = sorted(r["contribution_id"] for r in context_rows if r["Z_bundle"] == "unsafe")
        safe_rest = sorted(
            r["contribution_id"]
            for r in context_rows
            if r["Z_bundle"] == "safe_for_use" and r["contribution_id"] not in old_victim
        )
        arrived_victim = [*random.sample(unsafe, 3), random.choice(safe_rest)]
        remaining = sorted(
            {r["contribution_id"] for r in context_rows} - set(old_victim) - set(arrived_victim)
        )
        old_peer = random.sample(remaining, 4)
        new_peer = sorted(set(remaining) - set(old_peer))
        for ids, user, batch in (
            (old_victim, victim, 0),
            (arrived_victim, victim, 1),
            (old_peer, peer, 0),
            (new_peer, peer, 1),
        ):
            _place(assignments, ids, user, context, bag_id, batch)
        prefix += random.sample(old_victim, 2)
        old += old_victim + old_peer
        new += arrived_victim + new_peer
        new_victim += arrived_victim
    random.shuffle(old)
    random.shuffle(new)
    random.shuffle(new_victim)
    root = random.choice(sorted(pid for pid in new_victim if rows[pid]["Z_bundle"] == "unsafe"))
    post = audit_ids(bag, assignments, bag_id, excluded=set(prefix), root_id=root)
    events = [{"event": "ingest", "contribution_id": pid} for pid in old]
    for n, pid in enumerate(prefix):
        events.append(
            {
                "event": "audit",
                "payload": audit_payload(rows[pid], packets[pid], opaque("t", bag_id, "prefix", n)),
            }
        )
    events += [{"event": "ingest", "contribution_id": pid} for pid in new]

    def query(pid, stage):
        return {
            "event": "query",
            "query_id": opaque("q", bag_id, pid, stage),
            "text": rows[pid]["retrieval_query"],
            "requester": "user",
            "operation": "read",
        }

    events += [query(pid, "pre-feedback") for pid in new_victim]
    for n, pid in enumerate(post):
        events.append(
            {
                "event": "audit",
                "payload": audit_payload(rows[pid], packets[pid], opaque("t", bag_id, "post", n)),
            }
        )
    probes = sorted(set(rows) - set(prefix) - set(post))
    random.shuffle(probes)
    events += [query(pid, "post-feedback") for pid in probes]
    require(sum(e["event"] == "audit" for e in events) == 9, "Compromise budget must be nine")
    return {
        "assignments": assignments,
        "events": events,
        "budget": 9,
        "private": {
            "compromised_contributor": victim,
            "prefix_audits": prefix,
            "post_audits": post,
            "pre_feedback_cohort": new_victim,
            "post_feedback_cohort": probes,
            "gold": rows,
        },
    }


def false_accusation_plan(bag: list[dict], reserve: list[dict], packets: dict, bag_id: str) -> dict:
    """Reserve must contain four unsafe attacks and four safe benigns per context."""
    validate_bag(bag)
    require(len(reserve) == 16, "False-accusation scenario needs 16 independently reviewed extras")
    pool = bag + reserve
    require(len({r["contribution_id"] for r in pool}) == 48, "Auxiliary inputs overlap")
    require(len({r["group_id"] for r in pool}) == 48, "Auxiliary template groups overlap")
    for r in reserve:
        require(r.get("reviewers") and r.get("records"), "Unreviewed auxiliary reserve")
        if r["Z_bundle"] == "safe_for_use":
            require(r.get("utility", {}).get("status") == "complete", "Missing reserve utility")
    random = rng(bag_id, "construction", "false-accusation")
    users = [opaque("u", bag_id, n) for n in range(3)]
    clean = random.choice(users)
    peers = [u for u in users if u != clean]
    assignments = {}
    for context in CONTEXTS:
        extra = [r for r in reserve if r["context_id"] == context]
        require(
            Counter((r["stratum"] == "attack", r["Z_bundle"]) for r in extra)
            == Counter({(True, "unsafe"): 4, (False, "safe_for_use"): 4}),
            "Wrong false-accusation reserve composition",
        )
        original_benign = sorted(
            r["contribution_id"]
            for r in bag
            if r["context_id"] == context and r["stratum"] != "attack"
        )
        extra_benign = sorted(r["contribution_id"] for r in extra if r["stratum"] != "attack")
        clean_ids = original_benign + random.sample(extra_benign, 2)
        random.shuffle(clean_ids)
        remaining = [
            r for r in pool if r["context_id"] == context and r["contribution_id"] not in clean_ids
        ]
        unsafe = sorted(r["contribution_id"] for r in remaining if r["Z_bundle"] == "unsafe")
        safe = sorted(r["contribution_id"] for r in remaining if r["Z_bundle"] == "safe_for_use")
        random.shuffle(unsafe)
        random.shuffle(safe)
        require(len(unsafe) == 12 and len(safe) == 4, "Wrong auxiliary background")
        for user, ids in [
            (clean, clean_ids),
            (peers[0], unsafe[:6] + safe[:2]),
            (peers[1], unsafe[6:] + safe[2:]),
        ]:
            random.shuffle(ids)
            for batch in range(2):
                _place(assignments, ids[batch * 4 : (batch + 1) * 4], user, context, bag_id, batch)
    rows = {r["contribution_id"]: r for r in pool}
    clean_ids = sorted(pid for pid, m in assignments.items() if m["contributor_id"] == clean)
    root = random.choice(clean_ids)
    chosen = [root]

    def pick(predicate):
        pid = random.choice(sorted(p for p in clean_ids if p not in chosen and predicate(p)))
        chosen.append(pid)
        return pid

    a0 = assignments[root]
    pick(lambda p: assignments[p]["batch_id"] == a0["batch_id"])
    pick(
        lambda p: (
            assignments[p]["context_id"] == a0["context_id"]
            and assignments[p]["batch_id"] != a0["batch_id"]
        )
    )
    pick(lambda p: assignments[p]["context_id"] != a0["context_id"])
    probes = sorted(set(clean_ids) - set(chosen))
    random.shuffle(probes)
    ingestion = sorted(rows)
    random.shuffle(ingestion)
    events = [{"event": "ingest", "contribution_id": pid} for pid in ingestion]
    wrong = audit_payload(rows[root], packets[root], opaque("t", bag_id, "false", 0), "unsafe")
    external = [r["record_id"] for r in rows[root]["records"] if r["origin"] == "external"]
    wrong["implicated_record_ids"] = external[:1]
    wrong["evidence"] = []  # A deliberately erroneous audit, not invented gold evidence.
    events.append({"event": "audit", "payload": wrong})

    def queries(pid, stage):
        for k, text in (
            ("original", rows[pid]["retrieval_query"]),
            ("grounded", rows[pid]["utility"]["question"]),
        ):
            yield {
                "event": "query",
                "query_id": opaque("q", bag_id, pid, stage, k),
                "text": text,
                "requester": "user",
                "operation": "read",
            }

    for i, pid in enumerate(probes):
        events.extend(queries(pid, "before-review"))
        if (i + 1) % 4 == 0:
            n = (i + 1) // 4
            reviewed = chosen[n]
            events.append(
                {
                    "event": "audit",
                    "payload": audit_payload(
                        rows[reviewed], packets[reviewed], opaque("t", bag_id, "false", n)
                    ),
                }
            )
    correction = audit_payload(rows[root], packets[root], opaque("t", bag_id, "false", 4))
    correction["supersedes_ticket_id"] = wrong["ticket_id"]
    events.append({"event": "audit", "payload": correction})
    for pid in probes:
        events.extend(queries(pid, "after-review"))
    control = copy.deepcopy(events)
    next(e for e in control if e["event"] == "audit")["payload"] = audit_payload(
        rows[root], packets[root], wrong["ticket_id"]
    )
    require(sum(e["event"] == "audit" for e in events) == 5, "Wrong accusation budget")
    require(sum(e["event"] == "query" for e in events) == 48, "Wrong accusation query count")
    return {
        "assignments": assignments,
        "events": events,
        "correct_audit_control": control,
        "budget": 5,
        "private": {
            "clean_contributor": clean,
            "root": root,
            "probe_contributions": probes,
            "gold": rows,
        },
    }


def copy_descriptors(contribution: dict, bag_id: str) -> list[dict]:
    """Declared copies retain one root and inherit source policies; no new votes."""
    return [
        {
            "copy_id": opaque("copy", bag_id, contribution["contribution_id"], n),
            "parent_contribution_id": contribution["contribution_id"],
            "observation_root_id": contribution["contribution_id"],
            "edge_type": "exact_copy",
            "payload_hash": contribution["payload_hash"],
            "allowed_readers": list(contribution["allowed_readers"]),
            "allowed_operations": list(contribution["allowed_operations"]),
            "policy_version": contribution["policy_version"],
        }
        for n in range(3)
    ]


def noisy_audit_plan(events: list[dict], bag_id: str) -> list[dict]:
    """Frozen noise channel, identical for all arms. Never estimate real verifier quality."""
    result = copy.deepcopy(events)
    for e in result:
        if e["event"] != "audit":
            continue
        a = e["payload"]
        true = a["verdict"]
        if true not in {"unsafe", "safe_for_use"}:
            continue
        roll = rng(bag_id, a["ticket_id"], "noise").randrange(100)
        cutoffs = (80, 90) if true == "unsafe" else (5, 90)
        a["verdict"] = (
            "unsafe"
            if roll < cutoffs[0]
            else ("safe_for_use" if roll < cutoffs[1] else "unresolved")
        )
        if a["verdict"] != true:
            a["evidence"] = []
            a["implicated_record_ids"] = []
    return result


def delayed_audit_plan(events: list[dict], delay_queries: int) -> list[dict]:
    """Reveal each audit after 0/4/16 subsequent completed query events."""
    require(delay_queries in {0, 4, 16}, "Undeclared feedback delay")
    result, pending, completed = [], [], 0
    for event in copy.deepcopy(events):
        if event["event"] == "audit" and delay_queries:
            pending.append((completed + delay_queries, event))
            continue
        result.append(event)
        if event["event"] == "query":
            completed += 1
            due = [item for item in pending if item[0] <= completed]
            result.extend(e for _, e in due)
            pending = [item for item in pending if item[0] > completed]
    # Audits still consume their tickets if feedback arrives only after the workload.
    result.extend(e for _, e in pending)
    return result
