"""Read-only reuse of construction replies already paid for (no network, $0).

`PaidReplayCache` serves an exact request again only if the shared guarded
session holds a *completed* workload construction dispatch with the identical
request key (the key covers model, messages, temperature and max_tokens). It
never writes to the session and never touches billing. `CacheChain` tries the
frozen reproduction cache first, then the replay, and keeps per-layer counts.

Because v2 leaves every attack, seed, linked copy, principal control and probe
question byte-identical to v1, their v1 Stage-1 replies are reused unchanged.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import check
from ams.research.recovery.offline import OfflineMiss


class PaidReplayCache:
    def __init__(self, dispatch_db: Path):
        check(Path(dispatch_db).is_file(), f"Missing dispatch ledger {dispatch_db}")
        conn = sqlite3.connect(f"file:{Path(dispatch_db).resolve()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only=ON")
        self.replies, self.counts = {}, Counter()
        for key, result in conn.execute(
            "SELECT request_key,result FROM dispatches "
            "WHERE stage LIKE 'workload_%' AND status='completed' AND result_hash IS NOT NULL"
        ):
            response = json.loads(result)["response"]
            check(response is not None, "Completed dispatch without a response")
            previous = self.replies.setdefault(key, response)
            check(previous["text"] == response["text"], "Conflicting replies for one request")
        conn.close()

    def get(self, key: str, kind: str, provider: str, model: str):
        if kind == "chat" and provider == "openrouter" and key in self.replies:
            response = self.replies[key]
            check(response.get("model") == model, "Replayed reply model mismatch")
            self.counts["paid_replay_hit"] += 1
            return {**response, "provider": provider}, {"source": "paid_replay"}
        raise OfflineMiss("No paid replay")


class CacheChain:
    def __init__(self, *layers):
        self.layers = [layer for layer in layers if layer is not None]
        self.counts = Counter()

    def get(self, key: str, kind: str, provider: str, model: str):
        for i, layer in enumerate(self.layers):
            try:
                found = layer.get(key, kind, provider, model)
            except OfflineMiss:
                continue
            self.counts[f"layer{i}_{kind}_hit"] += 1
            return found
        self.counts[f"{kind}_miss"] += 1
        raise OfflineMiss(f"No cached {kind} response")


class EvaluationReplaySession:
    """Runner session: serve an already-paid identical Stage-3 request at $0, else forward.

    Keys are (evaluation stage, request key) of *completed* workload dispatches in
    the shared ledger, read once, read-only. Anything else goes to `inner` (the
    guarded live session, or a counting mock for cost estimates). The inner
    session's own exact-reuse and budget checks still apply to forwarded calls.
    """

    def __init__(self, dispatch_db: Path, inner, scope_hash: str):
        """`scope_hash`: only replies paid under this scope are replayed, so the replayed
        text is exactly what that run saw (temperature-0 replies can differ by scope)."""
        from ams.research.dynamic.models import digest
        from ams.research.workload.transport import evaluation_stage

        self._stage_of = evaluation_stage
        conn = sqlite3.connect(f"file:{Path(dispatch_db).resolve()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only=ON")
        self.replies = {}
        for call_id, stage, key, result in conn.execute(
            "SELECT call_id,stage,request_key,result FROM dispatches WHERE stage IN "
            "('workload_answer','workload_no_memory_answer','workload_conflict','workload_judge')"
            " AND status='completed' AND result_hash IS NOT NULL"
        ):
            if call_id != digest([scope_hash, stage, key]):
                continue
            response = json.loads(result)["response"]
            check((stage, key) not in self.replies, "Duplicate reply in one scope")
            self.replies[(stage, key)] = response
        conn.close()
        check(bool(self.replies), "No replies under the given scope")
        self.inner, self.counts = inner, Counter()

    def dispatch(self, stage, request):
        s = self._stage_of(stage, request)
        key = request.cache_key("openrouter")
        if (s, key) in self.replies:
            self.counts[f"replay:{s}"] += 1
            return "replay_" + key[:24], {"response": self.replies[(s, key)]}
        self.counts[f"forward:{s}"] += 1
        return self.inner.dispatch(stage, request)


class CountingMockSession:
    """Cost-estimate inner session: mock replies, one count per *distinct* new request."""

    def __init__(self, mock):
        self.mock, self.seen, self.chars = mock, {}, Counter()

    def dispatch(self, stage, request):
        from dataclasses import asdict

        from ams.research.workload.transport import evaluation_stage

        s = evaluation_stage(stage, request)
        key = (s, request.cache_key("openrouter"))
        if key not in self.seen:
            self.seen[key] = sum(len(m.content) for m in request.messages)
        response = self.mock.complete(request)
        return "mock_" + key[1][:24], {"response": asdict(response)}

    def tally(self) -> dict:
        out = Counter()
        for (s, _), chars in self.seen.items():
            out[f"{s}:requests"] += 1
            out[f"{s}:chars"] += chars
        return dict(out)
