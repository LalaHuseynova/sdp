"""LoCoMo v2 resumable runner: EXECUTION LEVEL ONLY (reports/LOCOMO_V2_EXECUTION_ADDENDUM.md).

It drives the frozen engine (`locomo_v1.execute.run`, the same paid path the frozen `locomo_v2`
CLI uses) one conversation at a time and adds, from outside the frozen files:
  * pre-flight repair: a truncated last line of a run journal (hard kill during a write) is moved
    to run/repairs/ (bytes kept), never parsed as data;
  * a graceful STOP file: new calls are refused BEFORE any budget reservation; in-flight calls
    finish and are saved, so a requested stop leaves no pending reservation;
  * a circuit breaker at HTTP-attempt level: the first failed attempt pauses dispatch; every later
    attempt (other workers and the frozen client's own retries) is refused locally before any
    reservation ($0, no hold), the runner waits for a free connectivity probe
    and continues (at most MAX_AUTO_RESUMES times per invocation);
  * S2 (protocol §11) per conversation over REAL HTTP attempts: >2% failed -> pause with
    'S2_review_required'; continuing needs --owner-reviewed-s2 (the owner's decision, logged).
Prompts, models, decoding, jobs, metrics and analysis are untouched; answers come only from the
frozen LoCoMoQA through the strict guard and the response cache (a cache hit costs $0 and never
reserves).

  python -m locomo_v2_supp.runner run [--only conv-48] [--workers 16]
  python -m locomo_v2_supp.runner status
  python -m locomo_v2_supp.runner stop
  python -m locomo_v2_supp.runner seed-cache        # only if the approval says reuse_cache: yes
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import locomo_v1.config as V1
from locomo_v1 import build as B1
from locomo_v1 import execute as E
from locomo_v2 import __main__ as CLI
from locomo_v2 import config as K

ORDER = ("conv-48",) + tuple(c for c in K.CONVS if c != "conv-48")  # dev canary first
MAX_AUTO_RESUMES = 5
PROBE_URL = "https://openrouter.ai/api/v1/models"
JOURNALS = ("answers.jsonl", "judgements.jsonl", "progress.jsonl", "errors.jsonl")


class Paused(RuntimeError):
    """Raised locally, before any reservation: no API call, no cost, no hold."""


class Breaker:
    def __init__(self, stop_file: Path):
        self.stop_file, self.reason, self.lock = stop_file, None, threading.Lock()
        self.dispatched = self.failed = 0

    def trip(self, reason):
        with self.lock:
            self.reason = self.reason or reason

    def wrap(self, client):
        """Outer (per request, before the cache): a requested STOP or an earlier trip refuses the
        request locally. Inner (per HTTP attempt, inside the frozen retry loop and before the
        frozen client's reservation): a tripped breaker refuses the attempt, so neither a retry
        nor another worker can create a new hold; the first failed attempt trips it."""
        br = self
        inner = client._inner

        class _Inner:
            def __getattr__(self, item):
                return getattr(inner, item)

            def complete(self, request):
                if br.reason is not None:
                    raise Paused(br.reason)
                with br.lock:
                    br.dispatched += 1
                try:
                    return inner.complete(request)
                except Exception:
                    with br.lock:
                        br.failed += 1
                    br.trip("api_error")
                    raise

        client._inner = _Inner()

        class _C:
            def __getattr__(self, item):
                return getattr(client, item)

            def complete(self, request):
                if br.reason is None and br.stop_file.exists():
                    br.trip("stop_requested")
                if br.reason is not None:
                    raise Paused(br.reason)
                return client.complete(request)

        return _C()


def log(run: Path, **rec):
    rec = {"utc": datetime.now(UTC).isoformat(timespec="seconds"), **rec}
    with (run / "resume_log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)


def repair(run: Path) -> list:
    """Move a truncated trailing line (no newline, or not JSON) to run/repairs/; keep the bytes."""
    out = []
    for name in JOURNALS:
        p = run / name
        if not p.exists() or p.stat().st_size == 0:
            continue
        data = p.read_bytes()
        cut = len(data)
        if not data.endswith(b"\n"):
            cut = data.rfind(b"\n") + 1
        else:
            last = data[: -1].rfind(b"\n") + 1
            try:
                json.loads(data[last:-1])
            except ValueError:
                cut = last
        if cut < len(data):
            (run / "repairs").mkdir(exist_ok=True)
            q = run / "repairs" / f"{name}.{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.partial"
            q.write_bytes(data[cut:])
            with p.open("r+b") as fh:
                fh.truncate(cut)
            out.append({"file": name, "moved_bytes": len(data) - cut, "to": str(q.name)})
    return out


def check_gate(run: Path):
    appr, man = CLI.FREEZE / "owner_approval.json", CLI.FREEZE / "freeze_manifest.json"
    if not appr.exists() or not man.exists():
        sys.exit("refused: no owner approval / freeze manifest (protocol §11)")
    ref = json.loads(man.read_text())
    if json.loads(appr.read_text()).get("digest") != ref["digest"] or CLI.freeze_files() != ref["files"]:
        sys.exit("refused: approval does not name the verified freeze digest")
    return json.loads(appr.read_text())


def probe(timeout=10) -> bool:
    try:
        with urllib.request.urlopen(PROBE_URL, timeout=timeout) as r:  # public list, no key, $0
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def run(run: Path, state: Path, build: Path, only=None, workers=16, sdk_client=None, gate=True,
        probe_fn=probe, wait_s=60, max_auto=MAX_AUTO_RESUMES, convs=ORDER, s2_reviewed=False, cap=None) -> dict:
    run.mkdir(parents=True, exist_ok=True)
    if gate:
        check_gate(run)
    stop_file = run / "STOP"
    if stop_file.exists():
        stop_file.unlink()
        log(run, event="stale_stop_file_removed")
    fixed = repair(run)
    if fixed:
        log(run, event="repaired_truncated_journal", items=fixed)
    V1.PROTOCOL_ID, V1.CAP_USD = K.PROTOCOL_ID, (cap or K.CAP_USD)
    breaker = Breaker(stop_file)
    orig = E.paid_qa

    def paid_qa(run_dir, prompts, state_dir=V1.STATE_DIR, sdk=None):
        qa, guard = orig(run_dir, prompts, state_dir, sdk)
        qa.agent, qa.judge = breaker.wrap(qa.agent), breaker.wrap(qa.judge)
        return qa, guard

    E.paid_qa = paid_qa
    real = {"dispatched": 0, "failed": 0}
    conv_real = {"dispatched": 0, "failed": 0}  # S2 is per conversation (as the frozen engine), real attempts only
    auto = 0
    marker = run / "S2_REVIEW_REQUIRED"
    if marker.exists():
        if not s2_reviewed:
            log(run, event="refused_s2_review_pending")
            return {"status": "S2_review_required", "detail": "rerun with --owner-reviewed-s2 after review"}
        marker.unlink()
        log(run, event="owner_reviewed_s2_override")
    try:
        todo = [c for c in convs if not only or c in only]
        i = 0
        log(run, event="segment_start", convs=todo, protocol=K.PROTOCOL_ID, cap=K.CAP_USD)
        while i < len(todo):
            cid = todo[i]
            breaker.reason = None
            res = E.run(build, run, "paid", K.DRAWS, workers=workers, convs=(cid,), state_dir=state,
                        sdk_client=sdk_client)
            for d in (real, conv_real):
                d["dispatched"] += breaker.dispatched
                d["failed"] += breaker.failed
            breaker.dispatched = breaker.failed = 0
            rate = conv_real["failed"] / conv_real["dispatched"] if conv_real["dispatched"] else 0.0
            if rate > V1.MAX_ERROR_RATE and conv_real["dispatched"] >= 200:
                marker.write_text(json.dumps({"conv": cid, "conversation": conv_real}))
                log(run, event="S2_review_required", conv=cid, conversation=conv_real, **real)
                return {"status": "S2_review_required", **real}
            if breaker.reason == "stop_requested":
                stop_file.unlink(missing_ok=True)
                log(run, event="paused_by_user", conv=cid, **real)
                return {"status": "paused_by_user", **real}
            if breaker.reason == "api_error" or res.get("stopped"):
                if auto >= max_auto:
                    log(run, event="paused_api_errors", conv=cid, auto_resumes=auto, **real)
                    return {"status": "paused_api_errors", **real}
                auto += 1
                log(run, event="breaker_tripped_waiting", conv=cid, attempt=auto)
                while not probe_fn():
                    time.sleep(wait_s)
                    if stop_file.exists():
                        stop_file.unlink()
                        log(run, event="paused_by_user_while_offline", conv=cid)
                        return {"status": "paused_by_user", **real}
                continue  # same conversation again: answered keys are skipped, cached ones are $0
            conv_real = {"dispatched": 0, "failed": 0}
            log(run, event="conversation_complete", conv=cid, **{k: res.get(k) for k in
                                                                 ("selected_keys", "missing_answers", "missing_judgements")})
            i += 1
        log(run, event="all_complete", **real)
        return {"status": "complete", **real}
    finally:
        E.paid_qa = orig


def status(run: Path, state: Path, build: Path) -> dict:
    out = {"conversations": {}}
    done = E._answered(run) if run.exists() else set()  # keys only, never predictions
    for cid in K.CONVS:
        sel = {(j["qid"], j["ctx"]) for j in B1.load_jobs(build, cid) if E.selected(j, K.DRAWS)}
        out["conversations"][cid] = f"{len(sel & done)}/{len(sel)} answered"
    live = state / run.name / "budget_guard.sqlite"
    if live.exists():
        db = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
        try:
            cfg = db.execute("SELECT used_nanodollars,held_nanodollars,blocked,blocked_reason FROM budget_config").fetchone()
            st = dict(db.execute("SELECT state,COUNT(*) FROM reservations GROUP BY state").fetchall())
        finally:
            db.close()
        out["ledger"] = {"spent_usd": int(cfg[0]) / 1e9, "held_usd": int(cfg[1]) / 1e9, "blocked": bool(cfg[2]),
                         "blocked_reason": cfg[3], "reservations": st, "cap_usd": K.CAP_USD}
    cache = run / "response_cache.sqlite"
    if cache.exists():
        db = sqlite3.connect(f"file:{cache}?mode=ro", uri=True)
        try:
            out["cache_rows"] = db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        finally:
            db.close()
    out["stop_file_present"] = (run / "STOP").exists()
    return out


def seed_cache(run: Path):
    appr = check_gate(run)
    if str(appr.get("reuse_v1_1_response_cache", "")).lower() != "yes":
        sys.exit("refused: the approval does not allow cache reuse")
    from ams.llm import ResponseCache

    run.mkdir(parents=True, exist_ok=True)
    target = run / "response_cache.sqlite"
    ResponseCache(target)  # creates the frozen schema
    db = sqlite3.connect(f"file:{target}", uri=True)  # URI mode, so the read-only ATTACH URI is honoured
    n0 = db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    from locomo_v2_supp.readiness import CACHES

    for name, src in CACHES.items():
        db.execute("ATTACH DATABASE ? AS src", (f"file:{src}?mode=ro&immutable=1",))
        db.execute("INSERT OR IGNORE INTO responses SELECT * FROM src.responses")  # rows copied, never read
        db.commit()
        db.execute("DETACH DATABASE src")
    n1 = db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    db.close()
    log(run, event="cache_seeded", rows_before=n0, rows_after=n1, sources=list(CACHES))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "status", "stop", "seed-cache"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--owner-reviewed-s2", action="store_true",
                    help="continue after an S2 pause; only after the owner reviewed the failed calls")
    a = ap.parse_args(argv)
    rd, state, build = CLI.OUT / "run", CLI.STATE, CLI.BUILD
    if a.cmd == "run":
        print(json.dumps(run(rd, state, build, only=a.only, workers=a.workers, s2_reviewed=a.owner_reviewed_s2)))
    elif a.cmd == "status":
        print(json.dumps(status(rd, state, build), indent=1))
    elif a.cmd == "stop":
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "STOP").write_text(datetime.now(UTC).isoformat())
        print("STOP requested: new calls are refused before reservation; in-flight calls finish and are saved.")
    else:
        seed_cache(rd)


if __name__ == "__main__":
    main()
