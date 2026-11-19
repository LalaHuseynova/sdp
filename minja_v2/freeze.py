"""MINJA freeze (protocol §1.7, plan M2.6): prepare / verify a manifest of everything that
decides a MINJA result, plus the Option B freeze of the frozen defences it reuses.

Hashed: the minja_v2 package, the MINJA harness scripts and configs, the protocol text and
runbook, MINJA's EHR code as patched (and its commit), the other vendored commits, the demo
database, the pair list, the environment lists, and protocol.protocol(). The Option B
manifest must verify, and every frozen module the adapter imports must equal its Option B
hash.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from ams.research.dynamic.models import check, digest

from . import protocol as P

REPO = P.REPO
VERSION = "minja-v2-freeze-v3"  # rev 3: 48 pairs, mixed-history memory, rev 3 conditions
# (rev 2: single-call layer, per-question reset, failure log)
FILES = {
    "minja_v2": ["minja_v2/*.py", "minja_v2/tests/*.py"],
    "harness": ["scripts/minja_v2.py", "scripts/minja_patch.py", "scripts/minja_report.py",
                "configs/minja_typed.yaml", "configs/minja_baselines.yaml",
                "configs/backbones.yaml"],
    "protocol_text": [P.PROTOCOL_TEXT, "research_data/minja_v2_freeze_20261115/RUNBOOK_rev3.md"],
    "minja_code": ["third_party/MINJA/EHR/ehragent/*.py",
                   "third_party/MINJA/EHR/ehragent/tools/*.py",
                   "third_party/MINJA/EHR/ehragent/ehrsql-ehragent/*.py",
                   "third_party/MINJA/EHR/ehragent/ehrsql-ehragent/mimic_iii/patient_only.json",
                   "third_party/MINJA/EHR/ehragent/ehrsql-ehragent/mimic_iii/valid_preprocessed.json"],
    "amemguard_code": ["third_party/AMemGuard/EhrAgent/ehragent/consistency.py"],
    "data": ["data/mimic_demo/ehragent_tables/mimic_iii.db",
             "data/mimic_demo/ehragent_tables/*.csv",
             "research_data/minja_v2_freeze_20261115/pairs.json", P.PAIRS_FILE],
    "environment": ["research_data/minja_env_20261115/pip_freeze.txt",
                    "research_data/minja_env_20261115/pip_freeze_minja.txt",
                    "research_data/minja_env_20261115/requirements_locked_full.txt"],
}  # fmt: skip
VENDORED = {"MINJA": P.MINJA_COMMIT,
            "AMemGuard": "dd92f7ff21b9a904a703141be3d5b80170e57228",
            "mem-inv-bench": "050b2ea5d6560c40f4eec7e8b9afd03e0224d877"}  # fmt: skip
# frozen Option B modules the adapter / seam / analysis import
FROZEN_IMPORTS = (
    "src/ams/research/dynamic/ledger.py", "src/ams/research/dynamic/models.py",
    "src/ams/research/dynamic/policies.py", "src/ams/research/workload/lineage.py",
    "src/ams/research/workload/sv2.py", "src/ams/research/workload/integration.py",
    "src/ams/research/protocol_v2/analysis.py", "src/ams/eval/callsite.py",
    "src/ams/eval/minja_defence.py", "src/ams/baselines/memlineage.py",
    "src/ams/llm/openrouter_legacy.py",  # rev 2: the agent's OpenRouter layer, unchanged
)  # fmt: skip


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def hashes(root: Path = REPO) -> dict:
    out = {}
    for section, patterns in FILES.items():
        files = {}
        for pattern in patterns:
            for p in sorted(root.glob(pattern)):
                if p.is_file() and "__pycache__" not in p.parts:
                    files[p.relative_to(root).as_posix()] = sha(p)
        out[section] = files
    return out


def vendored(root: Path = REPO) -> dict:
    out = {}
    for name in VENDORED:
        r = subprocess.run(["git", "-C", str(root / "third_party" / name), "rev-parse", "HEAD"],
                           capture_output=True, text=True)  # fmt: skip
        out[name] = r.stdout.strip()
    return out


def option_b(root: Path = REPO) -> dict:
    """The Option B freeze verifies, and every frozen module imported here is unchanged."""
    from ams.research.protocol_v2 import freeze as FZ

    digest_b = FZ.verify(root / P.OPTION_B_MANIFEST, root=root)
    check(digest_b == P.OPTION_B_DIGEST, "Option B digest is not the frozen one")
    saved = json.loads((root / P.OPTION_B_MANIFEST).read_text())["hashes"]["source_files"]
    for f in FROZEN_IMPORTS:
        check(saved.get(f) == sha(root / f), f"frozen module differs from Option B: {f}")
    return {"digest": digest_b, "frozen_imports": {f: saved[f] for f in FROZEN_IMPORTS}}


def body(root: Path = REPO) -> dict:
    return {"version": VERSION, "protocol": json.loads(json.dumps(P.protocol())),
            "hashes": hashes(root), "vendored": vendored(root), "option_b": option_b(root)}  # fmt: skip


def prepare(out: Path, root: Path = REPO) -> dict:
    check(not Path(out).exists(), f"{out} exists; a freeze is never overwritten")
    b = body(root)
    check(b["vendored"] == VENDORED, f"vendored commits differ: {b['vendored']}")
    for section in ("minja_code", "data", "environment"):
        check(b["hashes"][section], f"nothing to hash in {section}")
    saved = {**b, "minja_digest": digest(b)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(saved, indent=1, sort_keys=True) + "\n")
    return saved


def verify(path: Path, root: Path = REPO) -> str:
    saved = json.loads(Path(path).read_text())
    stored = saved.pop("minja_digest", None)
    check(digest(saved) == stored, "MINJA manifest was edited after freezing")
    now = body(root)
    diffs = []
    for section in sorted(set(saved["hashes"]) | set(now["hashes"])):
        old, new = saved["hashes"].get(section, {}), now["hashes"].get(section, {})
        diffs += [f"{section}:{k}" for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]
    check(not diffs, f"MINJA frozen files changed: {diffs[:20]}")
    check(now["vendored"] == saved["vendored"], "vendored commits changed")
    check(now["protocol"] == saved["protocol"], "protocol constants changed")
    check(now["option_b"] == saved["option_b"], "Option B freeze changed")
    return stored
