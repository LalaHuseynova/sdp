"""One function call per assistant turn, as MINJA's EHRAgent was written for (protocol rev 2).

Why. MINJA's EHRAgent (commit a3ec8da, config.py) calls GPT-4 through OpenAI's legacy
`functions` API, which returns at most ONE `function_call` per assistant message; its agent
(`medagent.execute_function`) runs that one call, and every call executes in a fresh
namespace (`toolset_high.run_code`: `global_var = {"answer": 0}`) and must set `answer`
itself. OpenRouter only offers the `tools` API, and GPT-4o-mini returns two or more
`python` tool calls in one reply in about half of EHRAgent's coding turns, although the
request carries `parallel_tool_calls: false` (pilot attempt 1, diagnostics/raw.jsonl).
The frozen compatibility layer `ams.llm.openrouter_legacy` (unchanged) rightly refuses such
a reply, because the legacy agent cannot represent it.

What. This layer sits BELOW the frozen one (it wraps the raw client call and must be
installed first) and keeps the first tool call of a multi-call reply, which is the reply the
legacy API would have produced: the model sees that cell's result and issues any further
cell on its next turn, as the agent loop intends. A later parallel cell cannot use the first
cell's variables (fresh namespace), so nothing executable is lost that the model cannot
re-issue. Nothing is discarded silently: every reply to a tool-bearing request is written to
$MINJA_V2_DROPPED (JSONL: number of calls, and every dropped call with its full arguments)
and the dropped calls are kept on the response as `minja_v2_dropped`. The drop RATE is over
unique requests: autogen 0.2's own response cache (`cache_seed`) answers a repeated identical
request with the identical stored reply before it reaches this layer.

Only requests that carry tools are touched; every other request and response passes through.
"""

from __future__ import annotations

import json
import os
import time

_INSTALLED = False


def keep_first(data: dict) -> tuple[dict, list[dict]]:
    """A raw chat-completion dict with at most one tool call per choice, and the dropped calls."""
    dropped = []
    for choice in data.get("choices") or []:
        msg = choice.get("message") or {}
        calls = msg.get("tool_calls") or []
        if len(calls) > 1:
            dropped.extend({"index": choice.get("index"), "kept_id": calls[0].get("id"),
                            "dropped": c} for c in calls[1:])  # fmt: skip
            msg["tool_calls"] = calls[:1]
            msg["minja_v2_dropped"] = [c for c in calls[1:]]
    return data, dropped


def log_dropped(dropped: list[dict], *, replay: bool, model: str, n_calls: int | None = None,
                always: bool = False) -> None:
    path = os.environ.get("MINJA_V2_DROPPED")
    if not path or not (dropped or always):
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), "run": os.environ.get("MINJA_V2_RUN", ""),
                            "model": model, "replay": replay, "n_calls": n_calls,
                            "n_dropped": len(dropped), "dropped": dropped}) + "\n")  # fmt: skip


def raw_mock(kwargs: dict) -> dict:
    """Offline stand-in for the raw OpenRouter reply (tools API): the mock agent's answer, with
    every coding turn returned as TWO parallel tool calls (as GPT-4o-mini did in pilot attempt 1)."""
    from .llm_cache import mock_response

    data = mock_response(kwargs)
    for choice in data["choices"]:
        fc = choice["message"].pop("function_call", None)
        if fc:
            extra = {"name": fc["name"], "arguments": json.dumps({"cell": "answer = 'parallel'"})}
            choice["message"]["tool_calls"] = [
                {"id": "call_0", "type": "function", "function": fc},
                {"id": "call_1", "type": "function", "function": extra}]
            choice["finish_reason"] = "tool_calls"
    return data


def install() -> None:
    """Wrap the raw client call. Must run before `ams.llm.openrouter_legacy.install`."""
    global _INSTALLED
    if _INSTALLED:
        return
    from openai.resources.chat.completions import Completions
    from openai.types.chat import ChatCompletion

    original = Completions.create
    if getattr(original, "_ams_openrouter_legacy", False) or getattr(original, "_minja_v2", False):
        raise RuntimeError("single_call must be installed below the legacy layer and the cache")
    if os.environ.get("MINJA_V2_MOCK_RAW") == "1":  # offline end-to-end test only

        def original(resource, *args, **kwargs):  # noqa: F811
            return ChatCompletion.model_validate(raw_mock(kwargs))

    def create(resource, *args, **kwargs):
        response = original(resource, *args, **kwargs)
        if not kwargs.get("tools"):
            return response
        data, dropped = keep_first(response.model_dump())
        n_calls = sum(len(c.message.tool_calls or []) for c in response.choices)
        log_dropped(dropped, replay=False, model=str(kwargs.get("model", "")), n_calls=n_calls,
                    always=True)  # every tool reply: the drop rate's denominator
        return ChatCompletion.model_validate(data) if dropped else response

    create._minja_v2_single_call = True
    Completions.create = create
    _INSTALLED = True


def dropped_on(response_json: str) -> list:
    """Dropped calls recorded on a (cached) response, for the replay log."""
    try:
        data = json.loads(response_json)
    except ValueError:
        return []
    return [c for ch in data.get("choices") or []
            for c in ((ch.get("message") or {}).get("minja_v2_dropped") or [])]  # fmt: skip
