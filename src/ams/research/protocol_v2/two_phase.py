"""Protocol v2, plan.md step 1.12 runtime fix 2 (owner-approved three-step version).

Why three steps: the paid stage is one process (single-writer guarded session) and the
original `pipeline.evaluate(answer=True)` recomputes every retrieval there. A free
precompute cannot simply be reused, because it answers conflict checks with the
placeholder "compatible": a real "contradict" reply marks claims contested, which adds
a "contested" label to the memory text in the prompt (`memory/typed.py`).

  1. FREE  `ConflictRecorder` precompute -> every distinct conflict-check request.
           They do not depend on the replies (selection never does; every served pair
           is checked; the request renders the raw claim texts) - tested.
     PAID  `send_conflicts`: those requests only, through the guarded v2_stage3 session
           (exactly what the original pipeline would send for them; ~3 per group).
  2. FREE  `build_contexts`: the precompute again, now replaying the REAL replies
           (`ReplayConflictSession`, no other call possible), storing per row the
           retrieved entries, the frozen answer template, the answer model and the
           conflict call ids. Parallel shards by group.
  3. PAID  `pipeline.evaluate(..., contexts=Contexts(...))`: reads those contexts,
           verifying the code version, the inputs fingerprint, the conditions, every
           blob and row hash, every row against its recomputation, and every conflict
           reply against the live paid ledger (exact reuse, $0; never a new call).

Rows, prompts, contested labels, retrieved contexts, model-call ids and the set of
paid requests are identical to the original pipeline (tests/test_v2_two_phase.py).
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path

from ams.core.prompts import Prompt
from ams.research.dynamic.models import canonical, check, digest
from ams.research.protocol_v2 import pipeline as PL
from ams.research.sequential.clients import request_from
from ams.research.workload.stage2 import ConflictPlaceholderSession

VERSION = "protocol-v2-two-phase-v1"
# Internal arms: their retrieval needs no paid call besides conflict checks. S2-ID needs
# MemLineage's paid classifier, so the paid stage computes it the original way.
CONTEXT_METHODS = ("static", "R", "C", "M", "S", "SL", "S2-BS")
REQUESTS, REPLIES, CONTEXTS = "conflict_requests.json", "conflict_replies.json", "contexts.sqlite"
_CONTESTED = re.compile(r"(?:^|\| |\n)contested\n")


def context_methods(methods) -> tuple:
    """The internal arms whose contexts `methods` read (published defences: their base)."""
    need = {(PL._published(m) or (None, m))[1] for m in methods}
    return tuple(m for m in CONTEXT_METHODS if m in need)


def _plain(value):
    return json.loads(canonical(value))


# ----------------------------------------------------------------------------- step 1


class ConflictRecorder(ConflictPlaceholderSession):
    """The Stage-2 placeholder (identical replies) that keeps each distinct request."""

    def __init__(self):
        super().__init__()
        self.requests = {}

    def dispatch(self, stage, request):
        self.requests.setdefault(request.cache_key("openrouter"), request)
        return super().dispatch(stage, request)


def save_requests(path: Path, recorder: ConflictRecorder):
    body = [asdict(recorder.requests[k]) for k in sorted(recorder.requests)]
    with Path(path).open("x") as f:
        f.write(canonical(body) + "\n")


def load_requests(paths) -> list:
    """The union of the shards' requests, in a fixed order."""
    out = {}
    for path in paths:
        for body in json.loads(Path(path).read_text()):
            request = request_from("chat", body)
            out[request.cache_key("openrouter")] = request
    return [out[k] for k in sorted(out)]


def send_conflicts(requests, session) -> list[dict]:
    """PAID in production (guarded v2_stage3 session): one dispatch per request."""
    replies = []
    for request in requests:
        check(request.max_tokens == 6, "Step 1 sends conflict checks only")
        call_id, result = session.dispatch("conflict", request)
        check(result.get("response") is not None,
              "A conflict check failed; inspect the ledger before step 2")  # fmt: skip
        replies.append({"request": _plain(asdict(request)), "call_id": call_id,
                        "response": _plain(result["response"])})  # fmt: skip
    return replies


