"""Response cache, cost ledger, hard budget stop and offline mock for MINJA processes.

Installed around openai's `Completions.create` (outside the OpenRouter compatibility shim),
so it sees every chat call of the agent, its knowledge step and A-MemGuard:

  cache   identical requests are answered from .llm_cache/minja_v2.sqlite (exact replay
          across rows, pairs and restarts: a resumed run never pays twice)
  ledger  one JSON line per paid call in $MINJA_V2_LEDGER: model, tokens, USD
  budget  before every paid call the ledger total is compared with $MINJA_V2_BUDGET_USD;
          at or above it the process stops (exit 3), so the arm is reported unfinished
  mock    $MINJA_V2_MOCK=1 answers offline with a deterministic stand-in agent (tests only)

Environment: MINJA_V2_CACHE (path of the sqlite cache), MINJA_V2_LEDGER, MINJA_V2_BUDGET_USD,
MINJA_V2_MOCK.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

from . import protocol as P

_INSTALLED = False


def request_key(kwargs: dict, host: str) -> str:
    body = {k: v for k, v in kwargs.items() if k not in ("timeout", "extra_headers")}
    return hashlib.sha256(json.dumps({"host": host, **body}, sort_keys=True, default=str)
                          .encode()).hexdigest()  # fmt: skip


class Cache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path), timeout=60, isolation_level=None)
        self.con.execute("pragma journal_mode=wal")
        self.con.execute("create table if not exists r (k text primary key, v text not null)")

    def get(self, k: str) -> str | None:
        row = self.con.execute("select v from r where k = ?", (k,)).fetchone()
        return row[0] if row else None

    def put(self, k: str, v: str) -> None:
        self.con.execute("insert or ignore into r (k, v) values (?, ?)", (k, v))


def cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = P.PRICE_PER_M.get(model, P.PRICE_PER_M.get(model.split("/")[-1], (0.0, 0.0)))
    return (prompt_tokens * pin + completion_tokens * pout) / 1e6


class Ledger:
    """Append-only JSONL shared by parallel processes (flock); total re-read incrementally."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        self._offset, self._total = 0, 0.0

    def total(self) -> float:
        with self.path.open("r", encoding="utf-8") as fh:
            fh.seek(self._offset)
            for line in fh:
                if line.endswith("\n"):
                    self._total += float(json.loads(line).get("usd", 0.0))
                    self._offset += len(line.encode("utf-8"))
        return self._total

    def add(self, row: dict) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            fh.write(json.dumps(row) + "\n")
            fh.flush()


# ----------------------------------------------------------------------------- mock

_PID = re.compile(r"patient (\d+)")
_REFER = re.compile(r"Refer (\d+) to (\d+)")


def _text(messages) -> str:
    return "\n".join(str(m.get("content") or "") for m in messages)


def mock_response(kwargs: dict) -> dict:
    """A deterministic stand-in that propagates MINJA's redirect like a compliant agent:
    knowledge repeats any 'Refer V to T' seen; code uses T for patient V if the prompt says so."""
    messages = kwargs.get("messages", [])
    system = str(messages[0].get("content", "")) if messages else ""
    text = _text(messages)
    last = messages[-1] if messages else {}
    model = kwargs.get("model", "mock")
    usage = {"prompt_tokens": len(text) // 4, "completion_tokens": 20, "total_tokens": len(text) // 4 + 20}
    base = {"id": "mock-" + hashlib.sha256(text.encode()).hexdigest()[:12], "object": "chat.completion",
            "created": 0, "model": model, "usage": usage}  # fmt: skip

    def msg(content=None, function_call=None):
        m = {"role": "assistant", "content": content}
        if function_call:
            m["function_call"] = function_call
        reason = "function_call" if function_call else "stop"
        return {**base, "choices": [{"index": 0, "message": m, "finish_reason": reason}]}

    if "find information" in system:  # MINJA's knowledge step
        q = text.rsplit("Question:", 1)[-1]
        pid = (_PID.findall(q) or ["0"])[0]
        # only redirects for the patient asked about (a compliant agent's relevant knowledge)
        refs = [f"Refer {v} to {t}." for v, t in _REFER.findall(text) if v == pid]
        return msg(" ".join(dict.fromkeys(refs)) + f" Use patient {pid}." if refs
                   else f"Use patient {pid}.")  # fmt: skip
    if "coding tasks" in system:  # the agent
        if last.get("role") in ("function", "tool"):
            return msg("TERMINATE")
        q = str(messages[-1].get("content", "")).rsplit("Question:", 1)[-1]
        pid = (_PID.findall(q) or ["0"])[0]
        use = pid
        for v, t in _REFER.findall(text):
            if v == pid:
                use = t
        return msg(None, {"name": "python",
                          "arguments": json.dumps({"cell": f"patient = {use}\nanswer = patient"})})
    if "consistency" in text.lower() or "memories" in text.lower():
        return msg('{"consistent_memories": [], "inconsistent_memories": []}')
    return msg("ORDINARY")


# ----------------------------------------------------------------------------- install


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from openai.resources.chat.completions import Completions
    from openai.types.chat import ChatCompletion

    cache = Cache(Path(os.environ["MINJA_V2_CACHE"]))
    ledger = Ledger(Path(os.environ.get("MINJA_V2_LEDGER", "minja_v2_ledger.jsonl")))
    budget = float(os.environ.get("MINJA_V2_BUDGET_USD", "0"))
    mock = os.environ.get("MINJA_V2_MOCK") == "1"
    # raw mock: the mock replies come from below the frozen OpenRouter layer (single_call.raw_mock)
    raw = mock and os.environ.get("MINJA_V2_MOCK_RAW") == "1"
    original = Completions.create

    def create(resource, *args, **kwargs):
        host = "mock" if mock else str(resource._client.base_url)
        key = request_key(kwargs, host)
        hit = cache.get(key)
        if hit is not None:
            from .single_call import dropped_on, log_dropped

            gone = dropped_on(hit)  # a replayed multi-call reply is reported again (rev 2)
            if gone:
                log_dropped([{"dropped": c} for c in gone], replay=True,
                            model=str(kwargs.get("model", "")))  # fmt: skip
            return ChatCompletion.model_validate(json.loads(hit))
        if raw:
            response = original(resource, *args, **kwargs)
        elif mock:
            response = ChatCompletion.model_validate(mock_response(kwargs))
        else:
            spent = ledger.total()
            if budget <= 0 or spent >= budget:
                print(f"!! MINJA budget stop: spent ${spent:.4f} of ${budget:.2f}", file=sys.stderr)
                sys.stderr.flush()
                os._exit(3)
            response = original(resource, *args, **kwargs)
        u = response.usage
        pt, ct = (u.prompt_tokens, u.completion_tokens) if u else (0, 0)
        model = str(kwargs.get("model", ""))
        ledger.add({"t": time.time(), "model": model, "prompt_tokens": pt,
                    "completion_tokens": ct, "usd": 0.0 if mock else cost(model, pt, ct),
                    "mock": mock, "key": key, "run": os.environ.get("MINJA_V2_RUN", "")})  # fmt: skip
        cache.put(key, response.model_dump_json())
        return response

    create._minja_v2 = True
    Completions.create = create
    _INSTALLED = True
