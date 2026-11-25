"""One SAFE-Mem store per LoCoMo scenario, with exact provenance for the frozen policies.

Ingestion (SAFE-Mem's own LoCoMo path, `ams.eval.locomo.run_memory`): one store per conversation,
one `TypedStandingMemory.write_dialogue` per write, the orientation's speaker as principal, turn
text = `Turn.render().split(" said, ", 1)[-1]`, settings of `configs/v31_locomo_withhold_{a,b}.yaml`.

Contributions (= MPBench's write units, `workload.integration.construct`):
  session   the genuine turns of one LoCoMo session (both speakers), one dialogue write
  poison    one injected turn (v2 generator), its own dialogue write in its session, written right
            after the session (MPBench: every attack item is its own contribution)
  relay     one unknown-origin verbatim copy (v2 relay family), its own write
  embedded  [sensitivity family only] the session's genuine AND injected turns in one write
Every write has up to two roots, as in MPBench: (contribution, principal) and (contribution,
external). Claims are bound to the root of their SAFE-Mem source role; evidence chunks to the
external root unless every source turn is the principal's. Batch = LoCoMo session, context =
conversation, contributor = the external speaker (relay copies: attribution unknown).
"""

from __future__ import annotations

import json
from collections import defaultdict

from ams.core.prompts import PromptLibrary
from ams.eval.use_type import UseTypeClassifier
from ams.llm.types import EmbedRequest
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import Audit, EvidenceSnapshot, Finding, Policy, Provenance, Register, StoredRecord
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import canonical, check, digest, event_dict
from ams.research.retrieval import AccessSnapshot, ArtifactGrant, RecordBinding
from ams.research.retrieval.replay import ExactReplayClient
from ams.research.workload.integration import classifier_request

from locomo_safemem import governance as G
from locomo_safemem.clients import CHAT_MODEL, EMBED_MODEL

STORE_VERSION = "locomo-safemem-store-v1"
KEY = "conv"  # SAFE-Mem's per-conversation store key (one memory object per scenario)
ACCESS_VERSION = "native-all-allow-v1"  # MPBench's all-allow ACL version (integration.AUDIT_POLICY_VERSION)
AUDIT_LIMIT = 64
# configs/v31_locomo_withhold_{a,b}.yaml through ams/eval/build.py (SAFE-Mem's published LoCoMo setting)
SAFE_MEM = dict(mode="withhold", source_cap=None, hops=0, coreference=False, scoped=True, granularity=5,
                max_claims=20, detect_conflicts=True, extract_version="v1", conflict_version="v1",
                retention_version=None, endorsement="sentence", retention_sentence_version="v1",
                evidence_slots=4, index="flat", external_evidence=False, index_check=False, hub_cap=None,
                entity_merge=None, dialogue_extract_version="v1", temperature=0.0)
USE_TYPE_VERSION = "v2"  # prompts.classify_use_type in the v31 LoCoMo configs
RETRIEVE_K = 4  # retrieve_k in the v31 LoCoMo configs


def make_memory(chat, embed, prompts: PromptLibrary) -> TypedStandingMemory:
    return TypedStandingMemory(chat, CHAT_MODEL, embed_client=embed, embed_model=EMBED_MODEL,
                               use_type=UseTypeClassifier(chat, CHAT_MODEL, prompts, version=USE_TYPE_VERSION),
                               prompts=prompts, **SAFE_MEM)


def turn_text(rendered: str) -> str:
    """SAFE-Mem's LoCoMo turn text (`run_memory`): the rendered turn after "<speaker> said, "."""
    return rendered.split(" said, ", 1)[-1]


def plan(c, mem: dict, embedded: bool = False) -> list[dict]:
    """Chronological write plan for one scenario memory (v2 record list)."""
    recs = mem["records"]
    by_s = defaultdict(list)
    for i, r in enumerate(recs):
        by_s[r["session"]].append(i)
    out = []
    for si, s in enumerate(c.sessions):
        idx = by_s.get(si, [])
        inserted = [i for i in idx if recs[i]["target"] or recs[i]["relay_of"]]
        if embedded:
            groups = [("embedded" if inserted else "session", idx)]
        else:
            groups = [("session", [i for i in idx if i not in inserted])]
            groups += [("relay" if recs[i]["relay_of"] else "poison", [i]) for i in inserted]
        for kind, members in groups:
            if members:
                cid = f"s{si}" if kind in ("session", "embedded") else f"s{si}.r{members[0]}"
                out.append({"id": cid, "kind": kind, "session": si, "date": s.date_time, "records": members})
    check(sorted(i for p in out for i in p["records"]) == list(range(len(recs))), "Every turn written once")
    return out


