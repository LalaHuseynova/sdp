"""Free end-to-end test of the supplementary PAID path with a fake offline API (no network, $0).

conv-30 only. A: uninterrupted (defence stage both defences x 4 shapes -> answers -> analysis).
B: STOP during the defence stage -> resume. B must give byte-identical defended contexts and the same
answers as A, with no extra defence call beyond those in flight at the stop.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from locomo_v1 import execute as E
from locomo_v2_supp import published_paid as PP
from locomo_v2_supp import published_supp as PS

ROOT = PS.OUT / "fake_test"
STATE = Path.home() / ".locomo_v2_supp_fake"
CONV = ("conv-30",)


class FakeSDK:
    base_url = "https://openrouter.ai/api/v1/"

    def __init__(self, log: Path):
        self.log, self.lock = log, threading.Lock()
        self.mock = PS.MockDefenceLLM()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **kw):
        return self

    def _create(self, **kw):
        with self.lock, self.log.open("a") as fh:
            fh.write("1\n")
        msgs = kw["messages"]
        text = "\n".join(m["content"] for m in msgs)
        if any(k in text for k in ("impartial auditor", "Reasoning Chain", "Santized Memory Log", "[STATUS]")):
            req = SimpleNamespace(messages=[SimpleNamespace(content=m["content"]) for m in msgs])
            out = self.mock.complete(req).text
        elif text.startswith("You are grading"):
            out = "CORRECT" if int(hashlib.sha256(text.encode()).hexdigest(), 16) % 2 else "WRONG"
        else:
            out = "ans-" + hashlib.sha256(text.encode()).hexdigest()[:10]
        time.sleep(0.002)
        return SimpleNamespace(id=f"gen-{uuid.uuid4().hex[:12]}", model="openai/gpt-4o-mini", error=None,
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=3, cost=0.00002, is_byok=False),
                               choices=[SimpleNamespace(message=SimpleNamespace(content=out), finish_reason="stop")])


def child(name):
    d = ROOT / name
    res = PP.run(run_dir=d / "run", build_dir=d / "build", state=STATE / name, convs=CONV, gate_on=False,
                 sdk_client=FakeSDK(STATE / f"{name}_calls.log"), probe_fn=lambda: True, wait_s=1)
    print("RESULT", json.dumps(res), flush=True)


def spawn(name):
    return subprocess.Popen([sys.executable, "-m", "locomo_v2_supp.published_fake_test", "child", name],
                            cwd=PS.K.REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def finish(p):
    out, _ = p.communicate(timeout=7200)
    r = [x for x in out.splitlines() if x.startswith("RESULT ")]
    return json.loads(r[-1][7:]) if r else {"status": "no_result", "tail": out[-1500:]}


def calls(name):
    p = STATE / f"{name}_calls.log"
    return sum(1 for _ in p.open()) if p.exists() else 0


def jobs(name):
    return gzip.open(ROOT / name / "build" / "conv-30.jobs.jsonl.gz").read()


def main():
    shutil.rmtree(ROOT, ignore_errors=True)
    shutil.rmtree(STATE, ignore_errors=True)
    STATE.mkdir(parents=True)
    rep = {"A": finish(spawn("A"))}
    rep["A_calls"] = calls("A")
    p = spawn("B")
    while calls("B") < rep["A_calls"] // 4 and p.poll() is None:
        time.sleep(0.2)
    (ROOT / "B" / "run").mkdir(parents=True, exist_ok=True)
    (ROOT / "B" / "run" / "STOP").write_text("test")
    rep["B_first"] = finish(p)
    rep["B_calls_at_stop"] = calls("B")
    rep["B_build_exists_after_stop"] = (ROOT / "B" / "build" / "conv-30.jobs.jsonl.gz").exists()
    rep["B"] = finish(spawn("B"))
    rep["B_calls_total"] = calls("B")
    rep["identical_defended_contexts"] = jobs("A") == jobs("B")
    a = {(r["qid"], r["ctx"]): r["prediction"] for r in E._read(ROOT / "A" / "run" / "answers.jsonl")}
    b = {(r["qid"], r["ctx"]): r["prediction"] for r in E._read(ROOT / "B" / "run" / "answers.jsonl")}
    rep["identical_answers"] = a == b and len(a) > 0
    rep["extra_calls_B_vs_A"] = rep["B_calls_total"] - rep["A_calls"]
    from locomo_v2_supp import supp_baselines_analysis as SA

    res = SA.analyse(ROOT / "A" / "build", ROOT / "A" / "run", CONV)
    rep["analysis_rows"] = len(res["table"])
    rep["analysis_has_supp_arms"] = all(f"1s|{x}" in res["table"] and res["table"][f"1s|{x}"] for x in ("llm_sanitiser", "a_memguard"))
    (PS.OUT / "fake_test_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "child":
        child(sys.argv[2])
    else:
        main()