def save_replies(path: Path, replies):
    with Path(path).open("x") as f:
        f.write(canonical(replies) + "\n")


def load_replies(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())


# ----------------------------------------------------------------------------- step 2


class ReplayConflictSession:
    """Step 2 (free): the real conflict replies of step 1; nothing else is possible."""

    def __init__(self, replies):
        self.replies, self.conflicts = {}, 0
        for r in replies:
            key = request_from("chat", r["request"]).cache_key("openrouter")
            self.replies[key] = (r["call_id"], r["response"])

    def dispatch(self, stage, request):
        check(stage == "conflict", "Step 2 replays only conflict checks; no answer calls")
        key = request.cache_key("openrouter")
        check(key in self.replies,
              "Conflict reply missing: run step 1 (conflicts) for these requests")  # fmt: skip
        self.conflicts += 1
        call_id, response = self.replies[key]
        return call_id, {"response": _plain(response)}


class _Writer:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.executescript(
            "CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE blobs(hash TEXT PRIMARY KEY, body TEXT NOT NULL);"
            "CREATE TABLE contexts(key TEXT PRIMARY KEY, body TEXT NOT NULL, "
            "hash TEXT NOT NULL); BEGIN;"
        )

    def _blob(self, text: str) -> str:
        h = digest(text)
        self.db.execute("INSERT OR IGNORE INTO blobs VALUES (?,?)", (h, text))
        return h

    def put(self, key, *, row, entries, required, template, answer_model, conflict_call_ids):
        check((template.name, template.version) == ("answer_typed", "v2"),
              "Unexpected answer template")  # fmt: skip
        body = {"row": _plain(row), "entries": self._blob(canonical(entries)),
                "template": self._blob(template.template), "required": required,
                "answer_model": answer_model,
                "conflict_call_ids": list(conflict_call_ids)}  # fmt: skip
        self.db.execute("INSERT INTO contexts VALUES (?,?,?)",
                        (key, canonical(body), digest(body)))  # fmt: skip

    def finish(self, manifest: dict):
        self.db.execute("INSERT INTO metadata VALUES ('manifest', ?)", (canonical(manifest),))
        self.db.execute("COMMIT")
        self.db.close()


def build_contexts(rows, stores, replies, out: Path, *, conditions, inputs: dict,
                   methods=CONTEXT_METHODS) -> dict:  # fmt: skip
    """Step 2 (free, no network needed): the precompute with the real conflict replies."""
    out = Path(out)
    check(set(methods) <= set(CONTEXT_METHODS), "Contexts are built for internal arms only")
    check(not out.exists(), "Refuse to overwrite an existing directory")
    out.mkdir(parents=True, mode=0o700)
    writer = _Writer(out / CONTEXTS)
    session = ReplayConflictSession(replies)
    result = PL.evaluate(rows, stores, session, out, conditions=conditions, methods=methods,
                         answer=False, contexts=writer)  # fmt: skip
    replies = _plain(replies)
    writer.finish({"version": VERSION, "pipeline": PL.VERSION, "inputs": inputs,
                   "conditions": list(conditions), "methods": list(methods),
                   "groups": sorted(s["group_id"] for s in stores), "replies": replies,
                   "replies_digest": digest(replies), "rows": result["rows"]})  # fmt: skip
    return {**result, "conflicts_replayed": session.conflicts}


# ----------------------------------------------------------------------------- step 3


