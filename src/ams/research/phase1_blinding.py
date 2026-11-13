"""Keyed public IDs prevent recovering hidden bag/profile seeds by ID enumeration."""

from __future__ import annotations

import copy
import hashlib
import hmac
import re

from ams.research.phase1_common import ARMS, digest, require
from ams.research.phase1_scenarios import validate_episode

_ID = re.compile(r"[a-z]+_[0-9a-f]{24}\Z")
_TEXT = {
    "text",
    "context",
    "user_query",
    "task",
    "intended_use",
    "retrieval_query",
    "expected_memory",
    "quote",
    "evidence_quote",
    "rationale",
    "question",
    "answers",
}


def keyed_id(value: str, key: bytes) -> str:
    require(len(key) == 32, "Identifier blinding needs a 32-byte private key")
    return (
        value.split("_", 1)[0]
        + "_"
        + hmac.new(key, value.encode(), hashlib.sha256).hexdigest()[:24]
    )


def blind_episode(episode: dict, key: bytes) -> dict:
    """Recode metadata IDs only; preserve every original source/question/quote byte."""
    id_map = {}

    def rewrite(value, field=""):
        if field in _TEXT:
            return copy.deepcopy(value)
        if isinstance(value, str) and _ID.fullmatch(value):
            id_map[value] = keyed_id(value, key)
            return id_map[value]
        if isinstance(value, dict):
            return {rewrite(k): rewrite(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        return value

    result = rewrite(episode)
    result["private"]["identifier_mapping"] = id_map
    result["shared_arm_inputs"] = {
        arm: digest([result["public_inputs"], result["private"]["events"]]) for arm in ARMS
    }
    validate_episode(result)
    return result
