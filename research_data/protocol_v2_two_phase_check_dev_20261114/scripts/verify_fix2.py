"""Fix 2 (three steps) on REAL dev data, free and offline: the original paid path vs the
three steps, every row compared. Conflict replies: the real dev-ledger replies where the
request was answered before (GPT-4o-mini, guarded ledgers), else a deterministic stand-in
(half 'contradict'); answers/judges: PromptAwareMock. No network, no paid call."""
import json, sqlite3, sys, time, zlib
from dataclasses import asdict, replace
from pathlib import Path
from common_dev import REPO, load, journal
from ams.research.protocol_v2 import pipeline as PL, two_phase as TP
from ams.research.recovery.offline import no_network
from ams.research.workload.mock import PromptAwareMock
from ams.research.workload.transport import evaluation_stage
import run_protocol_v2 as RP
FORCE = len(sys.argv) > 2 and sys.argv[2] == "--all-contradict"
out = Path(sys.argv[1]); assert not out.exists(); out.mkdir(parents=True)
real = {}
for led in ("controlled_workload_session_v2_20261108", "controlled_workload_session_v3_20261112"):
    db = sqlite3.connect(f"file:{REPO / 'research_data' / led / 'dispatch.sqlite'}?mode=ro", uri=True)
    for key, res in db.execute("SELECT request_key,result FROM dispatches WHERE stage='workload_conflict' AND status='completed'"):
        r = json.loads(res)["response"]
        if r: real[key] = r
class DevSession:
    def __init__(self): self.mock, self.sent, self.used = PromptAwareMock(), set(), {"real": set(), "standin": set()}
    def dispatch(self, stage, request):
        s = evaluation_stage(stage, request); key = request.cache_key("openrouter")
        cid = s + "_" + key[:24]; self.sent.add((s, key))
        if s == "workload_conflict":
            if FORCE:  # stress variant: every conflict check contradicts
                self.used["standin"].add(key)
                return cid, {"response": asdict(replace(self.mock.complete(request), text="contradict"))}
            if key in real:
                self.used["real"].add(key); return cid, {"response": real[key]}
            self.used["standin"].add(key)
            r = self.mock.complete(request)
            body = request.messages[-1].content
            r = replace(r, text="contradict" if zlib.crc32(body.encode()) % 2 == 0 else "compatible")
            return cid, {"response": asdict(r)}
        return cid, {"response": asdict(self.mock.complete(request))}
class Keep:
    def filter(self, q, mems):
        from ams.baselines.base import DefenceResult; return DefenceResult(kept=tuple(mems), flagged=())
class DropFirst:
    def filter(self, q, mems):
        from ams.baselines.base import DefenceResult; m = tuple(mems); return DefenceResult(kept=m[1:], flagged=m[:1])
sens = lambda q: "remember" in q.lower()
methods = PL.MAIN_METHODS + PL.APPENDIX_METHODS
res = {}
with no_network():
    rows, store, conds = load(out)
    defs = lambda: {"randec": RP.randec(), "a_memguard": Keep(), "llm_sanitiser": DropFirst(), "memlineage": PL.memlineage(sens)}
    t0 = time.monotonic(); orig = DevSession()
    PL.evaluate(rows, [store], orig, out / "original", conditions=conds, methods=methods, defences=defs(), sensitive=sens)
    res["original_seconds"] = time.monotonic() - t0
    t0 = time.monotonic(); rec = TP.ConflictRecorder()
    PL.evaluate(rows, [store], rec, out / "step1_precompute", conditions=conds, methods=TP.CONTEXT_METHODS, answer=False)
    TP.save_requests(out / "step1_precompute" / TP.REQUESTS, rec)
    s1 = DevSession(); replies = TP.send_conflicts(TP.load_requests([out / "step1_precompute" / TP.REQUESTS]), s1)
    TP.save_replies(out / TP.REPLIES, replies); res["step1_seconds"] = time.monotonic() - t0
    t0 = time.monotonic()
    b = TP.build_contexts(rows, [store], TP.load_replies(out / TP.REPLIES), out / "step2_contexts", conditions=conds, inputs={"dev": "G-D00"})
    res["step2_seconds"] = time.monotonic() - t0
    t0 = time.monotonic(); s3 = DevSession(); ctx = TP.Contexts([out / "step2_contexts"], inputs={"dev": "G-D00"})
    PL.evaluate(rows, [store], s3, out / "step3_paid", conditions=conds, methods=methods, defences=defs(), sensitive=sens, contexts=ctx)
    res["step3_seconds"] = time.monotonic() - t0
a, c = journal(out / "original"), journal(out / "step3_paid")
res.update(all_contradict=FORCE, conditions=len(conds), methods=len(methods), rows=len(a), identical=(a == c),
           differing=sum(x != y for x, y in zip(a, c)) + abs(len(a) - len(c)),
           same_requests_sent=(orig.sent == s1.sent | s3.sent),
           distinct_conflict_checks=len(replies),
           conflict_replies_real=len(orig.used["real"]), conflict_replies_standin=len(orig.used["standin"]),
           contradict_replies=sum("contradict" in r["response"]["text"].lower() for r in replies),
           contexts_with_contested_label=ctx.contested_prompts(),
           rows_with_conflict_calls=sum(len(r["model_call_ids"]) > 1 for _, r in a))
(out / "verification.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))
