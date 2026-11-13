"""Fail-closed construction client over immutable existing SQLite snapshots."""

from __future__ import annotations

import math
from dataclasses import asdict

from ams.llm.types import ChatRequest, EmbedRequest
from ams.research.dynamic.models import check
from ams.research.recovery.offline import CHAT_MODEL, EMBED_MODEL, ReadOnlyCache
from ams.research.sequential.clients import response_from


def cached_response(kind, payload):
    data = {**payload, "cached": True}
    if kind == "chat":
        data.setdefault("raw_finish_reason", None)
    return response_from(kind, data)


def validate_embedding(response, request):
    check(len(response.vectors) == len(request.texts), "Embedding batch size differs")
    check(all(len(v) == 384 for v in response.vectors), "Expected frozen MiniLM dimensions")
    check(
        all(type(x) in {float, int} and math.isfinite(x) for v in response.vectors for x in v),
        "Nonfinite cached vectors",
    )


class ConstructionCache:
    """No SDK, retries, cache writes, credential loading, model or paid fallback."""

    def __init__(self, cache: ReadOnlyCache, provider: str):
        check(provider in {"openrouter", "local"}, "Unexpected construction provider")
        self.cache, self.provider = cache, provider
        self.chats, self.embeddings, self.receipts = {}, {}, []

    def _request(self, kind, request):
        expected = ChatRequest if kind == "chat" else EmbedRequest
        model = CHAT_MODEL if kind == "chat" else EMBED_MODEL
        check(type(request) is expected and request.model == model, "Unfrozen construction model")
        check(self.provider == ("openrouter" if kind == "chat" else "local"), "Wrong cache role")
        key = request.cache_key(self.provider)
        payload, receipt = self.cache.get(key, kind, self.provider, model)
        response = cached_response(kind, payload)
        if kind == "embed":
            validate_embedding(response, request)
        else:
            check(type(response.text) is str, "Cached chat text is not a string")
        table = self.chats if kind == "chat" else self.embeddings
        check(
            key not in table or table[key] == response, "Cache response changed during construction"
        )
        table[key] = response
        self.receipts.append({"kind": kind, "request": asdict(request), "receipt": receipt})
        return response

    def complete(self, request):
        return self._request("chat", request)

    def embed(self, request):
        return self._request("embed", request)
