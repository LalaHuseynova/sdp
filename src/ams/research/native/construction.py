"""Original write calls observed at explicit construction boundaries, not ID guesses."""

from __future__ import annotations

from ams.core.spans import segment
from ams.memory.typed import TypedStandingMemory, split_artifacts
from ams.research.dynamic import Provenance, Register, StoredRecord
from ams.research.dynamic.models import check, digest
from ams.research.phase1_data import source_parts
from ams.research.retrieval import (
    AccessSnapshot,
    ArtifactGrant,
    BindingCatalog,
    RecordBinding,
    SourceBinding,
)


def validate_source(row):
    check(
        set(row)
        == {"contribution_id", "context_id", "user_query", "context", "artifacts", "payload_hash"},
        "Only allowlisted public source inputs accepted",
    )
    check(row["payload_hash"] == digest([row["user_query"], row["context"]]), "Input bytes changed")
    check(
        row["artifacts"] == source_parts(row["contribution_id"], row["user_query"], row["context"]),
        "Artifact construction/spans differ",
    )


class ObservedMemory(TypedStandingMemory):
    """Only observe source allocation; all memory decisions call the original code."""

    def begin_contribution(self, session, source):
        validate_source(source)
        self._observed_source = source
        self._observed_session = session
        self._sources_before = set(self._graph(session)._sources)
        self._source_map = {}
        self._source_spans = {}

    def _bind_roots(self, graph):
        if self._source_map:
            return
        source = self._observed_source
        artifacts = source["artifacts"]
        roots = [v for k, v in graph._sources.items() if k not in self._sources_before][
            : len(artifacts)
        ]
        # Original write creates principal + external artifact roots before indexing.
        check(len(roots) == len(artifacts), "Incomplete root creation boundary")
        check(
            [a["text"] for a in artifacts[1:]] == split_artifacts(source["context"]),
            "Original external artifact boundaries differ",
        )
        for root, artifact in zip(roots, artifacts, strict=True):
            role = "external_body" if artifact["role"] == "external" else "principal_turn"
            check(
                root.text == artifact["text"] and str(root.role) == role,
                "Root creation order/text differs",
            )
            self._source_map[root.source_id] = artifact["artifact_id"]
            self._source_spans[root.source_id] = {
                "artifact_id": artifact["artifact_id"],
                "start": 0,
                "end": len(root.text),
                "quote": root.text,
            }

    def _index_sentences(self, graph, session_id, src):
        self._bind_roots(graph)
        parent = self._source_map[src.source_id]
        before = set(graph._sources)
        # No change to embeddings, cut, standing, next/previous links or indexing.
        super()._index_sentences(graph, session_id, src)
        created = [s for sid, s in graph._sources.items() if sid not in before]
        sentences = segment(src.text)
        check(len(created) == len(sentences), "Unexpected sentence source construction")
        cursor = 0
        for node, span in zip(created, sentences, strict=True):
            start = src.text.find(span.text, cursor)
            check(start >= 0 and node.text == span.text, "Sentence source span differs")
            end = start + len(span.text)
            self._source_map[node.source_id] = parent
            self._source_spans[node.source_id] = {
                "artifact_id": parent,
                "start": start,
                "end": end,
                "quote": span.text,
            }
            cursor = end

    def finish_contribution(self, session):
        graph = self._graph(session)
        self._bind_roots(graph)  # Also handles empty/unindexed artifacts.
        actual = set(graph._sources) - self._sources_before
        check(set(self._source_map) == actual, "Unmapped native sources")
        return dict(self._source_map), dict(self._source_spans)


