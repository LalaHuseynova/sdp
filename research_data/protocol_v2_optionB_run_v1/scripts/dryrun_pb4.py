#!/usr/bin/env python3
"""P-B4 dry run (revision 10), FREE: the real P-B4 path on real data with no network.

    uv run python research_data/protocol_v2_optionB_run_v1/scripts/dryrun_pb4.py WORK_DIR [GROUP]

1. Clones the real guarded sessions (sessions_rerun3, GPT-4o-mini and published-defence
   ledgers) into WORK_DIR; the originals are only read.
2. Runs pipeline.evaluate exactly as `paid.sh PB4` does (8 Haiku cells, 11 methods,
   BackboneRouter -> Gemini) for one group (default G-T00), with a MOCK transport: every
   GPT-4o-mini call the real runs already paid for must replay from the cloned ledgers; only
   Gemini answers and the GPT judges of those answers reach the mock (cost $0).
3. Checks: (a) no conflict check, MemLineage, A-MemGuard or sanitiser request reaches the
   network (all replayed); (b) every Gemini request has the frozen shape (model, temperature
   0, reasoning disabled, 200 tokens, provider price ceiling); (c) the Gemini journal has the
   same rows as the real Claude Haiku journal for that group, and every field that does not
   depend on the answering model (prompt hash, retrieval exposure, context, audits, stratum)
   is IDENTICAL: same dataset, attacks, retrieval and prompts; only the answer differs.
Revision 11 additions: (d) if the copied Gemini ledger is halted (the P-B4 429 stop), the
owner review is rehearsed ON THE COPY (worst-case booking + audit table, as
review_unknown_rev7.py) and the paid Gemini answers must replay at $0; (e) every 25th new Gemini
request is refused once with HTTP 429 and must be recovered by the same request (no failed row);
the real 2 s Gemini pacing stays on (its time is reported).
Writes WORK_DIR/dryrun_report.json. Never reads .env and never opens the network.
"""

import importlib.util
import json
import shutil
import sqlite3
import sys
import time
from decimal import Decimal
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[3]
RUN = REPO / "research_data/protocol_v2_optionB_run_v1"
sys.path.insert(0, str(REPO / "src"))

from ams.research.dynamic.models import check  # noqa: E402
from ams.research.protocol_v2 import hashseed  # noqa: E402
from ams.research.protocol_v2 import pipeline as PL  # noqa: E402
from ams.research.protocol_v2 import registry as REG  # noqa: E402
from ams.research.protocol_v2.backbone import GEMINI  # noqa: E402
from ams.research.workload import transport as T  # noqa: E402
from ams.research.workload.transport import ConstructionSession  # noqa: E402

T.RATE_LIMIT_WAIT_S = 0  # dry run: no 30 s waits after the simulated 429s

hashseed.require()  # PYTHONHASHSEED=0, as every protocol-v2 run
work = Path(sys.argv[1]).resolve()
group = sys.argv[2] if len(sys.argv) > 2 else "G-T00"
check(not work.exists(), "WORK_DIR must not exist")
check(RUN not in work.parents, "WORK_DIR must be outside the run folder")
spec = importlib.util.spec_from_file_location("cli", REPO / "scripts/run_protocol_v2.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

# 1. clone the real ledgers (read-only source); the Haiku answer scope is not needed
sessions = work / "sessions"
for p in sorted((RUN / "sessions_rerun3").iterdir()):
    if p.name != "v2_backbone_answer":
        shutil.copytree(p, sessions / p.name, ignore=shutil.ignore_patterns("dispatch.lock"))
        # the COPY only: mark it mock so it accepts the offline transport (the guard never
        # lets a live ledger use a mock network); completed calls still replay from it
        with sqlite3.connect(sessions / p.name / "dispatch.sqlite") as db:
            db.execute("UPDATE metadata SET value='mock' WHERE key='transport_mode'")
review = None
gem_copy = sessions / "v2_backbone_gemini"
if gem_copy.exists():  # (d) rehearse the owner review on the COPY of the halted ledger
    with ConstructionSession(gem_copy) as s:
        snap = s.guard.snapshot()
        review = {"blocked_before": snap["blocked"], "paid_answers_before":
                  s.db.execute("SELECT count(*) FROM dispatches WHERE status='completed'")
                  .fetchone()[0]}  # fmt: skip
        if snap["blocked"]:
            review["booked_at_worst_case"] = s.guard.resolve_unknown_at_worst_case(
                "dryrun_review_rev11")
            review["moved_to_audit_table"] = s.supersede_reviewed_failures("dryrun_review_rev11")
        review["blocked_after"] = s.guard.snapshot()["blocked"]
rev9 = json.loads((REPO / "research_data/protocol_v2_freeze_optionB_20261115/"
                   "owner_approval_optionB_rev9.json").read_text())
approval = {"approved_by": "owner", "protocol_v2_digest": "dry-run-" + "0" * 56,
            "caps_usd": {**{k: v for k, v in rev9["caps_usd"].items()
                            if k != "v2_backbone_answer"}, "v2_backbone_gemini": "10.00"},
            "models": {**{k: v for k, v in rev9["models"].items() if k != "v2_backbone_answer"},
                       "v2_backbone_gemini": GEMINI}}

# 2. mock network: Gemini answers and GPT judges only; anything else is recorded as a leak
seen, refused, first = [], [], set()


def handler(request):
    body = json.loads(request.content)
    if body["model"] == GEMINI:  # (e) every 25th new Gemini request: one 429 first
        sig = json.dumps(body["messages"])
        if sig not in first:
            first.add(sig)
            if len(first) % 25 == 0:
                refused.append(sig)
                return httpx.Response(429, json={"error": {"code": 429,
                                                           "message": "dry run: rate limited"}})
    seen.append(body)
    if body["model"] == GEMINI:
        text = "Based on what I remember, I cannot confirm that."
    else:
        text = "NO\nmock judge (dry run)"
    return httpx.Response(200, json={
        "id": f"gen-dry-{len(seen)}", "model": body["model"], "object": "chat.completion",
        "created": 1, "provider": "dry-run",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                  "cost": "0"}})  # fmt: skip


