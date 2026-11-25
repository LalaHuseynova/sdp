"""Reproducibility manifest of the LoCoMo + SAFE-Mem study (free).

Hashes this study's code and protocol text, every frozen file it depends on (Original SAFE-Mem, the
research policy layer, the published baselines, the LLM client/guard code, LoCoMo v1/v2 generator,
metrics and runner), every prompt, SAFE-Mem's LoCoMo configs, the data, the recorded SensitiveAction
verdicts and the exact construction request list; plus the frozen LoCoMo v2 freeze digest.
`verify` recomputes everything; any changed, missing or added file fails. A paid stage refuses
unless `owner_approval.json` names this digest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from locomo_safemem import config as K

REPO = K.REPO
MANIFEST = REPO / "research_data/locomo_safemem/freeze/manifest.json"
REQUESTS = REPO / "research_data/locomo_safemem/requests/construction.jsonl.gz"
GLOBS = ["locomo_safemem/*.py", "locomo_safemem/tests/*.py", "prompts/*/*.txt",
         "src/ams/memory/*.py", "src/ams/core/*.py", "src/ams/eval/use_type.py", "src/ams/eval/locomo.py",
         "src/ams/eval/judge.py", "src/ams/research/retrieval/*.py", "src/ams/research/dynamic/*.py",
         "src/ams/research/sequential/*.py", "src/ams/research/evidence_memoization.py",
         "src/ams/research/provisional_run/runner.py", "src/ams/research/workload/lineage.py",
         "src/ams/research/workload/sv2.py", "src/ams/research/workload/published.py",
         "src/ams/research/workload/integration.py", "src/ams/research/workload/runner.py",
         "src/ams/research/workload/adaptive.py", "src/ams/research/workload/generator.py",
         "src/ams/research/protocol_v2/randec_cache.py", "src/ams/baselines/*.py",
         "src/ams/llm/*.py", "src/ams/llm/providers/*.py", "src/ams/data/locomo.py",
         "locomo_v1/*.py", "locomo_v2/*.py", "locomo_v2_supp/runner.py", "locomo_v2_supp/published_supp.py",
         "locomo_v2_supp/supplementary.py", "research_data/locomo_feasibility_20261119/feasibility.py",
         "configs/v31_locomo_withhold_a.yaml", "configs/v31_locomo_withhold_b.yaml",
         "data/locomo/locomo10.json", "research_data/locomo_v1_freeze/sensitive_verdicts.json",
         K.PROTOCOL_TEXT]


def files() -> dict:
    out = {}
    for g in GLOBS:
        for p in sorted(REPO.glob(g)):
            if p.is_file() and "__pycache__" not in p.parts:
                out[str(p.relative_to(REPO)).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    if REQUESTS.exists():
        out[str(REQUESTS.relative_to(REPO))] = hashlib.sha256(REQUESTS.read_bytes()).hexdigest()
    return out


def v2_freeze_ok() -> tuple[bool, str]:
    from locomo_v2 import __main__ as CLI

    ref = json.loads((CLI.FREEZE / "freeze_manifest.json").read_text())
    return CLI.freeze_files() == ref["files"], ref["digest"]


def digest_of(h: dict) -> str:
    return hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()


def prepare() -> dict:
    h = files()
    ok, v2 = v2_freeze_ok()
    assert ok, "LoCoMo v2 freeze changed"
    import locomo_safemem.store as ST

    m = {"protocol": K.PROTOCOL_ID, "evidence": K.EVIDENCE, "files": h, "n_files": len(h), "digest": digest_of(h),
         "locomo_v2_freeze_digest": v2, "safe_mem_settings": ST.SAFE_MEM, "retrieve_k": ST.RETRIEVE_K,
         "seeds": {"v2": K.SEED, "v2_new": K.SEED_V2, "this_study": K.SEED_SM}, "model": K.MODEL,
         "embed_model": K.EMBED_MODEL, "utc": datetime.now(UTC).isoformat(timespec="seconds")}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True))
    return m


def verify() -> dict:
    if not MANIFEST.exists():
        return {"ok": False, "changed": ["<no manifest>"], "digest": None}
    m = json.loads(MANIFEST.read_text())
    now = files()
    changed = sorted(k for k in set(now) | set(m["files"]) if now.get(k) != m["files"].get(k))
    ok2, v2 = v2_freeze_ok()
    return {"ok": not changed and ok2 and v2 == m["locomo_v2_freeze_digest"], "changed": changed,
            "digest": m["digest"], "locomo_v2_freeze_ok": ok2, "n_files": len(now)}