def build(c, mem: dict, chat, embed, prompts: PromptLibrary, questions, *, store_id: str,
          embedded: bool = False, dump: bool = False) -> dict:
    """Write the scenario into Original SAFE-Mem, bind provenance, freeze query-time replay tables.
    `chat`: a Recorder (construction + classifier calls); `embed`: EmbedCache (local MiniLM)."""
    recs, principal = mem["records"], mem["principal"]
    memory = make_memory(chat, embed, prompts)
    graph = memory._graph(KEY)
    sources, records, grants = [], [], []
    roots = {}  # root_id -> {"contribution", "kind", "members": [(record_id, hash, kind, artifact)]}
    owner, root_of_turn, public = {}, {}, []
    diag = {"session_writes": 0, "session_writes_at_cap": 0, "poison_writes_with_claims": 0,
            "poison_writes_value_in_claim": 0, "ambiguous_chunks": 0, "external_chunks": 0, "principal_chunks": 0}
    for p in plan(c, mem, embedded):
        cid = f"{store_id}/{p['id']}"
        turns = [(recs[i]["speaker"], turn_text(recs[i]["text"])) for i in p["records"]]
        before, n_chunks = set(graph._sources), len(memory._chunks.get(KEY, ()))
        result = memory.write_dialogue(session_id=KEY, turns=turns, date=p["date"], principal=principal)
        new = [s for sid, s in graph._sources.items() if sid not in before]
        check(len(new) == len(turns) and all(s.text == t for s, (_, t) in zip(new, turns, strict=True)),
              "One SAFE-Mem source per written turn, in order")
        art, turn_of = {}, {}
        for j, (src, i) in enumerate(zip(new, p["records"], strict=True)):
            art[src.source_id], turn_of[src.source_id] = f"{cid}.t{j}", i
            sources.append(G.DialogueSourceBinding(KEY, src.source_id, art[src.source_id], digest(src.text),
                                                   str(src.role), src.principal_id))
            grants.append(ArtifactGrant(art[src.source_id], ("user", "audit_service"), ("read", "describe", "audit")))
        is_p = {s.source_id: str(s.role) in G.PRINCIPAL_ROLES for s in new}
        p_arts = tuple(art[s.source_id] for s in new if is_p[s.source_id])
        all_arts = tuple(art[s.source_id] for s in new)
        ext_speakers = sorted({recs[i]["speaker"] for i in p["records"] if recs[i]["speaker"] != principal})
        targets = [recs[i]["target"] for i in p["records"] if recs[i]["target"]]
        relays = [recs[i]["relay_of"] for i in p["records"] if recs[i]["relay_of"]]

        def bind(native, text, kind, source_ids, artifacts, principal_kind, dia=()):
            rid = "r_" + digest([STORE_VERSION, store_id, p["id"], native])[:24]
            root = "root_" + digest([STORE_VERSION, store_id, p["id"], principal_kind])[:24]
            records.append(RecordBinding(KEY, native, rid, digest(text), kind, tuple(source_ids), artifacts,
                                         principal_kind))
            r = roots.setdefault(root, {"contribution": p["id"], "kind": principal_kind, "members": []})
            r["members"].append((rid, digest(text), kind, artifacts[0]))
            owner[native] = {"contribution_id": p["id"], "contribution_kind": p["kind"], "kind": principal_kind,
                             "record_kind": kind, "root": root, "session": p["session"], "targets": targets,
                             "relay_of": relays, "speakers": ext_speakers, "dia_ids": list(dia)}
            return root

        sides = {"principal": 0, "external": 0}
        for entry in result.written:
            sides["principal" if is_p[graph.claim(entry.entry_id).source_id] else "external"] += 1
        if p["kind"] in ("session", "embedded"):
            diag["session_writes"] += 1
            diag["session_writes_at_cap"] += any(v >= SAFE_MEM["max_claims"] for v in sides.values())
        if p["kind"] == "poison":
            from locomo_v1 import build as _B1
            from locomo_v2.metrics import asr_hit as _hit

            texts = [graph.claim(e.entry_id).text for e in result.written]
            wrong = _B1.WRONG.search(recs[p["records"][0]]["text"]).group(1)
            diag["poison_writes_with_claims"] += bool(texts)
            diag["poison_writes_value_in_claim"] += any(_hit(t, wrong) for t in texts)
        for entry in result.written:
            claim = graph.claim(entry.entry_id)
            pk = "principal" if is_p[claim.source_id] else "external"
            src_ids = tuple(dict.fromkeys((claim.source_id, *claim.endorsed_by)))
            bind(claim.claim_id, claim.text, "claim", src_ids, p_arts if pk == "principal" else all_arts, pk)
        for chunk in memory._chunks.get(KEY, ())[n_chunks:]:
            flags = {is_p[s] for s in chunk.source_ids}
            # a chunk spanning both speakers' turns: the frozen rule forbids principal text in
            # contributor evidence, so it is "ambiguous" with an unknown-attribution root
            pk = "principal" if flags == {True} else "external" if flags == {False} else "ambiguous"
            diag[f"{pk}_chunks"] += 1
            bind(chunk.chunk_id, chunk.text, "evidence_chunk", chunk.source_ids,
                 tuple(dict.fromkeys(art[s] for s in chunk.source_ids)), pk,
                 [recs[turn_of[s]]["dia_id"] for s in chunk.source_ids if recs[turn_of[s]]["dia_id"]])
        ext_root = "root_" + digest([STORE_VERSION, store_id, p["id"], "external"])[:24]
        for src in new:
            if not is_p[src.source_id]:
                root_of_turn[turn_of[src.source_id]] = ext_root
        public.append({"contribution_id": p["id"], "kind": p["kind"], "session": p["session"],
                       "user_query": "\n".join(t for (spk, t) in turns if spk == principal),
                       "context": "\n".join(f"{spk}: {t}" for (spk, t) in turns if spk != principal),
                       "external_speakers": ext_speakers, "targets": targets, "relay_of": relays})
    # roots whose contribution produced no record of that kind are absent (never audited: checked)
    registers = []
    plan_by_id = {p["contribution_id"]: p for p in public}
    for root, r in sorted(roots.items()):
        p = plan_by_id[r["contribution"]]
        batch = f"{c.sample_id}:s{p['session']}"
        if r["kind"] == "principal":
            prov = Provenance(root, c.sample_id, None, None, "principal", principal_id=principal)
        elif p["kind"] == "relay" or r["kind"] == "ambiguous":
            prov = Provenance(root, c.sample_id, batch, None, "unknown")
        else:
            check(len(p["external_speakers"]) == 1, "One authenticated external speaker per contribution")
            prov = Provenance(root, c.sample_id, batch, p["external_speakers"][0], "authenticated_external")
        registers.append(Register("reg_" + digest(root)[:24], 0, prov,
                                  tuple(StoredRecord(rid, h, k, a) for rid, h, k, a in r["members"])))
    episode = "lsm-" + digest([STORE_VERSION, store_id])[:20]
    catalog = G.DialogueBindingCatalog(episode, tuple(sources), tuple(records))
    access = AccessSnapshot(ACCESS_VERSION, tuple(grants))
    evidence = EvidenceSnapshot(LedgerConfig(episode, "verified_audits", AUDIT_LIMIT), tuple(registers), 0)
    # query-time replay tables (MPBench `freeze_queries`): classifier replies + question embeddings only
    chats, embeds = {}, {}
    for q in sorted(set(questions)):
        req = classifier_request(prompts, q)
        chats[req.cache_key("openrouter")] = chat.complete(req)
        ereq = EmbedRequest((q,), EMBED_MODEL)
        embeds[ereq.cache_key("local")] = embed.embed(ereq)
    replay = ExactReplayClient(key_provider="openrouter", chats=chats)
    memory.client, memory.use_type.client = replay, replay
    memory.embed_client = ExactReplayClient(key_provider="local", embeddings=embeds)
    state = G.DialogueRuntimeState.create(memory, catalog, access, evidence, Policy("R"), seed=20261124)
    stats = {"claims": len(list(graph.claims())), "chunks": len(memory._chunks.get(KEY, ())),
             "contributions": len(public), "roots": len(roots),
             "poison_roots_with_claims": sum(1 for r in roots.values() if r["kind"] == "external"
                                             and plan_by_id[r["contribution"]]["kind"] == "poison"
                                             and any(m[2] == "claim" for m in r["members"])),
             "poison_contributions": sum(1 for p in public if p["kind"] == "poison"), **diag}
    return {"store_id": store_id, "version": STORE_VERSION, "conv": c.sample_id, "principal": principal,
            "session_id": KEY, "group_id": c.sample_id, "state": state, "snapshot": state.dump() if dump else None,
            "record_owner": owner,
            "root_of_turn": root_of_turn, "roots": {k: {**v, "members": [m[:2] for m in v["members"]]}
                                                    for k, v in roots.items()},
            "public": public, "stats": stats}


def audit_events(store: dict, audits, *, verifier: str = "oracle_by_construction") -> list[dict]:
    """v2 tickets [(turn index, verdict, use_id)] as frozen `Audit` events on the turn's root: every
    record of that root is a finding with the ticket's verdict (MPBench's complete-bundle rule)."""
    events = []
    for n, (i, verdict, use) in enumerate(audits, 1):
        check(i in store["root_of_turn"], f"Audited turn {i} has no external SAFE-Mem root")
        root = store["root_of_turn"][i]
        members = store["roots"][root]["members"]
        ref = "oracle_" + digest([store["store_id"], i, verdict, use])[:20]
        a = Audit("audit_" + digest([store["store_id"], n, root, use])[:24], n, f"t{n}_" + digest([i, use])[:12],
                  root, use, ACCESS_VERSION, verdict, tuple(Finding(r, h, verdict, ref) for r, h in members),
                  True, verifier, "controlled_audit", ref)
        events.append(json.loads(canonical(event_dict(a))))
    return events