class Contexts:
    """Step 3: the verified reader of one or more step-2 shards (disjoint groups)."""

    def __init__(self, dirs, *, inputs: dict):
        self.by_group, self._blobs, manifests = {}, {}, []
        for d in dirs:
            path = (Path(d) / CONTEXTS).resolve()
            check(path.exists(), f"No contexts in {d}")
            db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            row = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
            check(row is not None, f"Incomplete contexts in {d} (step 2 did not finish)")
            m = json.loads(row[0])
            check(m["version"] == VERSION and m["pipeline"] == PL.VERSION,
                  "Contexts were built by another code version")  # fmt: skip
            check(m["inputs"] == inputs, "Contexts were built from other inputs "
                  "(bundle / Stage-1 stores)")  # fmt: skip
            check(digest(m["replies"]) == m["replies_digest"], "Contexts replies hash mismatch")
            for g in m["groups"]:
                check(g not in self.by_group, f"Group {g} appears twice in the contexts")
                self.by_group[g] = db
            manifests.append(m)
        check(bool(manifests), "No contexts given")
        first = manifests[0]
        replies = {}
        for m in manifests:
            check((m["conditions"], m["methods"]) == (first["conditions"], first["methods"]),
                  "Contexts shards differ in conditions or methods")  # fmt: skip
            for r in m["replies"]:
                check(replies.setdefault(r["call_id"], r) == r, "Contexts shards disagree")
        self.conditions, self.methods = tuple(first["conditions"]), set(first["methods"])
        self.replies = [replies[k] for k in sorted(replies)]

    def check(self, conditions, groups):
        check(tuple(conditions) == self.conditions,
              "The paid stage's conditions differ from the contexts' conditions")  # fmt: skip
        missing = sorted(set(groups) - set(self.by_group))
        check(not missing, f"No contexts for groups {missing}")

    def verify(self, session):
        """Every replayed conflict reply equals the live paid ledger's (exact reuse, $0).
        A guarded session is checked first, so verification can never pay."""
        guarded = getattr(getattr(session, "gpt", session), "db", None)
        if guarded is not None:
            for r in self.replies:
                row = guarded.execute("SELECT status FROM dispatches WHERE call_id=?",
                                      (r["call_id"],)).fetchone()  # fmt: skip
                check(row is not None and row[0] == "completed", "A step-2 conflict reply is "
                      "not in the paid ledger; run step 1 on this session first")  # fmt: skip
        for r in self.replies:
            call_id, result = session.dispatch("conflict", request_from("chat", r["request"]))
            check(
                call_id == r["call_id"] and _plain(result["response"]) == r["response"],
                "A conflict reply differs from the paid ledger; the contexts are stale",
            )

    def has(self, method) -> bool:
        return method in self.methods

    def _blob(self, db, h) -> str:
        if h not in self._blobs:
            row = db.execute("SELECT body FROM blobs WHERE hash=?", (h,)).fetchone()
            check(row is not None and digest(row[0]) == h, "Context blob hash mismatch")
            self._blobs[h] = row[0]
        return self._blobs[h]

    def get(self, gid, condition, method, pid) -> dict:
        db = self.by_group[gid]
        row = db.execute("SELECT body, hash FROM contexts WHERE key=?",
                         (digest([gid, condition, method, pid]),)).fetchone()  # fmt: skip
        check(row is not None, f"No context for {gid} {condition} {method} {pid}")
        body = json.loads(row[0])
        check(digest(body) == row[1], "Context row hash mismatch")
        return {
            **body,
            "entries": json.loads(self._blob(db, body["entries"])),
            "template": Prompt("answer_typed", "v2", self._blob(db, body["template"])),
        }

    def contested_prompts(self) -> int:
        """Stored contexts carrying a "contested" label (real 'contradict' replies)."""
        n = 0
        for db in set(self.by_group.values()):
            for (h,) in db.execute("SELECT entries FROM (SELECT json_extract(body, "
                                   "'$.entries') AS entries FROM contexts)"):  # fmt: skip
                entries = json.loads(self._blob(db, h))
                n += any(_CONTESTED.search(e["text"]) for e in entries)
        return n
