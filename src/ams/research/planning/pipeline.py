"""Read-only preparation checks and new versioned planning bundles; no launcher."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from ams.core.prompts import PromptLibrary
from ams.research.dynamic.models import LedgerError, canonical, check, digest
from ams.research.phase1_common import RAW_HASHES, read_jsonl
from ams.research.provisional.pipeline import validate as validate_provisional
from ams.research.recovery.annotation import review_coverage
from ams.research.recovery.offline import sha_file

from .costs import estimate
from .study import PROTOCOL_HASH, inventory, validate_config


def new_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")


def review_status(prepared: Path, reviews: Path) -> tuple[dict, dict]:
    """Recompute genuine review coverage from raw current forms, not a ready boolean."""
    inputs = {}

    def read(path):
        if not path.exists():
            inputs[str(path.resolve())] = None
            return []
        inputs[str(path.resolve())] = sha_file(path)
        return read_jsonl(path)

    packets = read(prepared / "private/review_packets.jsonl")
    questions = read(prepared / "private/question_drafts.jsonl")
    a = read(reviews / "reviewer_1/reviews_a.jsonl")
    b = read(reviews / "reviewer_2/reviews_b.jsonl")
    adjudications = read(reviews / "reviewer_3/adjudications.jsonl")
    qa = [r for n in (1, 2, 3) for r in read(reviews / f"reviewer_{n}/qa_reviews.jsonl")]
    result = review_coverage(packets, a, b, adjudications, questions, qa)
    # Individual labels and answer references are NOT copied into the planning bundle.
    status = {
        key: result[key]
        for key in (
            "status",
            "verified_bundle_labels",
            "independently_verified_bundles",
            "independently_verified_record_use_labels",
        )
    }
    status.update(
        {
            "human_validated_qa": len(result["human_validated_qa_candidate_ids"]),
            "safe_source_validated_qa": len(result["safe_source_and_qa_validated_candidate_ids"]),
            "missing_two_safety_reviews": result["safety_review"]["missing_two_reviews"],
            "reviewer_independence_is_structurally_checked": True,
            "human_identity_authentication_claimed": False,
        }
    )
    return status, inputs


def assess_readiness(status: dict) -> dict:
    """Counts help triage; they cannot establish eligible grouped cohorts on their own."""
    labels = status["verified_bundle_labels"]
    blockers = []
    if labels.get("unsafe", 0) < 320 or labels.get("safe_for_use", 0) < 320:
        blockers.append("independent_safety_and_provenance_labels_in_required_strata")
    if status["safe_source_validated_qa"] < 320:
        blockers.append("independently_validated_safe_external_source_questions")
    blockers.extend(
        [
            "validated_Z_balanced_group_manifests_not_created_or_frozen",
            "exact_audit_and_probe_ID_cohorts_and_denominators_not_frozen",
            "native_graph_bindings_and_exact_response_catalogs_not_provisioned_for_real_cases",
            "input_prompt_token_envelopes_and_local_embedding_coverage_not_verified",
            "live_transport_response_capture_and_budget_guard_not_integrated_with_offline_runner",
            "fresh_rate_account_guard_and_cost_disclosure_preflight_required_before_paid_dispatch",
        ]
    )
    return {
        "engineering_settings_frozen": True,
        "scientific_dataset_frozen": False,
        "scientific_pilot_ready": False,
        "paid_dispatch_enabled": False,
        "blockers": blockers,
        "provisional_groups_are_not_validated_pilot": True,
        "review_counts_alone_unlock_execution": False,
        "human_validation_can_remain_deferred_during_engineering": True,
    }


def dependencies(config_path: Path, pricing_path: Path) -> dict:
    repo = Path(__file__).resolve().parents[4]
    files = set()
    for folder in ("src/ams/research", "src/ams/memory", "src/ams/core"):
        files.update((repo / folder).rglob("*.py"))
    files.update(
        [
            config_path,
            pricing_path,
            repo / "scripts/prepare_dynamic_pilot.py",
            repo / "src/ams/eval/use_type.py",
            repo / "src/ams/eval/judge.py",
            repo / "src/ams/eval/lifecycle.py",
            repo / "src/ams/llm/budget.py",
            repo / "src/ams/llm/pricing.py",
            repo / "src/ams/llm/providers/openai_client.py",
            repo / "reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md",
            repo / "configs/openrouter_mpbench_safemem.yaml",
        ]
    )
    files.update((repo / "prompts").rglob("*.txt"))
    files.update(repo / "data/mpbench" / name for name in RAW_HASHES)
    return {str(p.resolve()): sha_file(p) for p in sorted(files)}


def prepare(
    prepared: Path, config_path: Path, pricing_path: Path, out: Path, *, reviews: Path | None = None
) -> dict:
    check(not out.exists(), "Refuse to overwrite an existing planning version")
    config, pricing = [json.loads(p.read_text()) for p in (config_path, pricing_path)]
    validate_config(config)
    repo = Path(__file__).resolve().parents[4]
    check(
        sha_file(repo / "reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md") == PROTOCOL_HASH,
        "Protocol changed; declare an amendment before planning",
    )
    for filename, expected in RAW_HASHES.items():
        check(
            sha_file(repo / "data/mpbench" / filename) == expected, "Official MPBench bytes changed"
        )
    base = yaml.safe_load((repo / "configs/openrouter_mpbench_safemem.yaml").read_text())
    for key in (
        "mode",
        "hops",
        "source_cap",
        "endorsement",
        "detect_conflicts",
        "external_evidence",
    ):
        check(
            base["typed"][key] == config["retrieval"][key],
            "Original settings differ from planned method",
        )
    check(
        base["typed"]["evidence_slots"] == config["retrieval"]["m"]
        and base["retrieve_k"] == config["retrieval"]["k"],
        "Original retrieval slot limits changed",
    )
    check(
        all(
            base["models"][r] == "openrouter:" + config["chat_model"]
            for r in ("memory", "agent", "judge")
        ),
        "Original model roles differ from pricing/frozen plan",
    )
    provisional = validate_provisional(prepared)
    status, review_inputs = review_status(prepared, reviews or prepared / "reviewers")
    deps = dependencies(config_path, pricing_path)
    source_manifest = prepared / "provisional_manifest.json"
    pm = json.loads(source_manifest.read_text())
    protected = {
        **deps,
        **review_inputs,
        str(source_manifest.resolve()): sha_file(source_manifest),
        **{str((prepared / name).resolve()): h for name, h in pm["files"].items()},
    }
    readiness = assess_readiness(status)
    costs, design = estimate(config, pricing), inventory(config)
    source_prompts = PromptLibrary()
    prompt_hashes = {
        name: source_prompts.get(name, version).sha256
        for name, version in config["prompts"].items()
    }
    report = {
        "schema": config["schema"],
        "status": "engineering_freeze_only_not_scientific_lock",
        "protocol_sha256": PROTOCOL_HASH,
        "settings_hash": digest(config),
        "pricing_hash": digest(pricing),
        "review_coverage": status,
        "existing_provisional_validation": provisional,
        "readiness": readiness,
        "grid_slot_count": len(design["grid_slots"]),
        "model_calls_performed": 0,
        "paid_cost_usd": 0,
        "user_api_authorization": (
            "Session allows needed API use after advance estimate; none dispatched"
        ),
        "spending_cap_activated": False,
        "human_annotation_labor_cost": "unknown, separate from API estimate",
    }
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    for name, value in {
        "settings.json": config,
        "pricing_observation.json": pricing,
        "study_inventory.json": design,
        "cost_estimate.json": costs,
        "readiness.json": readiness,
        "preparation_report.json": report,
        "prompt_fingerprints.json": prompt_hashes,
    }.items():
        new_json(out / name, value)
    _write_cost_report(out / "COST_ESTIMATE.md", costs)
    for name, checksum in protected.items():
        check(
            (not Path(name).exists()) if checksum is None else sha_file(Path(name)) == checksum,
            f"Input changed while planning: {name}",
        )
    payload = {str(p.relative_to(out)): sha_file(p) for p in sorted(out.rglob("*")) if p.is_file()}
    manifest = {
        "schema": "dynamic-engineering-freeze-manifest-v1",
        "files": payload,
        "input_sha256": protected,
        "scientific_freeze_created": False,
        "execution_enabled": False,
    }
    new_json(out / "engineering_manifest.json", {**manifest, "manifest_hash": digest(manifest)})
    return report


def verify(out: Path) -> dict:
    manifest = json.loads((out / "engineering_manifest.json").read_text())
    checksum = manifest.pop("manifest_hash")
    check(checksum == digest(manifest), "Engineering manifest checksum mismatch")
    for name, expected in manifest["files"].items():
        path = out / name
        check(path.resolve().is_relative_to(out.resolve()), "Planning path escapes bundle")
        check(sha_file(path) == expected, f"Planning payload modified: {name}")
    for path, expected in manifest["input_sha256"].items():
        check(
            (not Path(path).exists())
            if expected is None
            else Path(path).is_file() and sha_file(Path(path)) == expected,
            f"Frozen dependency/review changed; prepare a new version: {path}",
        )
    check(
        manifest["scientific_freeze_created"] is False and manifest["execution_enabled"] is False,
        "Engineering bundle cannot claim scientific or execution readiness",
    )
    report = json.loads((out / "preparation_report.json").read_text())
    check(not report["readiness"]["scientific_pilot_ready"], "Unsupported scientific lock")
    return {
        "status": "passed",
        "payload_files_checked": len(manifest["files"]),
        "dependencies_checked": len(manifest["input_sha256"]),
        "scientific_pilot_ready": False,
        "paid_dispatch_enabled": False,
    }


def require_scientific_freeze(out: Path) -> None:
    verify(out)
    readiness = json.loads((out / "readiness.json").read_text())
    raise LedgerError("Scientific freeze unavailable: " + "; ".join(readiness["blockers"]))


def _write_cost_report(path: Path, costs: dict):
    lines = [
        "# Conditional API-cost estimate",
        "",
        "Planning only. No paid calls are made.",
        "",
        "Prices: USD "
        + costs["input_usd_per_million"]
        + "/M input and "
        + costs["output_usd_per_million"]
        + "/M output, checked "
        + costs["pricing_checked_on"]
        + ". "
        + "[Official model page]("
        + costs["pricing_source"]
        + ").",
        "",
        "Input lengths and conflict frequency are assumptions, not measured token usage. "
        "Outputs use frozen completion ceilings. Provider-cache discounts are not assumed.",
        "",
        "| Scope | Working range incl. 20% retry allowance | Stress: two attempts + 25% headroom |",
        "| --- | ---: | ---: |",
    ]
    for name, scenarios in costs["scopes"].items():
        lines.append(
            f"| {name} | ${scenarios['working_low']['with_retries_usd']}–"
            f"${scenarios['working_high']['with_retries_usd']} | "
            f"${scenarios['stress']['with_headroom_usd']} |"
        )
    lines.extend(
        [
            "",
            "Proposed combined stop cap: **$" + costs["proposed_cap_usd"] + "**. "
            "It is not activated and is not a promise that every worst-case request will fit.",
            "",
            "The stress case uses six conflict calls per k=4 retrieval. The full 128,000-token "
            "context reservation for every possible attempt is a separate, much larger bound, "
            "listed in the JSON. A future run must stop at the cap rather than assume completion.",
            "",
            "Exact cohort IDs, token lengths, cache hits and human-review costs are unresolved. "
            "No fresh extraction, real verifier, tuning grid or optional baseline is included. "
            "Missing frozen memory replay aborts; replacing records requires new versions/review.",
            "",
            "Classifier outputs are frozen once per exact query; no-memory and write controls "
            "are shared only for identical conditions. Memory-answer and judge caching is not "
            "discounted. Logical verification tickets remain equal even with shared oracle lookup.",
            "",
            "QA scoring uses validated aliases and blinded human adjudication; their labor and "
            "dataset annotation labor are unknown costs. Taxes, credit purchase fees and local "
            "compute are excluded. Refresh pricing and inspect exact prompts before paid use.",
            "",
        ]
    )
    with path.open("x") as stream:
        stream.write("\n".join(lines))
