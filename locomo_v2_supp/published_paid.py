"""Paid path of the SUPPLEMENTARY published-baseline evaluation (LLM sanitiser, A-MemGuard).

Refuses to run without `supp_published/owner_approval_supp.json` naming the supplementary manifest
digest (note + code) and the frozen LoCoMo v2 digest. Two separate strict budget guards (defence
calls; answers + judges), both on WSL ext4, never the v2 ledger. Safe pause/resume: per-conversation
defence segments (every completed response is cached; a rerun replays at $0), the attempt-level
circuit breaker and STOP file of `locomo_v2_supp.runner`, then the answer stage through the verified
`runner.run` (its own STOP / breaker / S2 review). The answer cache is seeded from the frozen run's
cache, so contexts the defences leave unchanged cost $0.

  python -m locomo_v2_supp.published_paid manifest | status | stop | run
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from locomo_v1 import execute as E
from locomo_v2 import __main__ as CLI
from locomo_v2 import config as K
from locomo_v2_supp import published_supp as PS
from locomo_v2_supp import runner as RN

ROOT = PS.OUT
RUN = ROOT / "run_supp"
BUILD = ROOT / "build"
STATE = Path.home() / ".locomo_v2_supp_state"
APPROVAL = ROOT / "owner_approval_supp.json"
MANIFEST = ROOT / "supp_manifest.json"
NOTE = K.REPO / "reports" / "LOCOMO_V2_SUPP_PUBLISHED_BASELINES_NOTE.md"
CODE = ["locomo_v2_supp/published_supp.py", "locomo_v2_supp/published_paid.py", "locomo_v2_supp/runner.py",
        "locomo_v2_supp/supp_baselines_analysis.py", "reports/LOCOMO_V2_SUPP_PUBLISHED_BASELINES_NOTE.md",
        "src/ams/baselines/amemguard.py", "src/ams/baselines/amemguard_borrowed.py",
        "prompts/sanitiser_audit/v1.txt", "prompts/sanitiser_clean/v1.txt", "prompts/sanitiser_system/v1.txt"]


def files():
    return {f: hashlib.sha256((K.REPO / f).read_bytes()).hexdigest() for f in CODE}


def manifest():
    fz = json.loads((CLI.FREEZE / "freeze_manifest.json").read_text())["digest"]
    h = files()
    m = {"frozen_v2_digest": fz, "files": h, "digest": hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest(),
         "utc": datetime.now(UTC).isoformat(timespec="seconds")}
    MANIFEST.write_text(json.dumps(m, indent=1))
    return m


def gate():
    if not APPROVAL.exists() or not MANIFEST.exists():
        sys.exit("refused: no supplementary approval / manifest")
    m, a = json.loads(MANIFEST.read_text()), json.loads(APPROVAL.read_text())
    ref = json.loads((CLI.FREEZE / "freeze_manifest.json").read_text())
    if CLI.freeze_files() != ref["files"]:
        sys.exit("refused: frozen LoCoMo v2 files changed")
    if files() != m["files"] or a.get("digest") != m["digest"] or a.get("frozen_v2_digest") != ref["digest"]:
        sys.exit("refused: approval does not name the verified supplementary manifest and frozen digest")
    return a


def seed_answer_cache(run: Path, frozen_run: Path = PS.FROZEN_RUN):
    from ams.llm import ResponseCache

    run.mkdir(parents=True, exist_ok=True)
    tgt = run / "response_cache.sqlite"
    ResponseCache(tgt)
    db = sqlite3.connect(f"file:{tgt}", uri=True)
    db.execute("ATTACH DATABASE ? AS src", (f"file:{frozen_run / 'response_cache.sqlite'}?mode=ro&immutable=1",))
    db.execute("INSERT OR IGNORE INTO responses SELECT * FROM src.responses")  # rows copied, never read
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    db.close()
    return n


def defence_client(run: Path, state: Path, cap: str, breaker, sdk_client=None):
    from ams.llm import ResponseCache
    from ams.llm.budget import BudgetGuard

    if sdk_client is None:
        E._env_key()
    state.mkdir(parents=True, exist_ok=True)
    guard = E.FixedCeilingGuard(BudgetGuard(state / "defence_guard.sqlite", limit_usd=cap))
    client = E._strict_client(guard, ResponseCache(run / "defence_cache.sqlite"), "supp_defence", sdk_client)
    return breaker.wrap(client), guard


def run(run_dir=RUN, build_dir=BUILD, state=STATE, convs=RN.ORDER, sdk_client=None, gate_on=True,
        defence_cap=None, answer_cap=None, probe_fn=RN.probe, wait_s=60, max_auto=RN.MAX_AUTO_RESUMES) -> dict:
    appr = gate() if gate_on else {"defence_cap_usd": defence_cap or "14", "answer_cap_usd": answer_cap or "6"}
    run_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    stop = run_dir / "STOP"
    stop.unlink(missing_ok=True)
    if not (run_dir / "response_cache.sqlite").exists():
        RN.log(run_dir, event="answer_cache_seeded", rows=seed_answer_cache(run_dir))
    br = RN.Breaker(stop)
    client, guard = defence_client(run_dir, state, appr["defence_cap_usd"], br, sdk_client)
    auto = 0
    for cid in convs:  # defence stage, one conversation per segment; done = its build files exist
        if (build_dir / f"{cid}.jobs.jsonl.gz").exists():
            continue
        while True:
            br.reason = None
            try:
                PS.build(client, build_dir, convs=(cid,))
                RN.log(run_dir, event="defence_conversation_complete", conv=cid)
                break
            except Exception as exc:  # noqa: BLE001  (Paused, API error): nothing partial is written
                if br.reason == "stop_requested" or stop.exists():
                    stop.unlink(missing_ok=True)
                    RN.log(run_dir, event="paused_by_user", stage="defence", conv=cid)
                    return {"status": "paused_by_user", "stage": "defence"}
                auto += 1
                RN.log(run_dir, event="defence_breaker_tripped", conv=cid, error=type(exc).__name__, attempt=auto)
                if auto > max_auto:
                    return {"status": "paused_api_errors", "stage": "defence"}
                while not probe_fn():
                    time.sleep(wait_s)
    res = RN.run(run_dir, state, build_dir, gate=False, convs=convs, cap=appr["answer_cap_usd"], sdk_client=sdk_client,
                 probe_fn=probe_fn, wait_s=wait_s, max_auto=max_auto)
    return {"status": res["status"], "stage": "answers", **res}


def status(run_dir=RUN, state=STATE):
    out = {"defence_built": sorted(p.name.split(".")[0] for p in BUILD.glob("*.jobs.jsonl.gz")) if BUILD.exists() else []}
    led = state / "defence_guard.sqlite"
    if led.exists():
        db = sqlite3.connect(f"file:{led}?mode=ro", uri=True)
        cfg = db.execute("SELECT used_nanodollars,held_nanodollars,blocked FROM budget_config").fetchone()
        out["defence_ledger"] = {"spent_usd": int(cfg[0]) / 1e9, "held_usd": int(cfg[1]) / 1e9, "blocked": bool(cfg[2])}
        db.close()
    if run_dir.exists():
        out["answers"] = RN.status(run_dir, state, BUILD) if BUILD.exists() and any(BUILD.glob("*.jobs.jsonl.gz")) else None
    return out


def main(argv=None):
    cmd = (argv or sys.argv[1:])[0]
    if cmd == "manifest":
        print(json.dumps(manifest(), indent=1))
    elif cmd == "status":
        print(json.dumps(status(), indent=1, default=str))
    elif cmd == "stop":
        RUN.mkdir(parents=True, exist_ok=True)
        (RUN / "STOP").write_text(datetime.now(UTC).isoformat())
        print("STOP requested")
    elif cmd == "run":
        print(json.dumps(run()))
    else:
        sys.exit("manifest | status | stop | run")


if __name__ == "__main__":
    main()
