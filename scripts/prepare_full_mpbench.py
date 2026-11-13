#!/usr/bin/env python
"""Prepare frozen full-dataset MPBench jobs. This script never calls an LLM."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ams.core.env import load_env
from ams.core.prompts import PromptLibrary
from ams.data.mpbench import load_mpbench

ROOT = Path(__file__).resolve().parents[1]
BACKBONES = {
    "4omini": ("openai/gpt-4o-mini", "SAFE_MEM_MODEL_4OMINI"),
    "gpt56": ("openai/gpt-5.6-terra", "SAFE_MEM_MODEL_GPT56"),
    "haiku55": ("anthropic/claude-haiku-5.5", "SAFE_MEM_MODEL_HAIKU55"),
    "qwen38flash": ("qwen/qwen3.8-flash", "SAFE_MEM_MODEL_QWEN38FLASH"),
}
METHODS = {
    "no_defence": ("configs/mpbench.yaml", "no_defence"),
    "safe_mem": ("configs/v31_mpbench_withhold.yaml", "no_defence"),
    "a_memguard": ("configs/mpbench.yaml", "a_memguard"),
    "drift": ("configs/mpbench_drift.yaml", "no_defence"),
    "randec_distil": ("configs/mpbench_baselines.yaml", "randec_distil"),
    "llm_sanitiser": ("configs/mpbench_baselines.yaml", "llm_sanitiser"),
    "memlineage_coarse": ("configs/mpbench_baselines.yaml", "memlineage_coarse"),
    "integrity_gate_all": ("configs/mpbench_baselines.yaml", "integrity_gate_all"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_slug(value: str) -> str:
    value = value.removeprefix("openrouter:")
    if value.count("/") != 1 or any(c.isspace() for c in value) or ":" in value or "@" in value:
        raise ValueError("model variables must contain an OpenRouter author/model identifier")
    return value


def build_jobs(backbones: list[str], methods: list[str]) -> list[dict]:
    if len(backbones) != 1 and any(
        os.environ.get(k) for k in ("SAFE_MEM_MEMORY_MODEL", "SAFE_MEM_AGENT_MODEL")
    ):
        raise ValueError("global memory/agent overrides require selecting exactly one backbone")
    # The four original paper backbone presets select 16 workers.
    workers = int(os.environ.get("SAFE_MEM_WORKERS", "16"))
    if workers < 1:
        raise ValueError("SAFE_MEM_WORKERS must be positive")
    judge = model_slug(os.environ.get("SAFE_MEM_JUDGE_MODEL", "openai/gpt-4o-mini"))
    jobs = []
    for backbone in backbones:
        default, env_var = BACKBONES[backbone]
        chosen = model_slug(os.environ.get(env_var, default))
        memory = model_slug(os.environ.get("SAFE_MEM_MEMORY_MODEL", chosen))
        agent = model_slug(os.environ.get("SAFE_MEM_AGENT_MODEL", chosen))
        for method in methods:
            source, defence = METHODS[method]
            original = yaml.safe_load((ROOT / source).read_text())
            cfg = copy.deepcopy(original)
            cfg["name"] = f"full_mpbench_{backbone}_{method}"
            cfg["models"].update(
                memory=f"openrouter:{memory}",
                agent=f"openrouter:{agent}",
                judge=f"openrouter:{judge}",
            )
            cfg["pool_size"] = 6240
            cfg["defences"] = [defence]
            cfg["runtime"] = {**cfg.get("runtime", {}), "workers": workers}
            effort = {m: "none" for m in (memory, agent) if m != "openai/gpt-4o-mini"}
            if effort:
                cfg["reasoning_effort"] = effort
            cfg["reproduction"] = {
                "backbone": backbone,
                "method": method,
                "source_config": source,
                "full_dataset": True,
                "original_backbone_model": default,
                "model_substitution": memory != default
                or agent != default
                or judge != "openai/gpt-4o-mini",
                "transport": "OpenRouter; no model fallbacks",
                "identity_fix": "split-qualified internal case IDs; raw data unchanged",
            }
            jobs.append(
                {
                    "id": f"{backbone}/{method}",
                    "backbone": backbone,
                    "method": method,
                    "source_config": source,
                    "config": cfg,
                }
            )
    return jobs


def code_fingerprints() -> dict[str, str]:
    paths = list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py"))
    paths += [p for p in (ROOT / "prompts").rglob("*") if p.is_file()]
    paths += [ROOT / p for p in {v[0] for v in METHODS.values()}]
    paths += [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(set(paths))}


def original_method_integrity() -> dict:
    paths = subprocess.check_output(
        [
            "git",
            "ls-files",
            "src/ams/memory",
            "src/ams/core",
            "prompts",
            "src/ams/baselines",
            *sorted({v[0] for v in METHODS.values()}),
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    changed = []
    for path in paths:
        original = subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)
        if original != (ROOT / path).read_bytes():
            changed.append(path)
    return {"files_compared": len(paths), "changed_files": changed, "all_original": not changed}


def prompt_fingerprints() -> dict[str, str]:
    library = PromptLibrary()
    for path in sorted((ROOT / "prompts").glob("*/*.txt")):
        library.get(path.parent.name, path.stem)
    return library.fingerprint()


def local_artifact_fingerprints() -> dict[str, str]:
    paths = list((ROOT / "third_party/AMemGuard/ReAct").glob("*.py"))
    paths += list((ROOT / "third_party/AMemGuard/certified-llm-safety").glob("*.py"))
    paths.append(ROOT / "third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt")
    hub = Path.home() / ".cache/huggingface/hub"
    for model in ("sentence-transformers--all-MiniLM-L6-v2", "distilbert-base-uncased"):
        base = hub / f"models--{model}"
        reference = base / "refs/main"
        if reference.exists():
            paths.append(reference)
            revision = reference.read_text().strip()
            paths += [p for p in (base / "snapshots" / revision).rglob("*") if p.is_file()]
    return {str(p): sha256(p) for p in sorted(set(paths)) if p.is_file()}


def third_party_revisions() -> dict:
    result = {}
    for name in ("AMemGuard", "mem-inv-bench"):
        path = ROOT / "third_party" / name
        result[name] = {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=path, text=True
            ).strip(),
            "tracked_changes": subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"], cwd=path, text=True
            ).splitlines(),
        }
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backbones", default=",".join(BACKBONES))
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--output-dir", type=Path, default=ROOT / "reports/full_mpbench_reproduction")
    ap.add_argument(
        "--catalog", type=Path, default=ROOT / "reports/openrouter_full_reproduction_models.json"
    )
    args = ap.parse_args(argv)
    load_env()
    backbones, methods = args.backbones.split(","), args.methods.split(",")
    if not set(backbones) <= BACKBONES.keys() or not set(methods) <= METHODS.keys():
        ap.error("unknown backbone or method; use the published matrix names")
    if len(set(backbones)) != len(backbones) or len(set(methods)) != len(methods):
        ap.error("duplicate backbones or methods")
    cases, _ = load_mpbench(ROOT / "data/mpbench")
    counts = {
        "ingestions": len(cases),
        "attack_ingestions": sum(c.is_adversarial for c in cases),
        "attack_reads": sum(c.is_adversarial and bool(c.retrieval_query.strip()) for c in cases),
        "benign_reads": sum(
            not c.is_adversarial and bool(c.retrieval_query.strip()) for c in cases
        ),
    }
    if counts != {
        "ingestions": 6240,
        "attack_ingestions": 3241,
        "attack_reads": 2999,
        "benign_reads": 2997,
    }:
        ap.error(f"dataset counts do not match the audited full protocol: {counts}")
    official = json.loads((ROOT / "reports/mpbench_official_byte_validation.json").read_text())
    for row in official["verified_files"]:
        if sha256(ROOT / row["path"]) != row["sha256"] or not row["matches_official"]:
            ap.error("dataset differs from the official byte validation")
    integrity = original_method_integrity()
    if not integrity["all_original"]:
        ap.error(
            "original memory/governance/prompts/baseline files changed: "
            f"{integrity['changed_files']}"
        )
    jobs = build_jobs(backbones, methods)
    catalog = json.loads(args.catalog.read_text())
    available = {r["id"] for r in catalog["models"]}
    for job in jobs:
        for role in ("memory", "agent", "judge"):
            if model_slug(job["config"]["models"][role]) not in available:
                ap.error(
                    "selected model is absent from the saved public model/pricing catalog; "
                    "refresh the catalog first"
                )
    output = args.output_dir.resolve()
    (output / "configs").mkdir(parents=True, exist_ok=True)
    for job in jobs:
        config_path = output / "configs" / (job["id"].replace("/", "_") + ".yaml")
        config_path.write_text(yaml.safe_dump(job["config"], sort_keys=False))
        job["config_path"] = str(config_path)
        job["config_sha256"] = sha256(config_path)
        job["command"] = [
            str(ROOT / ".venv/bin/python"),
            "scripts/run_mpbench.py",
            "--config",
            str(config_path),
            "--require-full",
            "--yes",
        ]
    from estimate_mpbench_cost import estimate_jobs

    estimate = estimate_jobs(jobs, catalog, cases)
    (output / "cost_estimate.json").write_text(json.dumps(estimate, indent=2) + "\n")
    plan = {
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "awaiting_explicit_paid_execution_approval",
        "paid_llm_calls_during_preparation": 0,
        "repository": str(ROOT),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dataset": {"counts": counts, "official_validation": official},
        "original_method_integrity": integrity,
        "available_prompt_fingerprints": prompt_fingerprints(),
        "local_artifact_sha256": local_artifact_fingerprints(),
        "third_party_revisions": third_party_revisions(),
        "models_catalog": catalog,
        "source_sha256": code_fingerprints(),
        "cache_path": str(output / "cache/responses.sqlite"),
        "results_root": str(ROOT / "results/full_mpbench_reproduction"),
        "jobs": jobs,
        "estimate": estimate,
    }
    path = output / "plan.json"
    path.write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(
            {
                "plan": str(path),
                "plan_sha256": sha256(path),
                "jobs": len(jobs),
                "counts": counts,
                "original_method_integrity": integrity,
                "cost_estimate": str(output / "cost_estimate.json"),
                "paid_llm_calls": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
