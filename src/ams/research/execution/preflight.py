"""Versioned offline preparation under the user's USD 30 API ceiling."""

from __future__ import annotations

import json
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.planning.costs import estimate
from ams.research.planning.pipeline import review_status
from ams.research.provisional.pipeline import validate as validate_provisional
from ams.research.recovery.offline import sha_file

from .assets import audit_assets
from .session import LIMIT, ExecutionSession, new_json


def check_config(config):
    check(
        config["schema"] == "dynamic-execution-preparation-v1"
        and config["total_api_limit_usd"] == LIMIT
        and config["model"] == "openai/gpt-4o-mini"
        and config["provider"] == "openrouter"
        and config["scientific_execution_enabled"] is False
        and config["automatic_retries"] == 0
        and config["physical_attempts_per_dispatch_id"] == 1
        and config["live_query_stages"] == {"answer": 200, "conflict": 6}
        and config["context_token_bound"] == 128000
        and config["input_usd_per_million_ceiling"] == "0.15"
        and config["output_usd_per_million_ceiling"] == "0.60",
        "Execution preparation cannot raise USD 30 or enable unreviewed science",
    )


def prepare(repo: Path, out: Path, config_path: Path, pricing_path: Path, *, assets=True):
    check(not out.exists(), "Refuse to overwrite previous execution preparation")
    config = json.loads(config_path.read_text())
    pricing = json.loads(pricing_path.read_text())
    check_config(config)
    study = json.loads((repo / "configs/research/dynamic_pilot_v1.json").read_text())
    costs = estimate(study, pricing)
    costs["proposed_cap_usd"] = LIMIT
    costs["cap_activated"] = False
    costs["user_total_api_ceiling_usd"] = LIMIT
    for scope in costs["scopes"].values():
        for scenario in scope.values():
            from decimal import Decimal

            scenario["proposed_cap_covers_this_scenario"] = Decimal(
                scenario["with_headroom_usd"]
            ) <= Decimal(LIMIT)
    prepared = repo / "research_data/mpbench_provisional_v1_20261029"
    recovered = repo / "research_data/mpbench_recovery_v1_20261029"
    provisional = validate_provisional(prepared)
    coverage, review_inputs = review_status(prepared, prepared / "reviewers")
    before = {
        str(p.resolve()): sha_file(p)
        for p in (
            config_path,
            pricing_path,
            prepared / "provisional_manifest.json",
            recovered / "recovery_manifest.json",
            repo / "reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md",
        )
    }
    # Protect existing output bytes without replaying recovery or annotation.
    for root, manifest_name in (
        (prepared, "provisional_manifest.json"),
        (recovered, "recovery_manifest.json"),
    ):
        for name, checksum in json.loads((root / manifest_name).read_text())["files"].items():
            path = root / name
            check(sha_file(path) == checksum, "Previous preparation/recovery output changed")
            before[str(path.resolve())] = checksum
    if assets:
        cache = repo / "reports/safemem_full_mpbench/cache/responses.sqlite"
        before[str(cache)] = sha_file(cache)
        asset_report, catalog, missing = audit_assets(repo, prepared, recovered, [cache])
    else:
        asset_report, catalog, missing = {"not_checked": True}, {}, []
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    private = out / "private"
    private.mkdir(mode=0o700)
    new_json(private / "candidate_query_catalog.json", catalog)
    new_json(private / "missing_cache_requests.json", missing)
    new_json(out / "asset_availability.json", asset_report)
    new_json(out / "settings.json", config)
    new_json(out / "pricing_observation.json", pricing)
    new_json(out / "cost_estimate.json", costs)
    new_json(out / "review_coverage.json", coverage)
    # One allowance for the entire authorized package, including revised plans.
    # A new preparation/report directory must NOT create another USD 30 budget.
    session_directory = repo / "research_data/dynamic_execution_prep_v1_20261031/session"
    session = (
        ExecutionSession(session_directory)
        if session_directory.exists()
        else ExecutionSession.create(session_directory, plan_hash=digest(config))
    )
    check(session.config["plan_hash"] == digest(config), "Shared allowance belongs to another plan")
    try:
        session_summary = session.summary()
    finally:
        session.close()
    blockers = [
        "human safety/provenance review and benign-QA validation remain pending",
        "final validated Z-balanced source groups and fixed audit/probe cohorts remain pending",
        "real native stores, trusted bindings and exact frozen write catalogs remain required",
        "missing shared classifier/query embeddings require one frozen catalog; no arm fallback",
        "actual answer/conflict prompts and native token envelopes require those stores",
        "scientific-manifest promotion and fresh provider/account preflight remain required",
    ]
    report = {
        "status": "offline_execution_preparation_complete_scientific_pilot_blocked",
        "date": config["date"],
        "user_api_limit_usd": LIMIT,
        "actual_paid_cost_usd": "0",
        "live_api_calls": 0,
        "shared_session": session_summary,
        "shared_session_directory": str(session_directory.resolve()),
        "previous_provisional_validation": provisional,
        "independently_verified_bundles": coverage["independently_verified_bundles"],
        "human_validated_qa": coverage["human_validated_qa"],
        "scientific_pilot_ready": False,
        "paid_dispatch_enabled": False,
        "human_validation_can_remain_deferred_for_engineering": True,
        "blockers": blockers,
    }
    new_json(out / "preparation_report.json", report)
    for name, checksum in before.items():
        check(sha_file(Path(name)) == checksum, f"Input changed during offline preparation: {name}")
    deps = {**before, **review_inputs}
    for folder in ("src/ams/research", "src/ams/core", "src/ams/memory", "src/ams/llm"):
        deps.update({str(p.resolve()): sha_file(p) for p in (repo / folder).rglob("*.py")})
    deps.update({str(p.resolve()): sha_file(p) for p in (repo / "prompts").rglob("*.txt")})
    deps[str((repo / "scripts/prepare_dynamic_execution.py").resolve())] = sha_file(
        repo / "scripts/prepare_dynamic_execution.py"
    )
    payloads = {
        str(p.relative_to(out)): sha_file(p)
        for p in out.rglob("*")
        if p.is_file() and "session" not in p.relative_to(out).parts
    }
    manifest = {
        "schema": "dynamic-execution-engineering-freeze-v1",
        "files": payloads,
        "dependencies": deps,
        "session_id": session_summary["session_id"],
        "session_directory": str(session_directory.resolve()),
        "user_api_limit_usd": LIMIT,
        "execution_enabled": False,
    }
    new_json(out / "execution_manifest.json", {**manifest, "manifest_hash": digest(manifest)})
    return report


def verify(out: Path):
    body = json.loads((out / "execution_manifest.json").read_text())
    checksum = body.pop("manifest_hash")
    check(
        digest(body) == checksum
        and body["user_api_limit_usd"] == LIMIT
        and body["execution_enabled"] is False,
        "Execution freeze changed or increased budget",
    )
    for name, expected in body["files"].items():
        p = out / name
        check(
            p.resolve().is_relative_to(out.resolve()) and sha_file(p) == expected,
            "Execution payload changed",
        )
    for name, expected in body["dependencies"].items():
        p = Path(name)
        check(
            not p.exists() if expected is None else p.is_file() and sha_file(p) == expected,
            "Execution source/review dependency changed; prepare a new version",
        )
    with ExecutionSession(Path(body["session_directory"])) as session:
        check(session.config["session_id"] == body["session_id"], "Shared session changed")
        snapshot = session.summary()
    return {
        "status": "passed",
        "payloads_checked": len(body["files"]),
        "dependencies_checked": len(body["dependencies"]),
        "shared_session": snapshot,
        "scientific_pilot_ready": False,
        "paid_dispatch_enabled": False,
    }
