"""Single-writer, append-only SQLite event/call/commit journal and offline recovery."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ams.llm.types import ChatRequest, Message
from ams.research.dynamic import EvidenceSnapshot, Register
from ams.research.dynamic.models import LedgerError, canonical, check, digest, parse_event
from ams.research.retrieval import BindingCatalog, RetrievalContext

from .actions import Step
from .clients import (
    RecordedReplayClient,
    ReplayDivergence,
    accounting,
    request_from,
    response_from,
    validate_call_record,
)
from .state import SCHEMA, RuntimeState, access_load, graph_dump


def fingerprints() -> dict:
    """Pin executable dependencies; reports/data are not runtime code dependencies."""
    root = Path(__file__).resolve().parents[4]
    paths = [
        *Path(__file__).parent.glob("*.py"),
        *(root / "src/ams/research/dynamic").glob("*.py"),
        *(root / "src/ams/research/retrieval").glob("*.py"),
        *(root / "src/ams/research/execution").glob("*.py"),
        *(root / "src/ams/memory").glob("*.py"),
        *(root / "src/ams/core").glob("*.py"),
        root / "src/ams/eval/use_type.py",
        root / "src/ams/llm/types.py",
        root / "src/ams/llm/budget.py",
        root / "src/ams/llm/providers/openai_client.py",
        root / "src/ams/llm/pricing.py",
    ]
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
    }


def environment() -> dict:
    return {
        "python": sys.version,
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "numpy": np.__version__,
        "sqlite": sqlite3.sqlite_version,
    }


def append_evidence(state: RuntimeState, event, at: int):
    existing = next((v for v in state.evidence.events if v.event_id == event.event_id), None)
    check(existing is None or existing == event, "Conflicting evidence event ID")
    check(event.revealed_at == at, "Cannot backdate a revealed observation")
    events = state.evidence.events if existing else (*state.evidence.events, event)
    state.evidence = EvidenceSnapshot(state.evidence.config, tuple(events), at)


class SequentialRun:
    """One current action at a time. No future plan or evaluator label store is accepted.

    Intents, completed calls and commits are separate immutable rows. A crash
    between a saved call and its event commit resumes from the committed state,
    replaying the exact saved call prefix without charging or requesting it again.
    This implementation is restricted to offline recorded clients, not live APIs.
    """

    def __init__(self, directory: Path, *, fault=None):
        self.directory = Path(directory)
        check((self.directory / "run.sqlite").is_file(), "No existing run database")
        self._lock = (self.directory / "writer.lock").open("a+b")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self._lock.close()
            raise LedgerError("Another sequential writer owns this run") from error
        try:
            self.db = sqlite3.connect(self.directory / "run.sqlite", isolation_level=None)
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA foreign_keys=ON")
            self.fault = fault
            self._verify()
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self._lock.close()
            raise

    @classmethod
    def create(cls, directory: Path, state: RuntimeState, *, fault=None):
        directory = Path(directory)
        check(not directory.exists(), "Refuse to overwrite an existing run")
        directory.mkdir(parents=True, mode=0o700)
        (directory / ".gitignore").write_text("*\n!.gitignore\n")
        dbpath = directory / "run.sqlite"
        fd = os.open(dbpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        connection = sqlite3.connect(dbpath)
        try:
            connection.executescript("""
                PRAGMA synchronous=FULL;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE intents (seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                    action TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE calls (seq INTEGER PRIMARY KEY, intent INTEGER NOT NULL,
                    ordinal INTEGER NOT NULL, record TEXT NOT NULL, previous TEXT NOT NULL,
                    hash TEXT NOT NULL, UNIQUE(intent,ordinal));
                CREATE TABLE commits (seq INTEGER PRIMARY KEY, state TEXT NOT NULL,
                    result TEXT NOT NULL, call_count INTEGER NOT NULL, call_head TEXT NOT NULL,
                    previous TEXT NOT NULL, hash TEXT NOT NULL);
            """)
            initial = state.dump()
            for key, value in {
                "schema": SCHEMA,
                "code": fingerprints(),
                "environment": environment(),
                "initial": initial,
            }.items():
                connection.execute("INSERT INTO metadata VALUES (?,?)", (key, canonical(value)))
            connection.commit()
        finally:
            connection.close()
        return cls(directory, fault=fault)

    def close(self):
        self.db.close()
        self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _verify(self):
        check(
            self.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Corrupt run database"
        )
        metadata = {
            key: json.loads(value) for key, value in self.db.execute("SELECT * FROM metadata")
        }
        check(
            set(metadata) == {"schema", "code", "environment", "initial"}
            and metadata["schema"] == SCHEMA,
            "Unknown run metadata",
        )
        check(metadata["code"] == fingerprints(), "Runtime code changed since run/checkpoint")
        check(
            metadata["environment"] == environment(), "Runtime environment changed since checkpoint"
        )
        self.initial = metadata["initial"]
        self.anchor = digest(metadata)
        intents = self.db.execute("SELECT * FROM intents ORDER BY seq").fetchall()
        head = self.anchor
        for number, (seq, event_id, action, previous, checksum) in enumerate(intents, 1):
            check(seq == number and previous == head, "Intent order/prefix mismatch")
            step = Step.load(json.loads(action))
            check(
                step.event_id == event_id and canonical(step.dump()) == action, "Invalid action row"
            )
            head = digest([seq, event_id, action, previous])
            check(head == checksum, "Intent hash mismatch")
        calls = self.db.execute("SELECT * FROM calls ORDER BY seq").fetchall()
        call_heads = [self.anchor]
        ordinals = {}
        for number, (seq, intent, ordinal, record, previous, checksum) in enumerate(calls, 1):
            check(
                seq == number and 1 <= intent <= len(intents) and previous == call_heads[-1],
                "Call order/prefix mismatch",
            )
            check(ordinal == ordinals.get(intent, 0), "Call ordinal mismatch")
            ordinals[intent] = ordinal + 1
            check(canonical(json.loads(record)) == record, "Noncanonical call record")
            check(
                digest([seq, intent, ordinal, record, previous]) == checksum, "Call hash mismatch"
            )
            call_heads.append(checksum)
        commits = self.db.execute("SELECT * FROM commits ORDER BY seq").fetchall()
        head, last_clock = self.anchor, self.initial["clock"]
        for number, (seq, state, result, count, call_head, previous, checksum) in enumerate(
            commits, 1
        ):
            check(
                seq == number and seq <= len(intents) and previous == head, "Commit order mismatch"
            )
            check(
                0 <= count < len(call_heads) and call_heads[count] == call_head,
                "Commit call-prefix mismatch",
            )
            check(
                all(v[1] <= seq for v in calls[:count]) and all(v[1] > seq for v in calls[count:]),
                "Call attached to wrong committed boundary",
            )
            head = digest([seq, state, result, count, call_head, previous])
            check(checksum == head, "Commit hash mismatch")
            body = json.loads(state)
            check(body["clock"] >= last_clock, "Backdated committed step")
            last_clock = body["clock"]
        check(len(intents) in {len(commits), len(commits) + 1}, "More than one pending step")
        self.cursor, self.head = len(commits), head
        body = json.loads(commits[-1][1]) if commits else self.initial
        self.state = RuntimeState.load(body)
        for i, client in enumerate(self.state.clients):
            expected = [
                *self.initial["clients"][i]["history"],
                *(
                    json.loads(row[3])
                    for row in calls
                    if row[1] <= self.cursor and json.loads(row[3])["client_id"] == str(i)
                ),
            ]
            check(
                client.history == expected, "Committed response history differs from call journal"
            )
        for row in calls:
            record = json.loads(row[3])
            validate_call_record(record)
            client = self.state.clients[int(record["client_id"])]
            request = request_from(record["kind"], record["request"])
            check(
                request.cache_key(client.key_provider) == record["request_key"],
                "Call request-key mismatch",
            )
            if record["response"] is not None:
                response_from(record["kind"], record["response"])

    def results(self) -> list[dict]:
        return [
            json.loads(row[0]) for row in self.db.execute("SELECT result FROM commits ORDER BY seq")
        ]

    def resources(self) -> dict:
        """Include durable calls from a pending step without counting replay a second time."""
        rows = [json.loads(r[0]) for r in self.db.execute("SELECT record FROM calls ORDER BY seq")]
        clients = []
        for i, initial in enumerate(self.initial["clients"]):
            history = [*initial["history"], *(r for r in rows if r["client_id"] == str(i))]
            clients.append(RecordedReplayClient(initial["key_provider"], {}, {}, history))
        return {
            "committed": self.state.usage(),
            "recorded_inference_including_pending": accounting(clients),
            "pending_steps": self.db.execute("SELECT count(*) FROM intents").fetchone()[0]
            - self.cursor,
        }

    def _fault(self, stage):
        if self.fault:
            self.fault(stage)

    def step(self, step: Step) -> dict:
        self._assert_current()
        step = Step.load(step.dump())
        existing = self.db.execute(
            "SELECT seq,action FROM intents WHERE event_id=?", (step.event_id,)
        ).fetchone()
        if existing:
            check(existing[1] == canonical(step.dump()), "Event ID reused with changed action")
            committed = self.db.execute(
                "SELECT result FROM commits WHERE seq=?", (existing[0],)
            ).fetchone()
            if committed:
                return json.loads(committed[0])
            return self.recover()
        check(
            self.db.execute("SELECT count(*) FROM intents").fetchone()[0] == self.cursor,
            "Recover the pending step before dispatching another",
        )
        check(step.at >= self.state.clock, "Cannot backdate after a committed query/event")
        seq = self.cursor + 1
        previous = self.db.execute("SELECT hash FROM intents ORDER BY seq DESC LIMIT 1").fetchone()
        previous = previous[0] if previous else self.anchor
        action = canonical(step.dump())
        self.db.execute(
            "INSERT INTO intents VALUES (?,?,?,?,?)",
            (seq, step.event_id, action, previous, digest([seq, step.event_id, action, previous])),
        )
        self._fault("after_intent")
        return self._execute(seq, step)

    def recover(self) -> dict | None:
        self._assert_current()
        pending = self.db.execute(
            "SELECT seq,action FROM intents WHERE seq>?", (self.cursor,)
        ).fetchall()
        check(len(pending) <= 1, "Multiple pending steps")
        if not pending:
            return None
        return self._execute(pending[0][0], Step.load(json.loads(pending[0][1])))

    def _assert_current(self):
        saved = self.db.execute("SELECT state FROM commits WHERE seq=?", (self.cursor,)).fetchone()
        expected = saved[0] if saved else canonical(self.initial)
        check(canonical(self.state.dump()) == expected, "Unjournaled runtime state mutation")

    def _execute(self, seq: int, step: Step) -> dict:
        check(step.at >= self.state.clock, "Pending event is backdated")
        before = self.state.dump()
        work = RuntimeState.load(before)
        work.clock = step.at
        work.evidence = EvidenceSnapshot(work.evidence.config, work.evidence.events, step.at)
        saved = [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT record FROM calls WHERE intent=? ORDER BY ordinal", (seq,)
            )
        ]
        ordinal = 0

        def resolve(request, lookup):
            nonlocal ordinal
            if ordinal < len(saved):
                record = saved[ordinal]
                check_keys = {k: record[k] for k in request}
                if canonical(check_keys) != canonical(request):
                    raise ReplayDivergence("Saved call sequence differs; recovery refused")
            else:
                record = json.loads(
                    canonical(self._lookup_call(seq, ordinal, step, work, request, lookup))
                )
                validate_call_record(record)
                last = self.db.execute(
                    "SELECT seq,hash FROM calls ORDER BY seq DESC LIMIT 1"
                ).fetchone()
                number, previous = (last[0] + 1, last[1]) if last else (1, self.anchor)
                text = canonical(record)
                self.db.execute(
                    "INSERT INTO calls VALUES (?,?,?,?,?,?)",
                    (
                        number,
                        seq,
                        ordinal,
                        text,
                        previous,
                        digest([number, seq, ordinal, text, previous]),
                    ),
                )
                saved.append(record)
                self._fault("after_call")
            ordinal += 1
            return record

        for client in work.clients:
            client.resolver = resolve
        progress = {}
        try:
            value = self._perform(work, step, progress)
            work.validate()
            result = {
                "event_id": step.event_id,
                "at": step.at,
                "kind": step.kind,
                "status": "completed",
                "value": value,
            }
        except ReplayDivergence:
            raise
        except Exception as error:
            # Roll back graph, ACLs, RNG and classifier state, but never erase attempted calls.
            failed_clients = [c.dump() for c in work.clients]
            work = RuntimeState.load({**before, "clients": failed_clients})
            work.clock = step.at
            work.evidence = EvidenceSnapshot(work.evidence.config, work.evidence.events, step.at)
            result = {
                "event_id": step.event_id,
                "at": step.at,
                "kind": step.kind,
                "status": "failed",
                "error": {"type": type(error).__name__, "message": str(error)},
                "partial": progress,
            }
        check(ordinal == len(saved), "Unused saved calls: recovery would change behavior")
        for client in work.clients:
            client.resolver = None
        result["resources"] = work.usage()
        state_json, result_json = canonical(work.dump()), canonical(result)
        tail = self.db.execute("SELECT seq,hash FROM calls ORDER BY seq DESC LIMIT 1").fetchone()
        count, call_head = tail if tail else (0, self.anchor)
        checksum = digest([seq, state_json, result_json, count, call_head, self.head])
        self._fault("before_commit")
        self.db.execute(
            "INSERT INTO commits VALUES (?,?,?,?,?,?,?)",
            (seq, state_json, result_json, count, call_head, self.head, checksum),
        )
        self.state, self.cursor, self.head = work, seq, checksum
        self._fault("after_commit")
        return json.loads(result_json)

    def _lookup_call(self, seq, ordinal, step, work, request, lookup):
        """Offline by default. Only the explicitly attached research subclass dispatches."""
        return lookup()

    def _perform(self, state: RuntimeState, step: Step, progress: dict):
        p = step.payload
        if step.kind == "reveal":
            append_evidence(state, parse_event(p["event"]), step.at)
            return {
                "evidence_revision": state.evidence.revision,
                "audit": asdict(state.evidence.usage),
            }
        if step.kind == "policy":
            access = access_load(p["access"])
            check(
                access.version not in state.policy_history, "Policy changes require a fresh version"
            )
            state.access = access
            state.policy_history = (*state.policy_history, access.version)
            return {"version": access.version, "access_hash": access.fingerprint}
        if step.kind == "draw":
            return {"chosen": state.rng.choice(p["choices"])}
        if step.kind == "write":
            check(p["writer"] in state.writers, "Write denied by trusted writer policy")
            bindings = BindingCatalog.from_dict(p["bindings"])
            check(
                bindings.sources[: len(state.bindings.sources)] == state.bindings.sources
                and bindings.records[: len(state.bindings.records)] == state.bindings.records,
                "Write cannot rewrite earlier provenance bindings",
            )
            access = access_load(p["access"])
            if access.version == state.access.version:
                check(
                    access.grants[: len(state.access.grants)] == state.access.grants,
                    "Existing permission changes require a new policy version",
                )
            else:
                check(access.version not in state.policy_history, "Cannot reuse old policy version")
                state.policy_history = (*state.policy_history, access.version)
            previous_graphs = {key: graph_dump(g) for key, g in state.memory._graphs.items()}
            previous_chunks = {
                key: [asdict(c) for c in chunks] for key, chunks in state.memory._chunks.items()
            }
            written = state.memory.write(
                session_id=p["session_id"],
                user_query=p["user_query"],
                context=p["context"],
                principal=p["principal"],
            )
            for key, old in previous_graphs.items():
                current = graph_dump(state.memory._graphs[key])
                for field in ("claims", "sources", "entities"):
                    check(
                        current[field][: len(old[field])] == old[field],
                        "Write overwrote existing graph nodes",
                    )
            for key, old in previous_chunks.items():
                check(
                    [asdict(c) for c in state.memory._chunks[key]][: len(old)] == old,
                    "Write overwrote existing chunks",
                )
            progress["write"] = asdict(written)
            for row in p["registrations"]:
                event = parse_event(row)
                check(type(event) is Register, "Write may register provenance, not reveal labels")
                append_evidence(state, event, step.at)
            state.bindings, state.access = bindings, access
            return asdict(written)
        context = RetrievalContext(
            state.evidence, state.access, p["use_id"], p["requester"], p["operation"]
        )
        outcome = state.reader().retrieve_with_trace(
            session_id=p["session_id"],
            query=p["query"],
            context=context,
            k=p["k"],
            principal=p["principal"],
        )
        progress["retrieval"] = asdict(outcome)
        result = {"retrieval": asdict(outcome), "answer": None, "truncated": False}
        if p["answer"]:
            body = "\n".join(f"- {e.text}" for e in outcome.retrieval.entries) or "(nothing)"
            prompt = state.memory.prompts.get("answer_typed", "v2").render(
                query=p["query"], memory=body, required=outcome.retrieval.required or "description"
            )
            response = state.answer_client.complete(
                ChatRequest(
                    (Message("user", prompt),), state.answer_model, temperature=0.0, max_tokens=200
                )
            )
            result["answer"] = asdict(response)
            result["truncated"] = response.raw_finish_reason in {"length", "max_tokens"}
        return result

    def checkpoint(self, directory: Path) -> dict:
        directory = Path(directory)
        check(not directory.exists(), "Checkpoint destination exists")
        directory.mkdir(parents=True, mode=0o700)
        target = directory / "run.sqlite"
        dest = sqlite3.connect(target)
        try:
            self.db.backup(dest)
        finally:
            dest.close()
        os.chmod(target, 0o600)
        with target.open("rb") as stream:
            os.fsync(stream.fileno())
        manifest = {
            "schema": SCHEMA,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "committed_cursor": self.cursor,
            "commit_head": self.head,
            "pending_steps": self.db.execute("SELECT count(*) FROM intents").fetchone()[0]
            - self.cursor,
            "resources": self.resources(),
        }
        with (directory / "manifest.json").open("x") as stream:
            stream.write(canonical(manifest) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return manifest

    @classmethod
    def restore(cls, checkpoint: Path, destination: Path, *, fault=None):
        checkpoint, destination = Path(checkpoint), Path(destination)
        manifest = json.loads((checkpoint / "manifest.json").read_text())
        source = checkpoint / "run.sqlite"
        check(
            manifest["schema"] == SCHEMA
            and manifest["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest(),
            "Checkpoint database checksum mismatch",
        )
        check(not destination.exists(), "Restore destination exists")
        destination.mkdir(parents=True, mode=0o700)
        src = sqlite3.connect(source.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        dst = sqlite3.connect(destination / "run.sqlite")
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        os.chmod(destination / "run.sqlite", 0o600)
        result = cls(destination, fault=fault)
        if (
            result.cursor != manifest["committed_cursor"]
            or result.head != manifest["commit_head"]
            or result.resources() != manifest["resources"]
        ):
            result.close()
            raise LedgerError("Checkpoint cursor/head mismatch")
        return result
