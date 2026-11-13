"""Compact durable query journal; restart replays saved calls, never whole vector copies."""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.core.env import load_env
from ams.core.lattice import coarsen
from ams.eval.judge import MemoryJudge
from ams.llm.types import ChatRequest, Message
from ams.research import comparison
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.models import canonical, check, digest, parse_event
from ams.research.execution.session import new_json
from ams.research.retrieval import RetrievalContext
from ams.research.sequential.clients import request_from, response_from
from ams.research.sequential.state import RuntimeState, graph_dump

from .preparation import BASIS, read, verify
from .transport import ProvisionalSession


class BoundClient:
    def __init__(self, session, stage):
        self.session, self.stage, self.calls = session, stage, []

    def complete(self, request):
        call_id, result = self.session.dispatch(self.stage, request)
        self.calls.append(call_id)
        return response_from("chat", result["response"])


class Journal:
    def __init__(self, root, scope):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(root / "queries.sqlite", isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS outcomes("
            "key TEXT PRIMARY KEY,body TEXT NOT NULL,hash TEXT NOT NULL);"
        )
        old = self.db.execute("SELECT value FROM metadata WHERE key='scope'").fetchone()
        check(old is None or old[0] == scope, "Cannot reuse another experiment journal")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('scope',?)", (scope,))
        check(
            self.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "Corrupt experiment journal",
        )

    def commit(self, key, value):
        text = canonical(value)
        row = self.db.execute("SELECT body,hash FROM outcomes WHERE key=?", (key,)).fetchone()
        if row:
            check(row == (text, digest(value)), "Restart replay diverged from saved query outcome")
        else:
            self.db.execute("INSERT INTO outcomes VALUES (?,?,?)", (key, text, digest(value)))

    def rows(self):
        rows = []
        for text, h in self.db.execute("SELECT body,hash FROM outcomes ORDER BY rowid"):
            value = json.loads(text)
            check(digest(value) == h, "Saved outcome modified")
            rows.append(value)
        return rows


def resolve_models(state, session):
    references = []
    for client in state.clients:

        def resolve(record, lookup, client=client):
            if record["kind"] != "chat" or record["request"]["max_tokens"] not in {6, 200}:
                result = lookup()
                check(result["error"] is None, "Frozen classifier/embedding miss; no API fallback")
                return result
            request = request_from("chat", record["request"])
            stage = "answer" if request.max_tokens == 200 else "conflict"
            call_id, result = session.dispatch(stage, request)
            # A chosen physical reply is frozen into the replay table. Physical
            # charges belong to the session, not to every replay consumer.
            client.chats[record["request_key"]] = result["response"]
            references.append(call_id)
            return lookup()

        client.resolver = resolve
    return references


def mutation_hash(state):
    use = state.memory.use_type
    return digest(
        {
            "graphs": {k: graph_dump(g) for k, g in state.memory._graphs.items()},
            "classifier_cache": use._cache,
            "classifier_subjects": use._subjects,
            "classifier_unparsed": use.n_unparsed,
            "evidence": state.evidence.revision,
        }
    )


def answer_query(state, session_id, query, use_id, references):
    """Runtime receives public query/use values, never evaluator dictionaries."""
    context = RetrievalContext(state.evidence, state.access, use_id, "user", "read")
    start = len(references)
    outcome = state.reader().retrieve_with_trace(
        session_id=session_id, query=query, context=context, k=4, principal="user"
    )
    body = "\n".join(f"- {e.text}" for e in outcome.retrieval.entries) or "(nothing)"
    prompt = state.memory.prompts.get("answer_typed", "v2").render(
        query=query, memory=body, required=outcome.retrieval.required or "description"
    )
    response = state.answer_client.complete(
        ChatRequest((Message("user", prompt),), state.answer_model, temperature=0, max_tokens=200)
    )
    return {
        "answer": asdict(response),
        "retrieval": asdict(outcome),
        "model_call_ids": references[start:],
        "after_state_hash": mutation_hash(state),
    }


def observation(cell, episode, q, arm, answer, verdict):
    transfer = arm in "RCMS" and arm != "static"
    return {
        "episode_id": cell["episode_id"],
        "probe_id": q["query_id"],
        "arm": arm,
        "model": "openai/gpt-4o-mini",
        "question_hash": digest(q["text"]),
        "reference_hash": digest(q["expected_memory"]),
        "memory_input_hash": None if arm == "no_memory" else cell["memory_input_hash"],
        "initial_memory_hash": None if arm == "no_memory" else episode["initial_memory_hash"],
        "policy_hash": Policy(arm).fingerprint if transfer else None,
        "available_feedback_hash": cell["feedback_hash"] if transfer else None,
        "audit_tickets": 5 if transfer else 0,
        "equivalent_verification": episode["equivalent_verification"]
        if transfer
        else {"calls": 0, "input_tokens": 0, "output_tokens": 0, "usd": "0"},
        "answer_status": "answered",
        "judge_status": "complete",
        "outcome": verdict["hit"],
        "answer_hash": digest(answer),
        "judge_hash": digest(verdict),
    }


def run(plan, out, *, mock=None):
    cfg, spec = verify(plan)
    journal = Journal(out, digest([cfg, spec]))
    try:
        with ProvisionalSession(Path(cfg["session_directory"])) as session:
            if mock is None:
                load_env()
                key = os.environ.get("OPENROUTER_API_KEY")
                check(bool(key), "Missing OpenRouter credential")
                session.arm_provisional(plan, key)
            else:
                session.arm_provisional_mock(plan, mock)
            before = session.summary()
            for cell in spec["cells"]:
                eid = cell["episode_id"]
                episode = read(plan / "private" / (eid + ".json"))
                with gzip.open(plan / "private" / (eid + ".json.gz"), "rt") as stream:
                    snapshot = json.load(stream)
                judge_client = BoundClient(session, "judge_answer")
                judge = MemoryJudge(judge_client, model="openai/gpt-4o-mini")
                entry_client = BoundClient(session, "judge_entry")
                entry_judge = MemoryJudge(
                    entry_client, model="openai/gpt-4o-mini", entry_version="v2"
                )
                write_diagnostics = [
                    {
                        "input_id": w["input_id"],
                        "verdict": asdict(
                            entry_judge.judge_entry(w["expected_memory"], w["entries"])
                        ),
                    }
                    for w in episode.get("write_diagnostics", [])
                ]
                for arm in ["static", "R", "C", "M", "S"]:
                    state = RuntimeState.load(snapshot)
                    state.policy = Policy("R" if arm == "static" else arm)
                    state.effects_enabled = arm != "static"
                    if arm != "static":
                        state.evidence = EvidenceSnapshot(
                            state.evidence.config,
                            (*state.evidence.events, *(parse_event(a) for a in episode["audits"])),
                            5,
                        )
                        state.clock = 5
                    state.validate()
                    references = resolve_models(state, session)
                    for q in episode["queries"]:
                        value = answer_query(
                            state, episode["session_id"], q["text"], q["use_id"], references
                        )
                        judge_start = len(judge_client.calls)
                        verdict = asdict(
                            judge.judge_answer(
                                q["text"], q["expected_memory"], value["answer"]["text"].strip()
                            )
                        )
                        obs = observation(cell, episode, q, arm, value["answer"], verdict)
                        retrieval_verdict = (
                            asdict(
                                entry_judge.judge_entry(
                                    q["expected_memory"],
                                    [e["text"] for e in value["retrieval"]["retrieval"]["entries"]],
                                )
                            )
                            if q["metric"] == "attack"
                            else None
                        )
                        journal.commit(
                            digest([eid, arm, q["query_id"]]),
                            {
                                "observation": obs,
                                "actual": value,
                                "judge": verdict,
                                "retrieved_entry_verdict": retrieval_verdict,
                                "written_entry_diagnostics": write_diagnostics,
                                "judge_call_id": judge_client.calls[-1]
                                if len(judge_client.calls) > judge_start
                                else None,
                            },
                        )
                    print(
                        f"Completed {cell['scenario']} {arm}: {len(episode['queries'])} questions",
                        flush=True,
                    )
                # Empty-memory controls use only the query classifier, no source text.
                state = RuntimeState.load(snapshot)
                control = BoundClient(session, "no_memory_answer")
                for q in episode["queries"]:
                    required = coarsen(
                        state.memory.use_type.required(q["text"]), state.memory.granularity
                    ).name.lower()
                    prompt = state.memory.prompts.get("answer_typed", "v2").render(
                        query=q["text"], memory="(nothing)", required=required
                    )
                    response = control.complete(
                        ChatRequest(
                            (Message("user", prompt),),
                            state.answer_model,
                            temperature=0,
                            max_tokens=200,
                        )
                    )
                    judge_start = len(judge_client.calls)
                    verdict = asdict(
                        judge.judge_answer(q["text"], q["expected_memory"], response.text.strip())
                    )
                    obs = observation(cell, episode, q, "no_memory", asdict(response), verdict)
                    journal.commit(
                        digest([eid, "no_memory", q["query_id"]]),
                        {
                            "observation": obs,
                            "actual": {
                                "answer": asdict(response),
                                "model_call_ids": [control.calls[-1]],
                            },
                            "judge": verdict,
                            "judge_call_id": judge_client.calls[-1]
                            if len(judge_client.calls) > judge_start
                            else None,
                        },
                    )
            after = session.summary()
            rows = journal.rows()
            result = comparison.analyse(spec, [r["observation"] for r in rows])
            result["feedback_caveat"] = BASIS
            result["human_validation"] = "pending; source-grounded QA unavailable"
            result["refusal_annotation"] = (
                "not performed; answered means a generated response, not usefulness"
            )
            result["empty_answer_events"] = sum(
                not r["actual"]["answer"]["text"].strip() for r in rows
            )
            result["length_finish_events"] = sum(
                r["actual"]["answer"]["raw_finish_reason"] in {"length", "max_tokens"} for r in rows
            )
            charges = {
                "project_used_usd": str(
                    Decimal(after["budget"]["used_nanodollars"]) / 1_000_000_000
                ),
                "project_remaining_usd": str(
                    Decimal(after["budget"]["remaining_nanodollars"]) / 1_000_000_000
                ),
                "new_since_frozen_plan_usd": str(
                    Decimal(after["budget"]["used_nanodollars"]) / 1_000_000_000
                    - Decimal(cfg["budget_start_used_usd"])
                ),
                "dispatches_before": before["dispatches"],
                "dispatches_after": after["dispatches"],
            }
            # Final outputs are immutable. An interrupted run has only its append-only
            # journal and can safely resume without overwriting a completed report.
            if not (out / "comparison.json").exists():
                new_json(out / "comparison.json", result)
                new_json(out / "costs.json", charges)
                (out / "comparison.md").write_text(
                    comparison.markdown(result) + "\n\nFeedback: " + BASIS + ".\n"
                )
            else:
                check(
                    read(out / "comparison.json") == result, "Completed analysis changed on replay"
                )
            return {"status": result["status"], "outcomes": len(rows), "costs": charges}
    finally:
        journal.db.close()
