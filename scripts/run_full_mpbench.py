#!/usr/bin/env python
"""Run a frozen full MPBench plan only after explicit paid-execution approval."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import signal
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from ams.core.env import load_env
from ams.core.prompts import PromptLibrary
from ams.core.spans import segment
from ams.data.mpbench import load_mpbench
from ams.llm.openrouter_budget import (
    ProviderBudgetNotVerified,
    credential_fingerprint,
    current_key_budget,
)
from ams.llm.pricing import lookup
from prepare_full_mpbench import ROOT, sha256


def validate_plan(plan: dict) -> None:
    if Path(plan["repository"]).resolve() != ROOT:
        raise ValueError("plan belongs to another repository")
    if plan["dataset"]["counts"] != {
        "ingestions": 6240,
        "attack_ingestions": 3241,
        "attack_reads": 2999,
        "benign_reads": 2997,
    }:
        raise ValueError("plan does not describe the complete audited dataset")
    if len(plan["dataset"]["official_validation"]["verified_files"]) != 2:
        raise ValueError("both official MPBench files must be validated")
    for relative, expected in plan["source_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(
                f"source changed since preparation: {relative}; prepare/review a new plan"
            )
    for row in plan["dataset"]["official_validation"]["verified_files"]:
        if sha256(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("raw dataset changed since preparation")
    for path, expected in plan.get("local_artifact_sha256", {}).items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"local baseline/model artifact changed: {path}")
    for name, expected in plan.get("third_party_revisions", {}).items():
        path = ROOT / "third_party" / name
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        changes = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=path, text=True
        ).splitlines()
        if commit != expected["commit"] or changes != expected["tracked_changes"]:
            raise ValueError(f"third-party baseline checkout changed: {name}")
    for job in plan["jobs"]:
        if sha256(Path(job["config_path"])) != job["config_sha256"]:
            raise ValueError(f"resolved configuration changed: {job['id']}")
        cfg = job["config"]
        import yaml

        if yaml.safe_load(Path(job["config_path"]).read_text()) != cfg:
            raise ValueError("resolved configuration differs from the plan")
        if cfg.get("pool_size") != 6240 or cfg.get("limit") or cfg.get("adaptive"):
            raise ValueError("plan includes reduced pools, limited cases, or transformed attacks")
        if any(
            not cfg["models"][r].startswith("openrouter:") for r in ("memory", "agent", "judge")
        ):
            raise ValueError("all paid chat roles must use OpenRouter")
        if cfg.get("fallbacks") or cfg.get("fallback_provider"):
            raise ValueError("model/provider fallbacks must not silently change the experiment")
        if "--require-full" not in job["command"] or "--limit" in job["command"]:
            raise ValueError("job command does not enforce the complete dataset")


class LedgerBudget:
    """Monitor original usage logs; this is a billing estimate, not a server cap."""

    def __init__(self, root: Path):
        self.root = root
        self.offsets: dict[Path, int] = {}
        self.cost = 0.0
        self.calls = 0

    def poll(self) -> None:
        for path in self.root.rglob("usage.jsonl"):
            with path.open() as fh:
                fh.seek(self.offsets.get(path, 0))
                while True:
                    start = fh.tell()
                    line = fh.readline()
                    if not line:
                        break
                    if not line.endswith("\n"):
                        fh.seek(start)
                        break
                    row = json.loads(line)
                    if row["provider"] not in ("local", "echo") and not row["cached"]:
                        if lookup(row["provider"], row["model"]) is None:
                            raise RuntimeError(
                                "unpriced provider response: stop and review the cost estimate"
                            )
                        self.cost += row["cost_usd"]
                        self.calls += 1
                self.offsets[path] = fh.tell()


def billing_preflight(plan: dict, cases: list, guard, root: Path) -> dict:
    """Warm the first original retention request, verifying live accounting before bulk work."""
    from ams.llm import ChatRequest, ManagedClient, Message, ResponseCache, RetryPolicy, UsageLedger
    from ams.llm.providers.openai_client import OpenAIClient

    order = list(cases)
    cfg = next(j["config"] for j in plan["jobs"] if j["id"] == "4omini/safe_mem")
    random.Random(cfg.get("seed", 0)).shuffle(order)
    case = order[0]
    sentences = [s.text for s in segment(case.user_query)]
    version = cfg["prompts"]["retention_sentence"]
    prompt = PromptLibrary().get("retention_sentence", version)
    request = ChatRequest(
        messages=(
            Message(
                "user",
                prompt.render(
                    sentences="\n".join(f"{i}. {text}" for i, text in enumerate(sentences))
                ),
            ),
        ),
        model="openai/gpt-4o-mini",
        temperature=0.0,
        max_tokens=60 + 40 * len(sentences),
    )
    cache = ResponseCache(plan["cache_path"])
    ledger = UsageLedger(root / "billing_preflight_usage.jsonl")
    client = ManagedClient(
        OpenAIClient(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            provider="openrouter",
            budget_guard=guard,
            allow_estimated_billing=True,
        ),
        cache=cache,
        ledger=ledger,
        retry=RetryPolicy(max_attempts=1),
        stage="billing_preflight",
    )
    before = guard.snapshot()
    try:
        response = client.complete(request)
        if not response.text.strip():
            guard.halt("empty_billing_preflight_response")
            raise RuntimeError("empty original retention response in billing verification")
        after = guard.snapshot()
        if response.cached and before["counts"]["total"] == 0:
            raise RuntimeError(
                "cached response alone cannot verify live billing for a fresh budget"
            )
        if not response.cached and after["counts"]["total"] <= before["counts"]["total"]:
            raise RuntimeError("live request was not recorded in the persistent budget")
        report = {
            "status": (
                "passed_cached_replay"
                if response.cached
                else "passed_live"
                if after["counts"]["settled"] > before["counts"]["settled"]
                else "passed_live_conservative_estimate"
            ),
            "cid": case.cid,
            "original_method_request": "retention_sentence/" + version,
            "request_reused_by_full_run_cache": True,
            "response_model": response.model,
            "cached": response.cached,
            "response": response.text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "reported_cost_usd": response.usage.cost_usd,
            "budget_before": before,
            "budget_after": after,
        }
        (root / "billing_preflight.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        cache.close()
        ledger.close()


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run_job(
    job: dict,
    root: Path,
    cache: str,
    budget: LedgerBudget,
    limit: float,
    *,
    strict_budget_path: str | None = None,
    reservation_guard=None,
) -> tuple[int, str]:
    budget.poll()
    if budget.cost >= limit:
        return 2, "approved estimated-cost threshold reached before launching the job"
    job_root = root / job["id"]
    job_root.mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        AMS_RESULTS_ROOT=str(job_root),
        AMS_CACHE_PATH=cache,
        HF_HUB_OFFLINE="1",
        TOKENIZERS_PARALLELISM="false",
    )
    if strict_budget_path is not None:
        env["AMS_STRICT_BUDGET_PATH"] = strict_budget_path
        env["AMS_STRICT_BUDGET_LIMIT_USD"] = str(limit)
        env["AMS_BUDGET_ALLOW_ESTIMATED_USAGE"] = "1"
    process = subprocess.Popen(
        job["command"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    secrets = [v for k, v in env.items() if k.endswith("API_KEY") and v]

    def copy_log():
        assert process.stdout is not None
        with (job_root / "execution.log").open("a") as out:
            for line in process.stdout:
                for secret in secrets:
                    line = line.replace(secret, "[REDACTED]")
                out.write(line)
                out.flush()

    reader = threading.Thread(target=copy_log, daemon=True)
    reader.start()
    failure = ""
    try:
        while process.poll() is None:
            budget.poll()
            if reservation_guard is not None:
                snapshot = reservation_guard.snapshot()
                (job_root / "budget_progress.json").write_text(
                    json.dumps(snapshot, indent=2) + "\n"
                )
                if snapshot["blocked"]:
                    failure = "billing verification failed; persistent guard stopped dispatch"
                    stop_process(process)
                    break
            if budget.cost >= limit:
                failure = "approved estimated-cost threshold reached"
                stop_process(process)
                break
            time.sleep(1)
        budget.poll()
    except BaseException:
        stop_process(process)
        raise
    finally:
        reader.join(timeout=5)
    return process.returncode or (2 if failure else 0), failure


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--plan", type=Path, default=ROOT / "reports/full_mpbench_reproduction/plan.json"
    )
    ap.add_argument(
        "--jobs", help="comma-separated backbone/method identifiers; default all prepared jobs"
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="make paid calls only after the user has approved this plan/scope",
    )
    ap.add_argument(
        "--approved-budget-usd",
        type=float,
        help="total approved estimated-cost threshold for this plan, including previous jobs",
    )
    ap.add_argument("--approval-note", default="")
    ap.add_argument(
        "--stop-at-usd",
        type=float,
        default=27.0,
        help="software stop including outstanding reservations (approved default: $27)",
    )
    args = ap.parse_args(argv)
    plan = json.loads(args.plan.read_text())
    validate_plan(plan)
    selected_ids = args.jobs.split(",") if args.jobs else [j["id"] for j in plan["jobs"]]
    jobs = [j for j in plan["jobs"] if j["id"] in selected_ids]
    if len(jobs) != len(selected_ids) or len(set(selected_ids)) != len(selected_ids):
        ap.error("unknown or duplicate selected jobs")
    print(
        json.dumps(
            {
                "plan_sha256": sha256(args.plan),
                "jobs": [j["id"] for j in jobs],
                "mode": "execute" if args.execute else "offline_review_only",
                "dataset": plan["dataset"]["counts"],
                "cost_estimate": str(args.plan.parent / "cost_estimate.json"),
            },
            indent=2,
        ),
        flush=True,
    )
    if not args.execute:
        return 0
    if (
        args.approved_budget_usd is None
        or not math.isfinite(args.approved_budget_usd)
        or args.approved_budget_usd <= 0
    ):
        ap.error(
            "paid execution requires an explicit positive --approved-budget-usd after user approval"
        )
    load_env()
    if not os.environ.get("OPENROUTER_API_KEY"):
        ap.error("OPENROUTER_API_KEY is missing")
    if (
        not math.isfinite(args.stop_at_usd)
        or args.stop_at_usd <= 0
        or args.stop_at_usd > 27
        or args.approved_budget_usd > 30
        or args.approved_budget_usd - args.stop_at_usd < 3
    ):
        ap.error(
            "software threshold must be at most $27 with at least $3 margin below the $30 maximum"
        )
    if set(selected_ids) != {"4omini/safe_mem"}:
        ap.error("the current paid-execution approval covers Original SAFE-Mem only on GPT-4o-mini")
    for job in jobs:
        if any(
            job["config"]["models"][role] != "openrouter:openai/gpt-4o-mini"
            for role in ("memory", "agent", "judge")
        ):
            ap.error("the approved SAFE-Mem run requires GPT-4o-mini for every paid chat role")
    try:
        provider_budget = current_key_budget(os.environ["OPENROUTER_API_KEY"])
        (args.plan.parent / "provider_budget_preflight.json").write_text(
            json.dumps(provider_budget, indent=2) + "\n"
        )
    except ProviderBudgetNotVerified as exc:
        ap.error(f"paid execution stopped before launch: {exc}")
    from ams.llm.budget import BudgetGuard

    strict_budget_path = str(args.plan.parent / "safemem_only_request_budget.sqlite")
    guard = BudgetGuard(strict_budget_path, limit_usd=args.stop_at_usd)
    guard_before = guard.snapshot()
    if guard_before["blocked"] or guard_before["remaining_usd"] <= 0:
        ap.error("the persistent pre-dispatch budget has no verified allowance remaining")
    root = Path(plan["results_root"]) / sha256(args.plan)[:12]
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / "execution.json"
    state = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else {"plan": str(args.plan.resolve()), "jobs": {}}
    )
    state.update(
        approved_budget_usd=args.approved_budget_usd,
        approval_note=args.approval_note,
        approval_recorded_utc=datetime.now(UTC).isoformat(),
        provider_budget_preflight=provider_budget,
        software_stop_usd=args.stop_at_usd,
        account_limit_required=False,
        credential_fingerprint=credential_fingerprint(os.environ["OPENROUTER_API_KEY"]),
        strict_budget_path=strict_budget_path,
        strict_budget_before=guard_before,
    )
    budget = LedgerBudget(root)
    budget.poll()
    if budget.cost >= args.stop_at_usd:
        ap.error("previous usage has already reached the approved threshold")
    from analyse_mpbench_reproduction import analyse_run

    targets = json.loads((ROOT / "reports/mpbench_published_targets.json").read_text())[
        "published_targets"
    ]
    cases, _ = load_mpbench(ROOT / "data/mpbench")
    try:
        state["billing_preflight"] = billing_preflight(plan, cases, guard, root)
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        print(
            "Billing verification passed on the first original retention request: "
            + state["billing_preflight"]["status"],
            flush=True,
        )
        for job in jobs:
            previous = state["jobs"].get(job["id"], {})
            target = next(
                t
                for t in targets
                if t["backbone"] == job["backbone"] and t["method"] == job["method"]
            )
            allow_substitution = bool(
                job["config"].get("reproduction", {}).get("model_substitution")
            )
            if previous.get("status") in ("full_validated", "full_validated_model_substitution"):
                analyse_run(
                    Path(previous["result_directory"]),
                    target,
                    cases,
                    allow_model_substitution=allow_substitution,
                )
                print(f"Already completed and validated: {job['id']}", flush=True)
                continue
            budget.poll()
            if budget.cost >= args.stop_at_usd:
                state["budget_stop"] = (
                    "approved estimated-cost threshold reached before launching the next job"
                )
                state_path.write_text(json.dumps(state, indent=2) + "\n")
                return 2
            state["jobs"][job["id"]] = {
                "status": "running",
                "started_utc": datetime.now(UTC).isoformat(),
            }
            state_path.write_text(json.dumps(state, indent=2) + "\n")
            print(
                f"Starting full dataset: {job['id']} (estimated usage so far ${budget.cost:.3f})",
                flush=True,
            )
            code, reason = run_job(
                job,
                root,
                plan["cache_path"],
                budget,
                args.stop_at_usd,
                strict_budget_path=strict_budget_path,
                reservation_guard=guard,
            )
            entry = state["jobs"][job["id"]]
            entry.update(
                finished_utc=datetime.now(UTC).isoformat(),
                returncode=code,
                estimated_total_cost_usd=budget.cost,
                uncached_provider_calls=budget.calls,
                strict_budget=guard.snapshot(),
            )
            if code:
                entry.update(
                    status="incomplete", reason=reason or "experiment exited with an error"
                )
                state_path.write_text(json.dumps(state, indent=2) + "\n")
                return code
            candidates = sorted(
                (root / job["id"]).glob("*/manifest.json"), key=lambda p: p.stat().st_mtime
            )
            if not candidates:
                raise RuntimeError(f"missing completed manifest for {job['id']}")
            result_dir = candidates[-1].parent
            validation = analyse_run(
                result_dir, target, cases, allow_model_substitution=allow_substitution
            )
            entry.update(
                status=validation["status"], result_directory=str(result_dir), validation=validation
            )
            state_path.write_text(json.dumps(state, indent=2) + "\n")
    except Exception as exc:
        state["last_error"] = f"{type(exc).__name__}: {exc}"
        state["strict_budget_on_error"] = guard.snapshot()
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        raise
    print(f"Selected jobs completed with full coverage; execution record: {state_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
