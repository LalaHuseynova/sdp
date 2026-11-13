"""Allowlisted blinded review requests and a bounded development-only plan."""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import check, digest
from ams.research.execution.session import MODEL, new_json, prompt_measurement
from ams.research.phase1_common import read_jsonl
from ams.research.recovery.annotation import assert_blinded
from ams.research.recovery.offline import sha_file
from ams.research.sequential.clients import request_from

from .prompts import SYSTEM_PROMPT

SCHEMA = "automated-review-development-v1"
OUTPUT_LIMIT = 12288
STAGE = "annotation_review"
SESSION = Path("research_data/dynamic_execution_prep_v1_20261031/session")


def blinded_input(packet, candidates):
    artifacts = [{k: a[k] for k in ("artifact_id", "role", "text")} for a in packet["artifacts"]]
    records = [{k: r[k] for k in ("record_id", "record_kind", "text")} for r in packet["records"]]
    questions = [
        {
            k: q[k]
            for k in (
                "candidate_id",
                "question",
                "answers",
                "support_record_id",
                "support_artifact_id",
                "quote",
            )
        }
        for q in candidates
    ]
    body = {
        "task": packet["task"],
        "intended_use": packet["intended_use"],
        "context_id": packet["context_id"],
        "artifacts": artifacts,
        "records": records,
        "questions": questions,
    }
    assert_blinded(body)
    return body


def request_for(body):
    return ChatRequest(
        (Message("system", SYSTEM_PROMPT), Message("user", json.dumps(body, ensure_ascii=False))),
        MODEL,
        temperature=0.0,
        max_tokens=OUTPUT_LIMIT,
    )


def prepare(repo: Path, prepared: Path, out: Path):
    check(not out.exists(), "Review version exists; do not overwrite reviews or responses")
    bags = json.loads((prepared / "private/group_selections.json").read_text())
    # A declared first development group: never use new-method/attack outcomes.
    bag = next(b for b in bags if b["bag_id"] == "D00")
    ids = set(bag["source_ids"])
    check(
        len(ids) == 32 and bag["split_intent"] == "development",
        "Only first development bag permitted",
    )
    packets = {
        r["contribution_id"]: r
        for r in read_jsonl(prepared / "private/review_packets.jsonl")
        if r["contribution_id"] in ids
    }
    candidates = read_jsonl(prepared / "private/question_drafts.jsonl")
    check(set(packets) == ids, "Incomplete development review packets")
    session_config = json.loads((repo / SESSION / "session.json").read_text())
    check(session_config["limit_usd"] == "30.00", "Existing shared USD 30 allowance required")
    jobs = []
    for pid in sorted(ids):
        packet = packets[pid]
        qs = [q for q in candidates if q["contribution_id"] == pid]
        body = blinded_input(packet, qs)
        request = request_for(body)
        measurement = prompt_measurement(request)
        check(
            measurement["input_token_proxy"] + OUTPUT_LIMIT < 128000,
            "Review packet too large; no truncation",
        )
        key = request.cache_key("openrouter")
        jobs.append(
            {
                "call_id": digest([SCHEMA, key]),
                "request_key": key,
                "request": asdict(request),
                "contribution_id": pid,
                "use_id": packet["use_id"],
                "packet_hash": digest(packet),
                "record_versions": {r["record_id"]: r["content_hash"] for r in packet["records"]},
                "candidate_versions": {q["candidate_id"]: digest(q) for q in qs},
                "measurement": measurement,
            }
        )
    worst = (
        Decimal(len(jobs))
        * (Decimal(128000) * Decimal(".15") + Decimal(OUTPUT_LIMIT) * Decimal(".60"))
        / 1_000_000
    )
    check(worst <= 1, "Development review reservation exceeds USD 1")
    config = {
        "schema": SCHEMA,
        "model": MODEL,
        "stage": STAGE,
        "session_id": session_config["session_id"],
        "session_directory": str((repo / SESSION).resolve()),
        "development_bag": "D00",
        "requests": len(jobs),
        "single_pass": True,
        "physical_attempts_per_id": 1,
        "output_tokens": OUTPUT_LIMIT,
        "human_verified": False,
        "scientific_pilot_enabled": False,
        "total_project_ceiling_usd": "30.00",
        "review_task_reservation_ceiling_usd": str(worst),
        "working_estimate_usd": ["0.10", "0.25"],
        "input_price_ceiling_per_million": "0.15",
        "output_price_ceiling_per_million": "0.60",
        "price_checked_on": "2026-10-31",
        "price_source": "https://openrouter.ai/openai/gpt-4o-mini/overview",
        "basis": "conditional API usage estimate; native input/output counts not yet measured",
    }
    dependencies = {str(p.resolve()): sha_file(p) for p in Path(__file__).parent.glob("*.py")}
    for p in (
        prepared / "private/review_packets.jsonl",
        prepared / "private/question_drafts.jsonl",
        prepared / "private/group_selections.json",
        repo / "scripts/review_mpbench_llm.py",
        repo / "src/ams/research/execution/session.py",
        repo / "src/ams/llm/budget.py",
        repo / "src/ams/llm/providers/openai_client.py",
        repo / "src/ams/llm/openrouter_budget.py",
    ):
        dependencies[str(p.resolve())] = sha_file(p)
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    new_json(out / "settings.json", config)
    new_json(out / "jobs.json", jobs)
    lock = {
        "schema": SCHEMA,
        "dependencies": dependencies,
        "files": {n: sha_file(out / n) for n in ("settings.json", "jobs.json")},
    }
    new_json(out / "review_manifest.json", {**lock, "manifest_hash": digest(lock)})
    return {
        **config,
        "memory_records": sum(len(j["record_versions"]) for j in jobs),
        "question_candidates": sum(len(j["candidate_versions"]) for j in jobs),
    }


def verify(out: Path):
    lock = json.loads((out / "review_manifest.json").read_text())
    checksum = lock.pop("manifest_hash")
    check(digest(lock) == checksum and lock["schema"] == SCHEMA, "Review manifest changed")
    for name, checksum in lock["files"].items():
        p = out / name
        check(
            p.resolve().is_relative_to(out.resolve()) and sha_file(p) == checksum,
            "Review payload changed",
        )
    for name, checksum in lock["dependencies"].items():
        check(sha_file(Path(name)) == checksum, "Review dependency changed; prepare a new version")
    config = json.loads((out / "settings.json").read_text())
    jobs = json.loads((out / "jobs.json").read_text())
    check(
        config["human_verified"] is False
        and config["scientific_pilot_enabled"] is False
        and config["total_project_ceiling_usd"] == "30.00"
        and len(jobs) == config["requests"] == 32,
        "Unsupported review scope/promotion",
    )
    check(len({j["call_id"] for j in jobs}) == 32, "Repeated review job")
    for j in jobs:
        req = request_from("chat", j["request"])
        check(
            req.cache_key("openrouter") == j["request_key"]
            and req.max_tokens == OUTPUT_LIMIT
            and req.model == MODEL
            and req.temperature == 0
            and req.messages[0].content == SYSTEM_PROMPT,
            "Unfrozen review request",
        )
        assert_blinded(json.loads(req.messages[1].content))
    return config, jobs