def compare_and_bind(
    memory,
    session,
    source,
    written,
    new_chunks,
    recovered_claims,
    recovered_chunks,
    historical_written,
):
    """Exact text/order/type/standing/structural-parent checks; never infer authorship."""
    check(
        len(written) == len(recovered_claims) == len(historical_written),
        "Frozen claim count changed",
    )
    check(len(new_chunks) == len(recovered_chunks), "Frozen chunk count changed")
    mapping, spans = memory.finish_contribution(session)
    graph = memory._graph(session)
    pid = source["contribution_id"]
    sources = tuple(
        SourceBinding(
            session,
            sid,
            aid,
            digest(graph.source(sid).text),
            str(graph.source(sid).role),
            graph.source(sid).principal_id,
        )
        for sid, aid in mapping.items()
    )
    records, links = [], []
    grouped = {"principal": [], "unknown": []}
    all_artifacts = tuple(a["artifact_id"] for a in source["artifacts"])
    for entry, recovered, historical in zip(
        written, recovered_claims, historical_written, strict=True
    ):
        claim = graph.claim(entry.entry_id)
        check(
            claim.text == recovered["text"] and digest(claim.text) == recovered["content_hash"],
            "Frozen extracted claim text/order changed; reannotation required",
        )
        for key in ("claim_type", "standing", "usable_as", "subject", "raw_text", "contested"):
            check(
                entry.metadata[key] == historical["metadata"][key],
                "Historical claim metadata differs",
            )
        check(
            mapping[claim.source_id] == recovered["legacy_parent_artifact_id"],
            "Historical structural claim parent changed",
        )
        parent_ids = tuple(dict.fromkeys((claim.source_id, *claim.endorsed_by)))
        principal = graph.source(claim.source_id).principal_id is not None
        # The original _overlap result is preserved structurally, but carries NO
        # contributor penalty before independently checked semantic attribution.
        origin = "principal" if principal else "ambiguous"
        parents = (
            tuple(dict.fromkeys(mapping[s] for s in parent_ids)) if principal else all_artifacts
        )
        record = RecordBinding(
            session,
            claim.claim_id,
            recovered["record_id"],
            digest(claim.text),
            "claim",
            parent_ids,
            parents,
            origin,
        )
        records.append(record)
        grouped["principal" if principal else "unknown"].append(
            StoredRecord(
                record.record_id, record.content_hash, record.record_kind, mapping[claim.source_id]
            )
        )
        links.append(
            {
                "contribution_id": pid,
                "native_id": claim.claim_id,
                "record_id": record.record_id,
                "record_kind": "claim",
                "content_hash": record.content_hash,
                "structural_artifact_id": mapping[claim.source_id],
                "policy_artifact_ids": list(parents),
                "semantic_attribution": "principal_structural_source"
                if principal
                else "unknown_pending_review",
                "support_spans": recovered["proposed_support_spans"],
                "support_spans_status": "unreviewed_literal_candidates",
                "historical_text_and_visible_metadata_match": True,
                "historical_object_relation_state_verified": False,
            }
        )
    for chunk, recovered in zip(new_chunks, recovered_chunks, strict=True):
        parents = tuple(dict.fromkeys(mapping[s] for s in chunk.source_ids))
        exact_spans = [spans[s] for s in chunk.source_ids]
        check(
            chunk.text == recovered["text"] and digest(chunk.text) == recovered["content_hash"],
            "Frozen evidence text/order changed",
        )
        check(
            parents == (recovered["source_artifact_id"],)
            and exact_spans == recovered["source_spans"],
            "Historical chunk artifact/span relationship changed",
        )
        principal = all(graph.source(s).principal_id == "user" for s in chunk.source_ids)
        origin = "principal" if principal else "external"
        record = RecordBinding(
            session,
            chunk.chunk_id,
            recovered["record_id"],
            digest(chunk.text),
            "evidence_chunk",
            chunk.source_ids,
            parents,
            origin,
        )
        records.append(record)
        grouped["principal" if principal else "unknown"].append(
            StoredRecord(record.record_id, record.content_hash, record.record_kind, parents[0])
        )
        links.append(
            {
                "contribution_id": pid,
                "native_id": chunk.chunk_id,
                "record_id": record.record_id,
                "record_kind": "evidence_chunk",
                "content_hash": record.content_hash,
                "structural_artifact_id": parents[0],
                "policy_artifact_ids": list(parents),
                "semantic_attribution": "principal_structural_source"
                if principal
                else "unknown_pending_review",
                "support_spans": exact_spans,
                "historical_text_and_source_spans_match": True,
            }
        )
    registers = []
    for group, members in grouped.items():
        if members:
            root = "root_" + digest([pid, group])[:24]
            origin = Provenance(
                root,
                source["context_id"],
                None,
                None,
                "principal" if group == "principal" else "unknown",
                principal_id="user" if group == "principal" else None,
            )
            registers.append(Register("register_" + digest(root)[:24], 0, origin, tuple(members)))
    return sources, tuple(records), tuple(registers), links, spans


def sidecars(episode, source_bindings, record_bindings, sources):
    catalog = BindingCatalog(episode, tuple(source_bindings), tuple(record_bindings))
    grants = tuple(
        ArtifactGrant(a["artifact_id"], ("user", "audit_service"), ("read", "describe", "audit"))
        for row in sources
        for a in row["artifacts"]
    )
    return catalog, AccessSnapshot("native-all-allow-v1", grants)
