"""Free stop/resume verification of the LoCoMo v2 paid path with a FAKE, offline API.

Exercises the real paid code path (frozen OpenAIClient + strict BudgetGuard + FixedCeilingGuard +
ResponseCache + locomo_v1.execute.run) through `locomo_v2_supp.runner`, on conv-30 (smallest),
with a fake SDK that never touches the network and answers deterministically from the prompt.

  A  reference: one uninterrupted run
  B  hard kill (SIGKILL mid-conversation) -> resume
  C  graceful STOP file -> resume
  D  network outage (fake transport errors) -> breaker -> probe -> automatic continuation
  E  truncated journal line -> pre-flight repair -> resume
Each scenario must reproduce A's answers and judgements exactly, with no duplicate paid call beyond
the calls in flight at a hard kill, and a consistent ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from locomo_v1 import execute as E
from locomo_v2 import __main__ as CLI
from locomo_v2_supp import runner as RN

ROOT = CLI.OUT / "resume_test"
STATE = Path.home() / ".locomo_v2_resume_test"
CONV = ("conv-30",)
COST = 0.00002


class FakeSDK:
    base_url = "https://openrouter.ai/api/v1/"

    def __init__(self, log: Path, fail_from=None, fail_n=0):
        self.log, self.fail_from, self.fail_n = log, fail_from, fail_n
        self.lock, self.n = threading.Lock(), 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **kw):
        return self

    def _create(self, **kw):
        with self.lock:
            self.n += 1
            n = self.n
            with self.log.open("a") as fh:
                fh.write("1\n")
        if self.fail_from is not None and self.fail_from <= n < self.fail_from + self.fail_n:
            raise ConnectionError("fake network down")
        text = kw["messages"][0]["content"]
        h = hashlib.sha256(text.encode()).hexdigest()
        out = ("CORRECT" if int(h, 16) % 2 else "WRONG") if text.startswith("You are grading") else f"ans-{h[:10]}"
        time.sleep(0.002)
        return SimpleNamespace(
            id=f"gen-{uuid.uuid4().hex[:12]}", model="openai/gpt-4o-mini", error=None,
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=3, cost=COST, is_byok=False),
            choices=[SimpleNamespace(message=SimpleNamespace(content=out), finish_reason="stop")])


def child(name, fail_from=None, fail_n=0, probe_fail_first=0, reviewed=False):
    d = ROOT / name
    calls = STATE / f"{name}_fake_calls.log"
    calls.parent.mkdir(parents=True, exist_ok=True)
    probes = {"n": 0}

    def probe():
        probes["n"] += 1
        return probes["n"] > probe_fail_first

    res = RN.run(d / "run", STATE / name, CLI.BUILD, workers=16, gate=False, convs=CONV,
                 sdk_client=FakeSDK(calls, fail_from, fail_n), probe_fn=probe, wait_s=1, s2_reviewed=reviewed)
    print("RESULT", json.dumps(res), flush=True)


def spawn(name, *extra):
    env = dict(os.environ)
    return subprocess.Popen([sys.executable, "-m", "locomo_v2_supp.resume_test", "child", name, *extra],
                            cwd=CLI.K.REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def outputs(name):
    run = ROOT / name / "run"
    a = {(r["qid"], r["ctx"]): r["prediction"] for r in E._read(run / "answers.jsonl")}
    j = {(r["qid"], r["prediction"]): r["correct"] for r in E._read(run / "judgements.jsonl")}
    return a, j


def ledger(name):
    db = sqlite3.connect(f"file:{STATE / name / 'run' / 'budget_guard.sqlite'}?mode=ro", uri=True)
    cfg = db.execute("SELECT used_nanodollars,held_nanodollars,blocked FROM budget_config").fetchone()
    st = dict(db.execute("SELECT state,COUNT(*) FROM reservations GROUP BY state").fetchall())
    db.close()
    return {"used": int(cfg[0]), "held": int(cfg[1]), "blocked": cfg[2], **st}


def calls(name):
    p = STATE / f"{name}_fake_calls.log"
    return sum(1 for _ in p.open()) if p.exists() else 0


def wait_calls(name, n, proc, timeout=600):
    t = time.time()
    while calls(name) < n and proc.poll() is None and time.time() - t < timeout:
        time.sleep(0.2)


def finish(proc, timeout=1800):
    out, _ = proc.communicate(timeout=timeout)
    line = [x for x in out.splitlines() if x.startswith("RESULT ")]
    return json.loads(line[-1][7:]) if line else {"status": "no_result", "tail": out[-2000:]}


def main():
    shutil.rmtree(ROOT, ignore_errors=True)
    shutil.rmtree(STATE, ignore_errors=True)
    for n in ("A", "B", "C", "D", "D2", "E"):
        (ROOT / n).mkdir(parents=True)
    report = {}

    # A reference
    rA = finish(spawn("A"))
    aA, jA = outputs("A")
    report["A"] = {"result": rA, "answers": len(aA), "judgements": len(jA), "fake_calls": calls("A"), "ledger": ledger("A")}

    # B hard kill mid-run, then resume
    p = spawn("B")
    wait_calls("B", calls("A") // 3, p)
    p.send_signal(signal.SIGKILL)
    p.wait()
    before = {"fake_calls": calls("B"), "ledger": ledger("B"),
              "answers_saved": len(outputs("B")[0])}
    rB = finish(spawn("B"))
    aB, jB = outputs("B")
    lB = ledger("B")
    report["B"] = {"at_kill": before, "result": rB, "identical_to_A": (aB, jB) == (aA, jA),
                   "fake_calls_total": calls("B"), "extra_calls_vs_A": calls("B") - calls("A"), "ledger": lB}

    # C graceful STOP, then resume
    p = spawn("C")
    wait_calls("C", calls("A") // 3, p)
    (ROOT / "C" / "run" / "STOP").write_text("test")
    rC1 = finish(p)
    atstop = ledger("C")
    rC = finish(spawn("C"))
    aC, jC = outputs("C")
    report["C"] = {"first": rC1, "ledger_at_stop": atstop, "result": rC, "identical_to_A": (aC, jC) == (aA, jA),
                   "extra_calls_vs_A": calls("C") - calls("A"), "ledger": ledger("C")}

    # D network outage: calls 3000..3049 fail; probe fails twice then succeeds
    rD = finish(spawn("D", "3000", "50", "2"))
    aD, jD = outputs("D")
    report["D"] = {"result": rD, "identical_to_A": (aD, jD) == (aA, jA), "extra_calls_vs_A": calls("D") - calls("A"),
                   "ledger": ledger("D"), "resume_log": [json.loads(x)["event"] for x in
                                                         (ROOT / "D" / "run" / "resume_log.jsonl").read_text().splitlines()]}

    # D2 long outage (calls 3000..3399 fail: outlasts the frozen 10-attempt retry) -> breaker trips
    rD2a = finish(spawn("D2", "3000", "400", "2"))
    plain = finish(spawn("D2"))  # resume without review: must pause again (S2 needs the owner)
    rD2 = finish(spawn("D2", "reviewed"))  # owner-reviewed resume (network back)
    aD2, jD2 = outputs("D2")
    report["D2"] = {"first": rD2a, "resume_without_review": plain, "result": rD2, "identical_to_A": (aD2, jD2) == (aA, jA), "extra_calls_vs_A": calls("D2") - calls("A"),
                    "ledger": ledger("D2"), "resume_log": [json.loads(x)["event"] for x in
                                                           (ROOT / "D2" / "run" / "resume_log.jsonl").read_text().splitlines()]}

    # E truncated last line (simulates a kill during a journal write), then resume
    shutil.copytree(ROOT / "B" / "run", ROOT / "E" / "run")
    shutil.copytree(STATE / "B", STATE / "E")
    shutil.copy(STATE / "B_fake_calls.log", STATE / "E_fake_calls.log")
    mig = ROOT / "E" / "run" / E.K.GUARD_MIGRATION
    rec = json.loads(mig.read_text())
    rec["live"] = str(STATE / "E" / "run" / "budget_guard.sqlite")
    mig.write_text(json.dumps(rec, indent=1))
    with (ROOT / "E" / "run" / "answers.jsonl").open("a") as fh:
        fh.write('{"qid": "conv-30:1", "ctx": "abc", "predic')
    rE = finish(spawn("E"))
    aE, jE = outputs("E")
    report["E"] = {"result": rE, "identical_to_A": (aE, jE) == (aA, jA),
                   "repairs": sorted(x.name for x in (ROOT / "E" / "run" / "repairs").glob("*")),
                   "new_calls": calls("E") - calls("B")}
    (CLI.OUT / "resume_test_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        a = sys.argv[2:]
        if len(a) == 2 and a[1] == "reviewed":
            child(a[0], reviewed=True)
        else:
            child(a[0], int(a[1]) if len(a) > 1 else None, int(a[2]) if len(a) > 2 else 0, int(a[3]) if len(a) > 3 else 0)
    else:
        main()