methods = list(PL.MAIN_METHODS)
cells = list(REG.SECOND_BACKBONE)
conditions = cli.conditions_for(cells)
out = work / "gemini"
BUNDLE = REPO / "research_data/controlled_workload_v4_20261108"
STAGE1 = REPO / "research_data/controlled_workload_stage1_test_v4_20261108"
rows, stores, bundle_hash = cli.load(BUNDLE, STAGE1, conditions, [group],
                                     mirror=cli.mirror_for(out))
purposes = PL.required_purposes(methods, "gemini")
with PL.open_paid(sessions, bundle_hash, approval, purposes, transport=httpx.MockTransport(handler),
                  confirmed=True) as live:  # fmt: skip
    from ams.baselines.amemguard import AMemGuard
    from ams.baselines.amemguard_borrowed import LLMSanitiser
    from ams.research.recovery.offline import CHAT_MODEL

    defences = {"randec": cli.randec(), "memlineage": PL.memlineage(live.sensitive),
                "a_memguard": AMemGuard(model=CHAT_MODEL,
                                        client=live.client("v2_published_amemguard")),
                "llm_sanitiser": LLMSanitiser(live.client("v2_published_sanitiser"),
                                              model=CHAT_MODEL)}  # fmt: skip
    before = {p: s.task_spend() for p, s in live.sessions.items()}
    t0 = time.monotonic()
    result = PL.evaluate(rows, stores, live.stage3, out, conditions=conditions, methods=methods,
                         defences=defences, sensitive=live.sensitive)  # fmt: skip
    spend = {p: str(s.task_spend() - before[p]) for p, s in live.sessions.items()}  # this run
    counts = dict(live.stage3.counts)
    elapsed = round(time.monotonic() - t0)
    failed_rows = live.sessions["v2_backbone_gemini"].db.execute(
        "SELECT count(*) FROM dispatches WHERE status!='completed'").fetchone()[0]

# 3. checks
gem = [b for b in seen if b["model"] == GEMINI]
gpt = [b for b in seen if b["model"] != GEMINI]
leaks = [b for b in gpt if b["max_tokens"] != 120]  # only judges (120 tokens) may be new
shape_ok = all(b["temperature"] == 0 and b["max_tokens"] == 200
               and b["reasoning"] == {"enabled": False} and len(b["messages"]) == 1
               and b["provider"]["max_price"] == {"prompt": 0.25, "completion": 1.5, "request": 0}
               and b["provider"]["require_parameters"] is True
               and b["provider"]["allow_fallbacks"] is False for b in gem)  # fmt: skip


def journal(path, where=""):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    q = "SELECT body FROM outcomes" + where
    return {(r["condition"], r["method"], r["probe_id"]): r
            for r in (json.loads(x[0]) for x in db.execute(q))}


ANSWER_FIELDS = {"answer", "finish_reason", "judge", "outcome", "model_call_ids"}
haiku = journal(RUN / "haiku/queries.sqlite", f" WHERE json_extract(body,'$.group_id')='{group}'")
gemini = journal(out / "queries.sqlite")
same_keys = set(haiku) == set(gemini)
diff_fields = {}
for k in set(haiku) & set(gemini):
    for f in set(haiku[k]) | set(gemini[k]):
        if f not in ANSWER_FIELDS and haiku[k].get(f) != gemini[k].get(f):
            diff_fields[f] = diff_fields.get(f, 0) + 1
haiku_prompts = {r["prompt_hash"] for r in haiku.values()}
report = {
    "group": group, "cells": cells, "runtime_conditions": len(conditions), "methods": methods,
    "journal_rows": result["rows"], "haiku_rows_same_group": len(haiku),
    "gemini_requests": len(gem), "gpt_judge_requests": len(gpt) - len(leaks),
    "non_judge_gpt_requests_reaching_network": len(leaks),
    "gemini_request_shape_ok": shape_ok, "router_counts": counts, "spend_usd": spend,
    "same_rows_as_haiku": same_keys,
    "non_answer_fields_differing_from_haiku": diff_fields,
    "same_prompts_as_haiku": {r["prompt_hash"] for r in gemini.values()} == haiku_prompts,
    "review_rehearsal_on_copy": review,
    "simulated_429_refusals": len(refused), "gemini_rows_not_completed": failed_rows,
    "seconds_for_this_group_with_2s_pacing": elapsed,
}
report["PASSED"] = bool(len(leaks) == 0 and shape_ok and same_keys and not diff_fields
                        and report["same_prompts_as_haiku"] and gem
                        and all(Decimal(v) == 0 for v in spend.values())
                        and failed_rows == 0 and len(refused) > 0
                        and (review is None or not review["blocked_after"]))
(work / "dryrun_report.json").write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps(report, indent=1))
sys.exit(0 if report["PASSED"] else 1)
