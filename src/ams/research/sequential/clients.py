"""Exact offline clients with full response capture, including failures and usage."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from decimal import Decimal

from ams.llm.types import (
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    Message,
    Usage,
)
from ams.research.dynamic.models import LedgerError, canonical, check, fields_only
from ams.research.retrieval.replay import ExactReplayClient


class ReplayDivergence(LedgerError):
    """An interrupted step no longer issues its saved request sequence; stop recovery."""


def response_from(kind: str, data: dict):
    cls = ChatResponse if kind == "chat" else EmbedResponse
    body = fields_only(data, cls)
    body["usage"] = Usage(**fields_only(body["usage"], Usage))
    check(
        all(
            type(v) is int and v >= 0
            for v in (body["usage"].input_tokens, body["usage"].output_tokens)
        )
        and math.isfinite(body["usage"].cost_usd)
        and body["usage"].cost_usd >= 0,
        "Invalid reported response usage",
    )
    if kind == "embed":
        body["vectors"] = tuple(tuple(v) for v in body["vectors"])
    return cls(**body)


class RecordedReplayClient:
    """No live delegate or transport: a miss is recorded and fails closed.

    A journal resolver can return an already saved response before consulting the
    frozen table. It is therefore the event transcript, not a later cache value,
    that determines recovery. The resolver is never serialized executable code.
    """

    provider = "recorded-offline-replay"

    def __init__(self, key_provider: str, chats: dict, embeddings: dict, history=()):
        self.key_provider = key_provider
        self.chats = dict(chats)
        self.embeddings = dict(embeddings)
        self.history = list(history)
        self.resolver = None
        self.client_id = ""

    @classmethod
    def capture(cls, client):
        if type(client) is cls:
            return cls.load(client.dump())
        check(
            type(client) is ExactReplayClient and not client.requests,
            "Only unused ExactReplayClient can be attached; past responses cannot be guessed",
        )
        return cls(
            client.key_provider,
            {k: asdict(v) for k, v in client._chats.items()},
            {k: asdict(v) for k, v in client._embeddings.items()},
        )

    def dump(self) -> dict:
        return json.loads(
            canonical(
                {
                    "key_provider": self.key_provider,
                    "chats": self.chats,
                    "embeddings": self.embeddings,
                    "history": self.history,
                }
            )
        )

    @classmethod
    def load(cls, body: dict):
        check(
            set(body) == {"key_provider", "chats", "embeddings", "history"},
            "Unexpected replay client fields",
        )
        for kind, table in (("chat", body["chats"]), ("embed", body["embeddings"])):
            check(type(table) is dict, "Invalid frozen response table")
            for value in table.values():
                response_from(kind, value)
        return cls(**body)

    def _request(self, kind: str, request):
        expected = ChatRequest if kind == "chat" else EmbedRequest
        check(type(request) is expected, "Unsupported replay request")
        record = {
            "client_id": self.client_id,
            "kind": kind,
            "request": asdict(request),
            "request_key": request.cache_key(self.key_provider),
        }

        def lookup():
            table = self.chats if kind == "chat" else self.embeddings
            if record["request_key"] not in table:
                return {
                    **record,
                    "response": None,
                    "error": {"type": "OfflineMiss", "message": f"Offline {kind} replay miss"},
                    "actual_paid_usd": "0",
                }
            response = response_from(kind, table[record["request_key"]])
            error = None
            try:
                check(response.model == request.model, "Replay response model mismatch")
                if kind == "embed":
                    check(
                        len(response.vectors) == len(request.texts),
                        "Replay embedding shape mismatch",
                    )
            except LedgerError as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            return {**record, "response": asdict(response), "error": error, "actual_paid_usd": "0"}

        result = self.resolver(record, lookup) if self.resolver else lookup()
        self.history.append(json.loads(canonical(result)))
        if result["error"]:
            raise LedgerError(result["error"]["message"])
        return response_from(kind, result["response"])

    def complete(self, request: ChatRequest) -> ChatResponse:
        return self._request("chat", request)

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        return self._request("embed", request)


def accounting(clients: list[RecordedReplayClient]) -> dict:
    records = [row for c in clients for row in c.history]
    responses = [r["response"] for r in records if r["response"] is not None]
    return {
        "replay_attempts": len(records),
        "failed_replay_attempts": sum(bool(r["error"]) for r in records),
        "chat_responses": sum(r["kind"] == "chat" and r["response"] is not None for r in records),
        "embedding_responses": sum(
            r["kind"] == "embed" and r["response"] is not None for r in records
        ),
        "reported_input_tokens": sum(r["usage"]["input_tokens"] for r in responses),
        "reported_output_tokens": sum(r["usage"]["output_tokens"] for r in responses),
        "reported_equivalent_cost_usd": str(
            sum((Decimal(str(r["usage"]["cost_usd"])) for r in responses), Decimal(0))
        ),
        "unknown_usage_attempts": sum(r["response"] is None for r in records),
        "actual_paid_usd": str(
            sum(
                (
                    Decimal(r["actual_paid_usd"])
                    for r in records
                    if r["actual_paid_usd"] is not None
                ),
                Decimal(0),
            )
        ),
        "unknown_paid_attempts": sum(r["actual_paid_usd"] is None for r in records),
        "live_api_calls": sum(
            r.get("dispatch", {}).get("mode") == "live" and r["dispatch"]["receipt"] is not None
            for r in records
        ),
        "mock_dispatch_calls": sum(r.get("dispatch", {}).get("mode") == "mock" for r in records),
    }


def validate_call_record(record):
    keys = {"client_id", "kind", "request", "request_key", "response", "error", "actual_paid_usd"}
    check(set(record) in (keys, keys | {"dispatch"}), "Invalid call record fields")
    check(record["kind"] in {"chat", "embed"}, "Invalid call kind")
    if "dispatch" not in record:
        check(record["actual_paid_usd"] == "0", "Offline calls cannot claim paid dispatch")
        return
    d = record["dispatch"]
    check(
        record["kind"] == "chat"
        and set(d) == {"session_id", "call_id", "mode", "receipt", "prompt_measurement"}
        and d["mode"] in {"mock", "live"},
        "Invalid guarded dispatch provenance",
    )
    value = record["actual_paid_usd"]
    if value is not None:
        check(isinstance(value, str), "Invalid dispatch charge")
        amount = Decimal(value)
        check(amount.is_finite() and amount >= 0, "Invalid dispatch charge")
        receipt = d["receipt"]
        actual = receipt["actual_nanodollars"] if receipt else None
        expected = Decimal(actual) / 1_000_000_000 if actual is not None else Decimal(0)
        check(
            amount == (expected if d["mode"] == "live" else Decimal(0)),
            "Saved charge disagrees with guarded receipt",
        )
    else:
        check(record["error"] is not None, "Successful dispatch cannot have unknown billing")


def request_from(kind: str, value: dict):
    """Used only by integrity checks; never imports or executes an arbitrary class."""
    cls = ChatRequest if kind == "chat" else EmbedRequest
    body = fields_only(value, cls)
    if kind == "chat":
        body["messages"] = tuple(Message(**fields_only(v, Message)) for v in body["messages"])
        body["stop"] = tuple(body["stop"])
    else:
        body["texts"] = tuple(body["texts"])
    return cls(**body)
