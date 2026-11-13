#!/usr/bin/env python
"""Offline planning estimates; never sends provider requests or reads API keys."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from ams.core.prompts import PromptLibrary
from ams.core.spans import segment
from ams.data.mpbench import load_mpbench

ROOT = Path(__file__).resolve().parents[1]
PILOTS = {
    "simple": ROOT / "results/openrouter_mpbench_baseline_pool6240-20261028T091551Z/usage.jsonl",
    "safemem": ROOT / "results/openrouter_mpbench_safemem_pool6240-20261028T091550Z/usage.jsonl",
}


def _pilot_statistics(path: Path) -> dict:
    totals = defaultdict(lambda: [0, 0, 0])
    cached = defaultdict(int)
    local = 0
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row["cached"]:
                cached[row["provider"]] += 1
            elif row["provider"] == "openrouter":
                item = totals[row["stage"]]
                item[0] += 1
                item[1] += row["input_tokens"]
                item[2] += row["output_tokens"]
            elif row["provider"] == "local":
                local += 1
    return {
        "path": str(path.relative_to(ROOT)),
        "available": path.exists(),
        "uncached_openrouter_by_stage": {
            key: {"calls": n, "mean_input": inp / n, "mean_output": out / n}
            for key, (n, inp, out) in sorted(totals.items())
        },
        "uncached_local_operations": local,
        "cached_operations_by_provider": dict(cached),
    }


def _mean_stage(pilot: dict, stage: str, fallback: tuple[float, float]) -> tuple[float, float]:
    row = pilot["uncached_openrouter_by_stage"].get(stage)
    return (row["mean_input"], row["mean_output"]) if row else fallback


def _method(job: dict) -> str:
    cfg = job["config"]
    if cfg.get("memory_system") == "typed":
        return "safemem"
    if cfg.get("write_isolation") == "drift":
        return "drift"
    defenses = cfg.get("defences", [])
    if len(defenses) != 1:
        raise ValueError(f"{job['id']}: estimate expects one defense per job, got {defenses}")
    defense = defenses[0]
    return {
        "no_defence": "simple",
        "a_memguard": "amemguard",
        "randec_distil": "randec",
        "llm_sanitiser": "sanitizer",
        "memlineage_coarse": "memlineage",
        "memlineage_lm": "memlineage_lm",
        "integrity_gate": "integrity_sensitive",
        "integrity_gate_all": "integrity_all",
        "tma_nm_strict": "tma_strict",
        "tma_nm_values": "tma_values",
    }[defense]


def _catalog_index(catalog: dict | list) -> dict:
    rows = catalog if isinstance(catalog, list) else catalog.get("models", catalog.get("data", []))
    return {row["id"]: row for row in rows}


def estimate_jobs(jobs: list[dict], catalog: dict | list, cases) -> dict:
    """Estimate each resolved single-method job; all jobs are planned cold-cache.

    jobs: [{id, backbone, method, config: {models, defences, ...}, source_config}]
    catalog: saved OpenRouter /models response or {models: [...]} audit wrapper.
    cases: objects returned by load_mpbench, including cases without read queries.
    """
    cases = list(cases)
    read = [c for c in cases if c.retrieval_query.strip()]
    adv = [c for c in read if c.is_adversarial]
    benign_scorable = [c for c in read if not c.is_adversarial and c.expected_memory.strip()]
    n_write, n_read, n_attack = len(cases), len(read), len(adv)
    answers = n_read + n_attack
    judges = 4 * n_attack + len(benign_scorable)
    n_retention = sum(c.legitimate_memory_write is True for c in cases)
    n_query_write = sum(bool(c.user_query.strip()) for c in cases)
    n_context = sum(bool(c.context.strip()) for c in cases)
    models = _catalog_index(catalog)
    pilots = {key: _pilot_statistics(path) for key, path in PILOTS.items()}
    simple_in, simple_out = _mean_stage(pilots["simple"], "memory_write", (500, 115))
    answer_in, answer_out = _mean_stage(pilots["simple"], "agent_answer", (300, 40))
    judge_in, judge_out = _mean_stage(pilots["simple"], "judge", (370, 30))
    safe_answer_in, safe_answer_out = _mean_stage(pilots["safemem"], "agent_answer", (400, 40))
    safe_judge_in, safe_judge_out = _mean_stage(pilots["safemem"], "judge", (350, 30))
    prompts = PromptLibrary()
    pilot_cases = [c for c in cases if c.is_adversarial][:40]
    pilot_cases += [c for c in cases if not c.is_adversarial][:40]

    def extracted_chars(case):
        return len(
            prompts.get("memory_extract", "v1").render(
                query=case.user_query.strip(), context=case.context.strip()
            )
        )

    sample_mean_chars = mean(map(extracted_chars, pilot_cases)) if pilot_cases else 2000
    corpus_mean_chars = mean(map(extracted_chars, cases)) if cases else sample_mean_chars
    input_ratio = corpus_mean_chars / sample_mean_chars
    # Extrapolate actual input usage rather than treating character counts as token counts.
    simple_in *= input_ratio
    retention_caps = [60 + 40 * len(segment(c.user_query)) for c in cases if c.user_query.strip()]
    retention_cap = mean(retention_caps) if retention_caps else 100
    result_jobs = []

    for job in jobs:
        cfg = job["config"]
        if int(cfg.get("pool_size", 1)) != n_write:
            raise ValueError(f"{job['id']}: pool_size must match all {n_write} writes")
        kind = _method(job)
        k = int(cfg.get("retrieve_k", 4))
        selected = cfg["models"]
        resolved_models = {}
        for role in ("memory", "agent", "judge"):
            spec = selected[role]
            if not spec.startswith("openrouter:"):
                raise ValueError(f"{job['id']}: {role} must explicitly use OpenRouter")
            model_id = spec.partition(":")[2]
            if model_id not in models:
                raise ValueError(f"Unpriced model absent from supplied catalog: {model_id}")
            price = models[model_id]["pricing"]
            if price.get("request") not in (None, "0", "0.0"):
                raise ValueError(f"Unmodeled per-request surcharge for {model_id}")
            resolved_models[role] = {
                "id": model_id,
                "input_usd_per_token": float(price["prompt"]),
                "output_usd_per_token": float(price["completion"]),
            }
        # Cross-backbone output lengths are unknown before execution; use explicit allowances.
        model_id = resolved_models["memory"]["id"]
        output_factor = (
            1.5
            if "gpt-5.6" in model_id
            else 1.25
            if "claude" in model_id
            else 1.4
            if "qwen" in model_id
            else 1.0
        )
        scenarios = {}
        for conservative in (False, True):
            stages = []
            input_factor = 2.0 if conservative else 1.0
            length_factor = 2.0 if conservative else 1.0

            def add(
                stage,
                role,
                calls,
                inp,
                out,
                output_cap=None,
                *,
                _length_factor=length_factor,
                _output_factor=output_factor,
                _models=resolved_models,
                _input_factor=input_factor,
                _stages=stages,
            ):
                calls = math.ceil(calls)
                out = out * _length_factor * (_output_factor if role != "judge" else 1.0)
                if output_cap is not None:
                    out = min(out, output_cap)
                price = _models[role]
                tokens_in, tokens_out = (
                    math.ceil(calls * inp * _input_factor),
                    math.ceil(calls * out),
                )
                cost = (
                    tokens_in * price["input_usd_per_token"]
                    + tokens_out * price["output_usd_per_token"]
                )
                _stages.append(
                    {
                        "stage": stage,
                        "role": role,
                        "model": price["id"],
                        "logical_chat_requests": calls,
                        "input_tokens": tokens_in,
                        "output_tokens": tokens_out,
                        "estimated_usd": round(cost, 6),
                    }
                )

            if kind == "safemem":
                add("retention_sentences", "memory", n_query_write, 400, 60, retention_cap)
                extra_passes = n_write if conservative else n_retention
                add(
                    "typed_extraction",
                    "memory",
                    n_write + extra_passes,
                    max(600, simple_in * 1.5),
                    190,
                    900,
                )
                add("use_classification", "memory", n_read, 350, 4, 24)
                conflict_pairs = k * (k - 1) / 2
                add(
                    "conflict_checks",
                    "memory",
                    n_read * (conflict_pairs if conservative else 0.5),
                    220,
                    3,
                    6,
                )
                add(
                    "answers_with_and_without_memory",
                    "agent",
                    answers,
                    safe_answer_in * 1.2,
                    safe_answer_out * 1.2,
                    200,
                )
                add("original_judges", "judge", judges, safe_judge_in * 1.2, safe_judge_out, 120)
            else:
                add("simple_extraction", "memory", n_write, simple_in, simple_out, 400)
                add(
                    "answers_with_and_without_memory",
                    "agent",
                    answers,
                    answer_in * 1.2,
                    answer_out * 1.2,
                    200,
                )
                add("original_judges", "judge", judges, judge_in * 1.2, judge_out, 120)

            if kind == "amemguard":
                add("consensus_reasoning_chains", "agent", k * n_read, 600, 160, 2048)
                add("consensus_audit", "agent", n_read, 1100, 100, 2048)
            elif kind == "drift":
                add(
                    "injection_isolator",
                    "agent",
                    n_context * (2 if conservative else 1),
                    max(900, simple_in * 1.6),
                    180 if not conservative else 800,
                    10000,
                )
            elif kind == "sanitizer":
                add("sanitizer_audit", "agent", k * n_read, 650, 8, 1024)
                add(
                    "sanitizer_rewrite",
                    "agent",
                    k * n_read * (1.0 if conservative else 0.15),
                    550,
                    110,
                    1024,
                )
            elif kind in ("memlineage", "memlineage_lm", "integrity_sensitive"):
                add("sensitive_action", "agent", n_read, 190, 2, 4)
                if kind == "memlineage_lm":
                    add("lm_parent_attribution", "agent", k * n_read, 1100, 25, 200)

            logical_requests = sum(s["logical_chat_requests"] for s in stages)
            raw_cost = sum(s["estimated_usd"] for s in stages)
            reserve = raw_cost * 0.20 if conservative else 0.0
            scenarios["conservative" if conservative else "typical"] = {
                "logical_chat_requests": logical_requests,
                "assumed_uncached_paid_requests": logical_requests,
                "cache_discount_requests": 0,
                "input_tokens": sum(s["input_tokens"] for s in stages),
                "output_tokens": sum(s["output_tokens"] for s in stages),
                "token_cost_usd": round(raw_cost, 4),
                "incidental_request_and_pricing_reserve_usd": round(reserve, 4),
                "estimated_usd": round(raw_cost + reserve, 4),
                "stages": stages,
            }
        result_jobs.append(
            {
                "id": job["id"],
                "backbone": job["backbone"],
                "method": job["method"],
                "cost_model_method": kind,
                "source_config": job.get("source_config"),
                "models": resolved_models,
                "scenarios": scenarios,
                "local_embeddings": {
                    "provider": "local",
                    "estimated_usd": 0,
                    "operations": (
                        "Depend on extracted claims, evidence chunks, and cache reuse; "
                        "excluded from paid request counts."
                    ),
                },
            }
        )

    def totals(rows):
        return {
            scenario: {
                "logical_chat_requests": sum(
                    r["scenarios"][scenario]["logical_chat_requests"] for r in rows
                ),
                "estimated_usd": round(
                    sum(r["scenarios"][scenario]["estimated_usd"] for r in rows), 2
                ),
                "input_tokens": sum(r["scenarios"][scenario]["input_tokens"] for r in rows),
                "output_tokens": sum(r["scenarios"][scenario]["output_tokens"] for r in rows),
            }
            for scenario in ("typical", "conservative")
        }

    groups = {
        b: [r for r in result_jobs if r["backbone"] == b]
        for b in sorted({r["backbone"] for r in result_jobs})
    }
    core = [
        r
        for r in result_jobs
        if r["cost_model_method"] in ("simple", "safemem")
        and r["models"]["memory"]["id"] == "openai/gpt-4o-mini"
    ]
    return {
        "status": "offline_estimate_only_execution_requires_approval",
        "catalog_source": catalog.get("source") if isinstance(catalog, dict) else None,
        "catalog_fetched_utc": catalog.get("fetched_utc") if isinstance(catalog, dict) else None,
        "counts": {
            "writes": n_write,
            "reads": n_read,
            "attack_reads": n_attack,
            "benign_scorable_reads": len(benign_scorable),
            "answer_requests": answers,
            "judge_requests_upper": judges,
        },
        "pilot_calibration": pilots,
        "full_to_pilot_extraction_input_length_ratio": input_ratio,
        "jobs": result_jobs,
        "by_job": {row["id"]: row for row in result_jobs},
        "totals": totals(result_jobs),
        "by_backbone": {b: totals(rows) for b, rows in groups.items()},
        "core_gpt4omini": {"job_ids": [r["id"] for r in core], **totals(core)},
        "assumptions": [
            (
                "All jobs are planned cold-cache; no discount for existing cache, "
                "cross-method extraction, repeated judges, or cross-backbone judge reuse."
            ),
            (
                "Existing 80-case GPT-4o-mini usage calibrates extraction/answer/judge lengths "
                "only; this selected repetition-only smoke workload is not a representative sample."
            ),
            (
                "Typical read prompts have a 20% input/output allowance. Other-backbone output "
                "allowances are 1.5 for GPT-5.6, 1.25 for Claude, and 1.4 for Qwen; "
                "these are not measurements."
            ),
            (
                "Typical SAFE-Mem workload assumes 0.5 conflict checks/read and one extra "
                "extraction pass per labeled retention request; actual model outputs may differ."
            ),
            (
                "Unrun baseline assumptions per call: AMG chain 600 input/160 output tokens, "
                "audit 1100/100; sanitizer 650/8 with 15% rewrites at 550/110; DRIFT >=900/180."
            ),
            (
                "Conservative scenario doubles assumed input/output lengths. SAFE-Mem uses "
                "two extraction passes and up to six conflict checks/read; sanitizer rewrites "
                "all candidates; DRIFT uses two calls/write and 800-token replies before doubling."
            ),
            (
                "Conservative total adds a 20% incidental/pricing reserve. It is a planning "
                "scenario, not a statistical interval, hard dollar cap, or worst-case token bound."
            ),
            (
                "DRIFT permits 10,000 output tokens/call and AMG permits 2,048. Use near those "
                "caps could exceed this scenario. Reasoning must remain disabled as configured."
            ),
            (
                "Local embeddings cost zero API dollars and are excluded from paid chat counts. "
                "Cached operations cost zero new API dollars but appear in original ledger totals."
            ),
            (
                "Successful logical requests exclude SDK/managed retries, provider cache rates, "
                "taxes, credit fees, or unexpected surcharges. "
                "Prices are saved public catalog rates."
            ),
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Full MPBench offline cost estimate",
        "",
        "No paid calls were made to produce this estimate. Execution requires approval.",
        "",
        (
            "Each job writes all 6,240 cases; reads/scoring follow the original protocol. "
            "Every job is priced as cold-cache; shared-cache reuse may lower the total."
        ),
        "",
        "| Backbone | Method | Typical paid requests | Typical USD | Conservative planning USD |",
        "|---|---|---:|---:|---:|",
    ]
    for r in report["jobs"]:
        t, c = r["scenarios"]["typical"], r["scenarios"]["conservative"]
        lines.append(
            f"| {r['backbone']} | {r['method']} | {t['logical_chat_requests']:,} "
            f"| ${t['estimated_usd']:.2f} | ${c['estimated_usd']:.2f} |"
        )
    t, c = report["totals"]["typical"], report["totals"]["conservative"]
    lines += [
        "",
        f"All jobs: approximately **${t['estimated_usd']:.2f} typical**, "
        f"**${c['estimated_usd']:.2f} conservative planning**; "
        f"{t['logical_chat_requests']:,} typical logical paid requests before cache savings.",
        "",
    ]
    core = report["core_gpt4omini"]
    lines += [
        "Included GPT-4o-mini core-method jobs "
        f"({', '.join(core['job_ids']) or 'none'}): "
        f"**${core['typical']['estimated_usd']:.2f} typical**, "
        f"**${core['conservative']['estimated_usd']:.2f} conservative planning**.",
        "",
        "## Assumptions and practical limits",
        "",
    ]
    lines += [f"- {a}" for a in report["assumptions"]]
    lines += [
        "",
        (
            "The conservative figure is not a guaranteed spending ceiling. A separately enforced "
            "execution budget is needed for a hard limit. "
            "This estimate grants no execution approval."
        ),
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, help="JSON list or object containing jobs")
    parser.add_argument("--catalog", default="reports/openrouter_full_reproduction_models.json")
    parser.add_argument("--output-prefix", default="reports/full_mpbench_cost_estimate")
    args = parser.parse_args()
    raw_jobs = json.loads(Path(args.jobs).read_text())
    jobs = raw_jobs["jobs"] if isinstance(raw_jobs, dict) else raw_jobs
    catalog = json.loads(Path(args.catalog).read_text())
    cases, _ = load_mpbench("data/mpbench")
    report = estimate_jobs(jobs, catalog, cases)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    prefix.with_suffix(".md").write_text(render_markdown(report))
    print(
        json.dumps(
            {
                "jobs": len(jobs),
                "totals": report["totals"],
                "core_gpt4omini": report["core_gpt4omini"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
