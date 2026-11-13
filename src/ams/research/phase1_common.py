"""Deterministic, standard-library-only Phase 1 primitives."""

from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

MASTER_SEED = 20261028
SCHEMA = "mpbench-phase1-v1"
CONTEXTS = ("email", "file_and_doc")
ARMS = ("R", "C", "M", "S")
RAW_HASHES = {
    "adversarial_data.jsonl.jsonl": (
        "f2d23a5a2d483889eb2fdd9a2a082f0759603bc0a17664814a7caafbd318f90d"
    ),  # noqa: E501
    "benign_data.jsonl.jsonl": "707ef7e311e147d9818a8a9e04293296fc6bf3390241e4cac23c8145765b62d5",
}
PROTOCOL_HASH = "5d5824e682ac58f5aabbf49be6827dca6ba0a3f6163391c1426b7562caa58c2a"


class PreparationError(ValueError):
    """Invalid or insufficient preparation evidence; never substitute labels."""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage_seed(bag: str, scenario: str, stage: str) -> int:
    """First 64 SHA-256 bits; each UTF-8 component has an 8-byte length prefix."""
    parts = (str(MASTER_SEED), str(bag), scenario, stage)
    payload = b"".join(len(p.encode()).to_bytes(8, "big") + p.encode() for p in parts)
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def rng(bag: str, stage: str, scenario: str = "COMMON") -> random.Random:
    return random.Random(stage_seed(bag, scenario, stage))


def opaque(kind: str, *parts: object) -> str:
    return kind + "_" + digest([MASTER_SEED, *parts])[:24]


def read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise PreparationError(f"{path}:{n}: expected object")
                rows.append(row)
    return rows


def write_json(path: str | Path, value: object, *, private: bool = False) -> None:
    _write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", private)


def write_jsonl(path: str | Path, rows: list[dict], *, private: bool = False) -> None:
    _write(path, "".join(canonical(row) + "\n" for row in rows), private)


def _write(path: str | Path, text: str, private: bool) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if private:
        os.chmod(target.parent, 0o700)
        for ancestor in target.parents:
            if ancestor.name == "private":
                os.chmod(ancestor, 0o700)
                break
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(target, flags, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    if private:
        os.chmod(target, 0o600)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise PreparationError(reason)
