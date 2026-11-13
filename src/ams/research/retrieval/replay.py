"""Exact offline replay client for integration checks; misses have no fallback."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ams.llm.types import ChatRequest, ChatResponse, EmbedRequest, EmbedResponse
from ams.research.dynamic.models import LedgerError, check


class ExactReplayClient:
    """Already captured/fixture responses only. Never constructs a model/provider.

    Keys are original request cache keys under `key_provider`, which must be
    explicitly supplied for actual saved responses. Entries must include the
    exact response chosen by the relevant transcript, not an assumed cache winner.
    Loading historical SQLite/transcripts is deliberately outside this adapter.
    """

    provider = "exact-offline-replay"

    def __init__(
        self,
        *,
        key_provider: str,
        chats: Mapping[str, ChatResponse] | None = None,
        embeddings: Mapping[str, EmbedResponse] | None = None,
    ):
        check(isinstance(key_provider, str) and bool(key_provider), "Explicit cache key provider")
        self.key_provider = key_provider
        self._chats = MappingProxyType(dict(chats or {}))
        self._embeddings = MappingProxyType(dict(embeddings or {}))
        self.requests = []

    def complete(self, request: ChatRequest) -> ChatResponse:
        check(type(request) is ChatRequest, "Expected original chat request")
        self.requests.append(request)
        key = request.cache_key(self.key_provider)
        if key not in self._chats:
            raise LedgerError(
                "Offline chat replay miss; no API request or model fallback permitted"
            )
        response = self._chats[key]
        check(
            type(response) is ChatResponse and response.model == request.model,
            "Chat replay model/type mismatch",
        )
        return response

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        check(type(request) is EmbedRequest, "Expected original embedding request")
        self.requests.append(request)
        key = request.cache_key(self.key_provider)
        if key not in self._embeddings:
            raise LedgerError(
                "Offline embedding replay miss; no API request or model fallback permitted"
            )
        response = self._embeddings[key]
        check(
            type(response) is EmbedResponse
            and response.model == request.model
            and len(response.vectors) == len(request.texts),
            "Embedding replay shape/model mismatch",
        )
        return response
