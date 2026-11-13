"""Inspect protocol mechanics on invented records, not a defense/benchmark evaluation."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .ledger import EvidenceLedger, _new_file
from .models import Audit, Finding, Provenance, Register, StoredRecord, canonical, check, digest
from .policies import Candidate, Policy

DISCLAIMER = "ARTIFICIAL FIXTURE ONLY: no MPBench annotations, model answers or efficacy results"


def write_example(out: Path) -> dict:
    """Exclusive new destination, one shared five-ticket stream, no external inputs."""
    check(not out.exists(), "Refuse to overwrite an existing example/output directory")
    out.mkdir(parents=True, mode=0o700)
    _new_file(out / ".gitignore", b"*\n!.gitignore\n")
    ledger = EvidenceLedger.create(
        out / "events.jsonl",
        episode_id="artificial-policy-example",
        mode="artificial_fixture",
        audit_limit=5,
        token_limit=0,
        cost_limit_microusd=0,
    )
    specs = (
        ("incident-a", "u1", "email", "b1"),
        ("incident-b", "u1", "email", "b2"),
        ("incident-c", "u1", "file_and_doc", "b1"),
        ("incident-d", "u1", "file_and_doc", "b2"),
        ("same-batch-sibling", "u1", "email", "b1"),
        ("other-batch-sibling", "u1", "email", "b2"),
        ("other-context-sibling", "u1", "file_and_doc", "b1"),
        ("verified-safe-sibling", "u1", "email", "b1"),
        ("unrelated-contributor", "u2", "email", "b1"),
    )
    records = {}
    for root, contributor, context, batch in specs:
        memories = tuple(
            StoredRecord(f"{root}-{kind}", digest([root, kind]), kind, f"{root}-artifact")
            for kind in ("claim", "evidence_chunk")
        )
        records[root] = memories
        ledger.append(
            Register(
                f"ingest-{root}",
                0,
                Provenance(
                    root, context, batch, contributor, "authenticated_external", "innocent-relay"
                ),
                memories,
            )
        )

    decisions, checkpoints = [], []

    def record_stage(stage: str):
        snap = ledger.snapshot()
        snap.save(out / f"snapshot-{stage}.json")
        checkpoints.append(
            {
                "stage": stage,
                "cursor": snap.cursor,
                "revision": snap.revision,
                "usage": asdict(snap.usage),
            }
        )
        for arm in "RCMS":
            policy = Policy(arm)
            for memories in records.values():
                for memory in memories:
                    candidate = Candidate(
                        memory.record_id, memory.content_hash, "fixture-use", "v1", 0.8, True, True
                    )
                    decisions.append(
                        {
                            "stage": stage,
                            "status": "artificial_fixture",
                            **asdict(policy.decide(candidate, snap)),
                        }
                    )

    record_stage("initial")
    schedule = (
        ("verified-safe-sibling", "safe_for_use"),
        ("incident-a", "unsafe"),
        ("incident-b", "unsafe"),
        ("incident-c", "unsafe"),
        ("incident-d", "unsafe"),
    )
    for i, (root, verdict) in enumerate(schedule, 1):
        ledger.append(
            Audit(
                f"fixture-audit-{i}",
                i,
                f"fixture-ticket-{i}",
                root,
                "fixture-use",
                "v1",
                verdict,
                tuple(
                    Finding(
                        m.record_id, m.content_hash, verdict, f"fixture://invented-evidence/{root}"
                    )
                    for m in records[root]
                ),
                True,
                "fixture-author",
                "artificial_fixture",
                f"fixture://invented-review/{i}",
            )
        )
        record_stage(f"after-{i}")
    _new_file(out / "decisions.jsonl", "".join(canonical(row) + "\n" for row in decisions).encode())
    summary = {
        "status": DISCLAIMER,
        "records": sum(map(len, records.values())),
        "independent_roots": len(records),
        "policy_decisions": len(decisions),
        "policies": [{**asdict(Policy(a)), "fingerprint": Policy(a).fingerprint} for a in "RCMS"],
        "checkpoints": checkpoints,
        "final_usage_per_policy": asdict(ledger.snapshot().usage),
        "genuine_human_reviews_created": 0,
        "mpbench_cases_used": 0,
        "model_requests": 0,
        "training_runs": 0,
        "scientific_pilot_generated": False,
    }
    _new_file(out / "summary.json", (canonical(summary) + "\n").encode())
    return summary
