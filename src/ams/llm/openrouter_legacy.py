"""Translate AutoGen 0.2 function calls at the OpenRouter HTTP boundary.

The legacy agent still receives ``function_call`` responses and executes its
original function map. Only requests sent to openrouter.ai use the tools schema.
"""

from __future__ import annotations

from copy import deepcopy
from functools import wraps
from urllib.parse import urlparse


def _modern_request(kwargs: dict) -> tuple[dict, bool]:
    out = dict(kwargs)
    legacy = "functions" in out or "function_call" in out
    functions = out.pop("functions", None)
    if functions is not None:
        if "tools" in out:
            raise ValueError("Cannot mix legacy functions and modern tools")
        out["tools"] = [{"type": "function", "function": f} for f in functions]
    choice = out.pop("function_call", None)
    if choice is not None:
        out["tool_choice"] = (
            {"type": "function", "function": {"name": choice["name"]}}
            if isinstance(choice, dict)
            else choice
        )

    messages = []
    pending: dict[str, list[str]] = {}
    for index, message in enumerate(out.get("messages", [])):
        item = deepcopy(message)
        call = item.pop("function_call", None)
        if call:
            legacy = True
            if item.get("tool_calls"):
                raise ValueError("Cannot mix function_call and tool_calls in one message")
            item["tool_calls"] = [
                {"id": f"legacy_call_{index}", "type": "function", "function": call}
            ]
        for tool_call in item.get("tool_calls") or []:
            pending.setdefault(tool_call["function"]["name"], []).append(tool_call["id"])
        if item.get("role") == "function":
            legacy = True
            name = item.pop("name")
            if not pending.get(name):
                raise ValueError(f"Legacy function result {name!r} has no matching call")
            item["role"] = "tool"
            item["tool_call_id"] = pending[name].pop(0)
        messages.append(item)
    out["messages"] = messages
    if legacy:
        if out.get("stream"):
            raise ValueError("AutoGen 0.2 compatibility requires non-streaming responses")
        # The original agent handles one function per response.
        out["extra_body"] = {**(out.get("extra_body") or {}), "parallel_tool_calls": False}
    return out, legacy


def _legacy_response(response):
    from openai.types.chat import ChatCompletion

    data = response.model_dump()
    for choice in data["choices"]:
        calls = choice["message"].pop("tool_calls", None) or []
        if len(calls) > 1:
            raise ValueError("OpenRouter returned parallel calls to a single-function legacy agent")
        if calls:
            choice["message"]["function_call"] = calls[0]["function"]
            if choice["finish_reason"] == "tool_calls":
                choice["finish_reason"] = "function_call"
    return ChatCompletion.model_validate(data)


def install() -> None:
    """Install once in the legacy environment; other providers pass through."""
    from openai.resources.chat.completions import Completions

    original = Completions.create
    if getattr(original, "_ams_openrouter_legacy", False):
        return

    @wraps(original)
    def create(resource, *args, **kwargs):
        if urlparse(str(resource._client.base_url)).hostname != "openrouter.ai":
            return original(resource, *args, **kwargs)
        request, legacy = _modern_request(kwargs)
        response = original(resource, *args, **request)
        return _legacy_response(response) if legacy else response

    create._ams_openrouter_legacy = True
    Completions.create = create
