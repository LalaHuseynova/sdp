"""Read-only cache access, original pure algorithms and a hard network guard."""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import math
import socket
import sqlite3
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from ams.core.spans import cosine
from ams.research.phase1_common import PreparationError, require

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHAT_MODEL = "openai/gpt-4o-mini"
STATUSES = (
    "directly_recovered",
    "reconstructed_verified",
    "reconstructed_unverified",
    "unavailable_offline",
)


class OfflineMiss(PreparationError):
    pass


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@contextlib.contextmanager
def no_network():
    def denied(*args, **kwargs):
        raise RuntimeError("Offline preparation forbids all network connections")

    with (
        patch.object(socket.socket, "connect", denied),
        patch.object(socket.socket, "connect_ex", denied),
        patch.object(socket, "create_connection", denied),
        patch.object(socket, "getaddrinfo", denied),
    ):
        yield


def embed_key(texts: list[str]) -> str:
    return request_key({"provider": "local", "model": EMBED_MODEL, "texts": texts})


def request_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ReadOnlyCache:
    """No normal ResponseCache/client: construction cannot create tables or call APIs.

    Immutable SQLite access avoids modifying existing SHM/WAL files. A nonempty WAL
    is refused instead of silently ignoring committed rows or checkpointing inputs.
    """

    def __init__(self, paths: list[Path]):
        self.connections = []
        self.counts = Counter()
        for path in paths:
            require(path.is_file(), f"Missing existing cache: {path}")
            wal = Path(str(path) + "-wal")
            require(
                not wal.exists() or wal.stat().st_size == 0,
                f"Nonempty WAL needs a separately captured consistent snapshot: {path}",
            )
            conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
            conn.execute("PRAGMA query_only=ON")
            self.connections.append((str(path), conn))

    def get(self, key: str, kind: str, provider: str, model: str) -> tuple[dict, dict]:
        for path, conn in self.connections:
            row = conn.execute(
                "SELECT provider,model,kind,payload FROM responses WHERE key=?", (key,)
            ).fetchone()
            if row:
                require(row[:3] == (provider, model, kind), "Cache key/provider/model mismatch")
                data = json.loads(row[3])
                require(
                    data.get("provider") == provider and data.get("model") == model,
                    "Cached response metadata mismatch",
                )
                self.counts[f"{kind}_hit"] += 1
                return data, {
                    "cache_path": path,
                    "request_key": key,
                    "response_hash": hashlib.sha256(row[3].encode()).hexdigest(),
                }
        self.counts[f"{kind}_miss"] += 1
        raise OfflineMiss(f"No saved {kind} response for {key}; no fallback permitted")

    def vectors(self, texts: list[str]) -> tuple[list, dict]:
        data, receipt = self.get(embed_key(texts), "embed", "local", EMBED_MODEL)
        vectors = data.get("vectors", [])
        require(len(vectors) == len(texts), "Embedding count mismatch")
        sizes = {len(v) for v in vectors}
        require(len(sizes) == 1 and next(iter(sizes)) > 0, "Invalid embedding dimensions")
        require(
            all(isinstance(x, (int, float)) and math.isfinite(x) for v in vectors for x in v),
            "Invalid embedding values",
        )
        return vectors, receipt

    def close(self):
        for _, c in self.connections:
            c.close()


def original_cut(path: Path):
    """Compile only the existing pure cut function, without importing memory/LLM factories."""
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "cut")
    cap = next(
        n.value.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "MAX_CHUNK_CHARS" for t in n.targets)
    )
    require(type(cap) is int, "Unrecognized original chunk cap")
    module = ast.Module(
        body=[*ast.parse("from __future__ import annotations").body, node], type_ignores=[]
    )
    namespace = {"cosine": cosine, "MAX_CHUNK_CHARS": cap}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["cut"]
