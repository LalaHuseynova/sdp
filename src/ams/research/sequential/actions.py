"""Only the currently dispatched public action/revealed finding enters the runner."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ams.research.dynamic.models import (
    Audit,
    Retract,
    canonical,
    check,
    event_dict,
    integer,
    name,
    parse_event,
)


@dataclass(frozen=True)
class Step:
    event_id: str
    at: int
    kind: str
    data_json: str

    def __post_init__(self):
        name(self.event_id, "event ID")
        integer(self.at, "logical time")
        body = json.loads(self.data_json)
        keys = {
            "query": {
                "session_id",
                "query",
                "use_id",
                "requester",
                "principal",
                "operation",
                "k",
                "answer",
            },
            "reveal": {"event"},
            "policy": {"access"},
            "draw": {"choices"},
            "write": {
                "session_id",
                "user_query",
                "context",
                "principal",
                "writer",
                "bindings",
                "access",
                "registrations",
            },
        }
        check(
            self.kind in keys and type(body) is dict and set(body) == keys[self.kind],
            "Unexpected action fields; pending/gold schedules are not runtime actions",
        )
        check(canonical(body) == self.data_json, "Action payload must be canonical")
        if self.kind == "query":
            for field in ("session_id", "use_id", "requester", "principal", "operation"):
                name(body[field], field)
            check(
                type(body["query"]) is str and type(body["answer"]) is bool, "Invalid query action"
            )
            integer(body["k"], "k")
        elif self.kind == "reveal":
            event = parse_event(body["event"])
            check(
                type(event) in {Audit, Retract} and event.revealed_at == self.at,
                "Reveal time must match current dispatched event",
            )
        elif self.kind == "draw":
            check(type(body["choices"]) is list and bool(body["choices"]), "Nonempty draw choices")
            for value in body["choices"]:
                name(value, "choice")

    @property
    def payload(self) -> dict:
        return json.loads(self.data_json)

    def dump(self) -> dict:
        return {
            "event_id": self.event_id,
            "at": self.at,
            "kind": self.kind,
            "payload": self.payload,
        }

    @classmethod
    def make(cls, event_id: str, at: int, kind: str, payload: dict):
        return cls(event_id, at, kind, canonical(payload))

    @classmethod
    def load(cls, body: dict):
        check(set(body) == {"event_id", "at", "kind", "payload"}, "Unexpected step fields")
        return cls.make(body["event_id"], body["at"], body["kind"], body["payload"])

    @classmethod
    def query(
        cls,
        event_id: str,
        at: int,
        *,
        session_id: str,
        query: str,
        use_id: str,
        requester="user",
        principal="user",
        operation="read",
        k=4,
        answer=True,
    ):
        return cls.make(
            event_id,
            at,
            "query",
            {
                "session_id": session_id,
                "query": query,
                "use_id": use_id,
                "requester": requester,
                "principal": principal,
                "operation": operation,
                "k": k,
                "answer": answer,
            },
        )

    @classmethod
    def reveal(cls, event_id: str, at: int, event: Audit | Retract):
        return cls.make(event_id, at, "reveal", {"event": event_dict(event)})
