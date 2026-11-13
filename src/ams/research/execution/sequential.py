"""Explicit guarded transport extension; original SequentialRun stays offline."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.sequential.clients import request_from
from ams.research.sequential.runner import SequentialRun

from .session import ExecutionSession, new_json


class GuardedSequentialRun(SequentialRun):
    """Offline snapshots plus an explicit session, never a serialized live client.

    Writes, embeddings and query classifiers remain exact replay only. Only
    current query conflict checks/answers can use the attached budgeted transport.
    A response saved in either journal always wins on restart. Any ambiguous
    provider completion halts rather than issuing the same dispatch again.
    """

    def attach(self, session: ExecutionSession):
        check(type(session) is ExecutionSession, "Expected a shared execution session")
        path = self.directory / "execution_binding.json"
        binding = {
            "session_id": session.config["session_id"],
            "session_directory": str(session.directory),
            "plan_hash": session.config["plan_hash"],
        }
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS execution_binding "
            "(singleton INTEGER PRIMARY KEY CHECK(singleton=1), body TEXT NOT NULL)"
        )
        pinned = self.db.execute("SELECT body FROM execution_binding WHERE singleton=1").fetchone()
        if pinned:
            saved = json.loads(pinned[0])
            check(
                {k: saved[k] for k in binding} == binding,
                "Run cannot switch its shared spending allowance",
            )
            if path.exists():
                check(json.loads(path.read_text()) == saved, "Run/session binding changed")
            else:
                new_json(path, saved)
        else:
            check(
                not self.db.execute("SELECT 1 FROM calls").fetchone(),
                "Attach session before the first recorded call",
            )
            if path.exists():
                saved = json.loads(path.read_text())
                check({k: saved[k] for k in binding} == binding, "Run binding differs")
            else:
                saved = {**binding, "run_id": uuid.uuid4().hex}
                new_json(path, saved)
            from ams.research.dynamic.models import canonical

            self.db.execute("INSERT INTO execution_binding VALUES (1,?)", (canonical(saved),))
        self._execution_session = session
        self._execution_run_id = saved["run_id"]
        return self

    def _lookup_call(self, seq, ordinal, step, work, request, lookup):
        record = lookup()
        if record["error"] is None or record["error"]["type"] != "OfflineMiss":
            return record
        session = getattr(self, "_execution_session", None)
        if session is None or request["kind"] != "chat" or step.kind != "query":
            return record
        client = work.clients[int(request["client_id"])]
        check(
            client.key_provider == "openrouter",
            "Live chat requires the frozen OpenRouter key provider",
        )
        req = request_from("chat", request["request"])
        stage = {200: "answer", 6: "conflict"}.get(req.max_tokens)
        # In particular, a missing 24-token classifier MUST NOT be regenerated per arm.
        if stage is None:
            return record
        call_id = digest([self._execution_run_id, step.event_id, ordinal, request["request_key"]])
        result = session.complete(call_id, stage, req)
        return {**request, **result}

    def execution_resources(self):
        result = super().resources()
        session = getattr(self, "_execution_session", None)
        if session is not None:
            result["shared_execution_session"] = session.summary()
        return result

    def checkpoint(self, directory: Path):
        result = super().checkpoint(directory)
        binding = self.directory / "execution_binding.json"
        if binding.exists():
            new_json(Path(directory) / "execution_binding.json", json.loads(binding.read_text()))
        return result

    @classmethod
    def restore(cls, checkpoint: Path, destination: Path, *, fault=None):
        # Super restores only the offline state. Never reopen/reset a budget implicitly.
        result = super().restore(checkpoint, destination, fault=fault)
        binding = Path(checkpoint) / "execution_binding.json"
        if binding.exists():
            new_json(Path(destination) / "execution_binding.json", json.loads(binding.read_text()))
        return result
