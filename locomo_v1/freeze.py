"""Freeze manifest (protocol section 11): prepare once, verify before every paid start.
A manifest is never overwritten. The digest is the SHA-256 of the canonical manifest body."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from . import config as K

FROZEN_MODULES = (  # imported unchanged; each must equal its Option B manifest hash
    "src/ams/research/dynamic/ledger.py", "src/ams/research/dynamic/policies.py",
    "src/ams/research/dynamic/models.py", "src/ams/research/workload/lineage.py",
    "src/ams/research/workload/integration.py",
)
REUSED = (  # reused unchanged code outside the Option B manifest
    "research_data/locomo_feasibility_20261119/feasibility.py", "minja_v2/adapter.py",
    "minja_v2/runner.py", "src/ams/eval/locomo.py", "src/ams/data/locomo.py",
    "src/ams/core/prompts.py", "src/ams/llm/budget.py", "src/ams/llm/pool.py",
    "src/ams/llm/cache.py", "src/ams/llm/registry.py", "src/ams/llm/providers/openai_client.py",
)
PROMPTS = ("prompts/locomo_qa/v1.txt", "prompts/locomo_judge/v1.txt",
           "prompts/locomo_memory_start/v1.txt")


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def collect(build_dir: Path, env: dict) -> dict:
    root = K.REPO
    code = sorted(p for p in (root / "locomo_v1").rglob("*.py") if "__pycache__" not in p.parts)
    files = {
        "code": {p.relative_to(root).as_posix(): sha(p) for p in code},
        "reused": {f: sha(root / f) for f in REUSED},
        "frozen_modules": {f: sha(root / f) for f in FROZEN_MODULES},
        "prompts": {f: sha(root / f) for f in PROMPTS},
        "protocol": {K.PROTOCOL_TEXT: sha(root / K.PROTOCOL_TEXT)},
        "data": {"data/locomo/locomo10.json": sha(K.DATA)},
        "build": {p.name: sha(p) for p in sorted(build_dir.glob("*")) if p.is_file()},
        "draws": {"draws.json": sha(build_dir.parent / "draws.json")}
        if (build_dir.parent / "draws.json").exists() else {},
    }
    return {"protocol_id": K.PROTOCOL_ID, "files": files, "environment": env,
            "config": {k: (str(v) if isinstance(v, Path) else v)
                       for k, v in vars(K).items() if k.isupper()}}


def check_option_b() -> dict:
    """Every frozen module equals its Option B hash, and the Option B freeze verifies."""
    manifest = json.loads((K.REPO / K.OPTION_B_MANIFEST).read_text())
    text = json.dumps(manifest)
    mism = [f for f in FROZEN_MODULES if sha(K.REPO / f) not in text]
    proc = subprocess.run([sys.executable, "scripts/freeze_protocol_v2.py", "verify", "--protocol",
                           K.OPTION_B_MANIFEST], cwd=K.REPO, capture_output=True, text=True)
    ok = proc.returncode == 0 and '"verified"' in proc.stdout and K.OPTION_B_DIGEST in proc.stdout
    return {"frozen_modules_match_option_b": not mism, "mismatch": mism,
            "option_b_verified": ok}


def prepare(build_dir: Path, out: Path, env: dict) -> str:
    if out.exists():
        raise SystemExit(f"{out} exists; a manifest is never overwritten")
    ob = check_option_b()
    if not (ob["frozen_modules_match_option_b"] and ob["option_b_verified"]):
        raise SystemExit(f"Option B check failed: {ob}")
    body = collect(build_dir, env)
    digest = hashlib.sha256(canonical(body).encode()).hexdigest()
    out.write_text(json.dumps({"digest": digest, "option_b": ob, **body}, indent=1))
    return digest


def verify(build_dir: Path, manifest: Path, env: dict) -> dict:
    saved = json.loads(manifest.read_text())
    body = collect(build_dir, env)
    digest = hashlib.sha256(canonical(body).encode()).hexdigest()
    diffs = [f"{g}/{k}" for g in body["files"] for k in set(body["files"][g]) |
             set(saved["files"].get(g, {})) if body["files"][g].get(k) !=
             saved["files"].get(g, {}).get(k)]
    if body["environment"] != saved["environment"]:
        diffs.append("environment")
    ob = check_option_b()
    return {"verified": digest == saved["digest"] and not diffs and ob["option_b_verified"]
            and ob["frozen_modules_match_option_b"], "digest": digest,
            "saved_digest": saved["digest"], "diffs": diffs, "option_b": ob}
