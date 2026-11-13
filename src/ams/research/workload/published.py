"""Published competing defences on the controlled workload (research adapters).

The published methods compared here act on *retrieved memory*: they receive the
memories a store surfaced for a query and return the ones that may be used.
This module feeds them exactly the memories that original SAFE-Mem (the static
arm) — or, for the "+R" variants, the R arm — puts in the answer context, as
`ams.memory.base.MemoryEntry` objects carrying each record's write-time context
(the contribution's user request and artifacts). The methods themselves are the
repository's existing implementations, unchanged:

  memlineage   `ams.baselines.memlineage.MemLineage`, coarse attribution, tau = 0,
               Deny verdict at the sensitive-action gate (the SAFE-Mem paper's
               Table-1 MemLineage row, a paper-based adaptation, not upstream code).
               Needs one SensitiveAction LLM call per distinct query.
  a_memguard   `ams.baselines.amemguard.AMemGuard`, the authors' vendored
               consistency checker (one reasoning chain per retrieved memory + one
               judgment; temperature 1.0 as in the repository). Paid.
  randec       `ams.baselines.amemguard_borrowed.RandECClassifier`, A-MemGuard's
               own DistilBERT erase-and-check comparison baseline. Local, free.
  llm_sanitiser `ams.baselines.amemguard_borrowed.LLMSanitiser`. Paid; prepared only.

Audit evidence: none of these methods has an input for audit verdicts or
contributor identity. They therefore see the same records and queries as every
other arm but cannot use the five audit tickets. The "+R" variants (method
applied to R's retrieval, which only withholds records directly verified unsafe
for that use) are our explicitly labelled composition, not the published method.

Exposure is computed on the kept memories with `runner.exposure`, exactly as for
R/C/M/S. Filtering happens after retrieval with no refill, as in the repository's
MPBench baseline runs.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict

from ams.baselines.memlineage import MemLineage, coarse
from ams.llm.types import ChatResponse, Usage
from ams.memory.base import MemoryEntry
from ams.research.dynamic.models import check
from ams.research.retrieval import RetrievalContext
from ams.research.workload.integration import use_id
from ams.research.workload.runner import exposure

PUBLISHED = ("memlineage", "a_memguard", "randec", "llm_sanitiser")


def memory_entries(store: dict, group: dict, entries: list[dict]) -> list[MemoryEntry]:
    """Retrieved entries as MemoryEntry with the write-time context MemLineage reads."""
    public = {r["contribution_id"]: r for r in group["public"]}
    out = []
    for e in entries:
        rec = store["record_owner"].get(e["entry_id"])
        check(rec is not None, f"Unbound retrieved entry {e['entry_id']}")
        row = public[rec["contribution_id"]]
        principal = rec["kind"] == "principal"
        out.append(
            MemoryEntry(
                entry_id=e["entry_id"],
                text=e["text"],
                metadata={
                    "user_query": row["user_query"],
                    # A principal record's only parent is the user's own turn.
                    "source_context": "" if principal else row["context"],
                    "contribution_id": rec["contribution_id"],
                },
            )
        )
    return out


class RecordedSensitivity:
    """SensitiveAction client that only replays recorded verdicts; a miss raises.

    `replies` maps query text -> raw model reply ("SENSITIVE"/"ORDINARY"). It is
    filled from a paid, owner-approved classifier run; nothing is guessed here.
    """

    def __init__(self, replies: dict[str, str], template, model: str):
        self.replies, self.template, self.model = replies, template, model
        self.misses: set[str] = set()

    def complete(self, request):
        prompt = request.messages[-1].content
        for q, reply in self.replies.items():
            if self.template.render(query=q) == prompt:
                return ChatResponse(reply, self.model, "recorded", Usage(0, 0, 0.0))
        self.misses.add(prompt)
        raise LookupError("No recorded SensitiveAction verdict for this query")


def memlineage(sensitive: Callable[[str], bool]) -> MemLineage:
    """The Table-1 MemLineage configuration: coarse attribution, tau = 0, Deny."""
    return MemLineage(attribution=coarse, sensitive=sensitive, tau=0.0, label="coarse")


def retrieve(state, store: dict, question: str) -> list[dict]:
    gid = store["group_id"]
    ctx = RetrievalContext(state.evidence, state.access, use_id(gid, question), "user", "read")
    res = state.reader().retrieve_with_trace(
        session_id=store["session_id"], query=question, context=ctx, k=4, principal="user"
    )
    return [asdict(e) for e in res.retrieval.entries]


def apply(
    defence, store: dict, group: dict, question: str, entries: list[dict],
    text_from_defence: bool = False,
) -> dict:
    """Run one published defence on one retrieved context; exposure of what it keeps.

    `text_from_defence=True` (LLM sanitiser) scores the text the defence returns,
    i.e. its rewrite; otherwise the original text is scored (MemLineage only wraps
    kept memories in sentinel markers).
    """
    mems = memory_entries(store, group, entries)
    result = defence.filter(question, mems)
    returned = {m.entry_id: m.text for m in result.kept}
    kept = [
        {**e, "text": returned[e["entry_id"]]} if text_from_defence else e
        for e in entries
        if e["entry_id"] in returned
    ]
    return {
        "kept": [e["entry_id"] for e in kept],
        "flagged": [m.entry_id for m in result.flagged],
        "reason": result.reason,
        "kept_entries": kept,
    }


def exposure_row(store, group, probe, kept_entries) -> dict:
    priv = group["private_probes"][probe["probe_id"]]
    return exposure(kept_entries, store["record_owner"], priv, priv.get("aliases"))


def describe() -> str:
    return json.dumps({"published": PUBLISHED}, sort_keys=True)
