"""Parallel passes over the experiment matrix (free; no network in any pass).

Modes (the chat backend answers SAFE-Mem's construction + classifier calls; the conflict backend
answers SAFE-Mem's query-time conflict checks):
  dry         construction only; extraction -> '{"claims": []}', classifier -> 'description | none';
              records every construction request exactly (the P1a prefetch list and its estimate)
  mock        MockLLM for everything (free end-to-end test; outcomes meaningless)
  precompute  construction replayed from the paid P1a cache; conflicts answered 'compatible' and
              recorded (MPBench P-B1's placeholder pass: conflicts never change selection)
  final       construction from the P1a cache, conflicts from the paid P1c cache -> build/
Shards = (conversation, orientation, draw); the no-attack frame store is its own shard per
orientation. A cache miss in precompute/final fails the shard (never a silent fallback).
"""

from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import sqlite3
import threading
import time
import traceback
from pathlib import Path

from ams.llm.types import ChatRequest, ChatResponse, Message, Usage
from ams.research.dynamic.models import check, digest

from locomo_safemem import config as K

ROOT = K.REPO / "research_data" / "locomo_safemem"
EMBED_CACHE = Path.home() / ".locomo_safemem_embed.sqlite"
RANDEC_CACHE = Path.home() / ".locomo_safemem_randec.sqlite"


def req_dict(request) -> dict:
    check(len(request.messages) == 1 and request.messages[0].role == "user", "One user message expected")
    return {"content": request.messages[0].content, "model": request.model, "temperature": request.temperature,
            "max_tokens": request.max_tokens}


def req_from(d: dict):
    return ChatRequest((Message("user", d["content"]),), d["model"], temperature=d["temperature"],
                       max_tokens=d["max_tokens"])


class DryLLM:
    """Construction recorder: neutral replies, every request kept (exact prompts)."""

    provider = "dry"

    def __init__(self):
        self.requests, self.lock = {}, threading.Lock()

    def complete(self, request):
        with self.lock:
            self.requests.setdefault(request.cache_key("openrouter"), req_dict(request))
        body = request.messages[-1].content
        text = '{"claims": []}' if "Return a JSON object with at most" in body else "description | none"
        return ChatResponse(text, request.model, "dry", Usage(0, 0, 0.0), raw_finish_reason="stop")


class CacheReplay:
    """Answers only from a paid stage's response cache (same keys as the strict client)."""

    provider = "replay"

    def __init__(self, path: Path):
        check(path.exists(), f"Missing paid cache {path}")
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.misses = 0

    def complete(self, request):
        key = request.cache_key("openrouter")
        row = self.db.execute("SELECT payload FROM responses WHERE key = ?", (key,)).fetchone()
        if row is None:
            self.misses += 1
            raise LookupError(f"Paid response missing from the cache: {key[:16]}")
        hit = json.loads(row[0])
        return ChatResponse(hit["text"], hit["model"], hit["provider"], Usage(**hit["usage"]), cached=True,
                            raw_finish_reason=hit.get("raw_finish_reason"))


class RecordingConflicts:
    """Placeholder conflict backend for `precompute`: 'compatible', requests recorded."""

    def __init__(self):
        self.requests = {}

    def complete(self, request):
        self.requests.setdefault(request.cache_key("openrouter"), req_dict(request))
        return ChatResponse("compatible", request.model, "placeholder", Usage(0, 0, 0.0), raw_finish_reason="stop")


class PersistentRandEC:
    """Frozen RandEC with an exact persistent verdict cache (MPBench runtime fix 1: a verdict is a
    function of the text alone); the classifier is loaded only on a miss."""

    def __init__(self, path=RANDEC_CACHE):
        self.db = sqlite3.connect(str(path), timeout=300, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS v (t TEXT PRIMARY KEY, harmful INTEGER)")
        self.db.commit()
        self._clf, self._mem = None, {}

    def _model(self):
        if self._clf is None:
            from ams.baselines.amemguard_borrowed import RandECClassifier

            self._clf = RandECClassifier(upstream_root=Path("/mnt/c/Users/HP/Documents/sdp"))
        return self._clf

    def harmful(self, text: str) -> bool:
        if text not in self._mem:
            row = self.db.execute("SELECT harmful FROM v WHERE t = ?", (text,)).fetchone()
            if row is None:
                v = bool(self._model().harmful(text))
                self.db.execute("INSERT OR IGNORE INTO v VALUES (?, ?)", (text, int(v)))
                self.db.commit()
            else:
                v = bool(row[0])
            self._mem[text] = v
        return self._mem[text]

    def filter(self, query, memories):
        """`RandECClassifier.filter`, unchanged logic, with the cached `harmful`."""
        from ams.baselines.base import DefenceResult

        items = list(memories)
        dropped = {i for i, m in enumerate(items) if self.harmful(m.text + "\n")}
        return DefenceResult(kept=tuple(m for i, m in enumerate(items) if i not in dropped),
                             flagged=tuple(m for i, m in enumerate(items) if i in dropped),
                             reason="RandEC/DistilBERT (suffix)")


# ----------------------------------------------------------------------------- shards
def shards(convs) -> list[tuple]:
    out = []
    for cid in convs:
        for p in K.ORIENTATIONS:
            out.append((cid, p, None))
            out += [(cid, p, d) for d in range(K.DRAWS)]
    return out


def _items(c, pidx, draw, families):
    from locomo_safemem import scenarios as SN

    fams = families or ("loc", "sybil", "shift", "relay", "frame", "embed")
    if draw is None:
        items = SN.plan(c, families=("frame",) if "frame" in fams else ())
    else:
        items = SN.plan(c, families=tuple(f for f in fams if f != "frame"), draws=[draw])
    return [i for i in items if i["pidx"] == pidx]


def work(spec: dict) -> dict:
    """One shard in a worker process; writes <out>/shards/<id>.json.gz and returns a summary."""
    from ams.core.prompts import PromptLibrary
    from ams.data.locomo import load_locomo
    from locomo_v1 import build as B1

    from locomo_safemem import evaluate as EV
    from locomo_safemem import governance as G
    from locomo_safemem import store as ST
    from locomo_safemem.clients import EmbedCache, MockLLM, Recorder

    cid, pidx, draw, mode, out = spec["conv"], spec["pidx"], spec["draw"], spec["mode"], Path(spec["out"])
    if spec.get("qlimit"):
        check(mode in ("mock", "dry") and "smoke" in str(out), "Question limit is for smoke tests only")
        EV.QLIMIT = int(spec["qlimit"])
    sid = f"{cid}_o{pidx}_{'frame' if draw is None else f'd{draw}'}"
    path = out / "shards" / f"{sid}.json.gz"
    if path.exists():
        return {"shard": sid, "skipped": True}
    t0 = time.time()
    try:
        c = {x.sample_id: x for x in load_locomo(K.DATA)}[cid]
        items = _items(c, pidx, draw, spec.get("families"))
        embed = EmbedCache(EMBED_CACHE)
        prompts = PromptLibrary()
        if mode == "dry":
            chat = DryLLM()
        elif mode == "mock":
            chat = MockLLM()
        else:
            chat = CacheReplay(Path(spec["construction_cache"]))
        conflicts = {"mock": MockLLM(), "precompute": RecordingConflicts()}.get(mode)
        if mode == "final":
            conflicts = CacheReplay(Path(spec["conflict_cache"]))
        verdicts = B1.load_verdicts()
        defences = EV.Defences(verdicts)  # RandEC runs as its own stage (`randec_stage`), like P2
        session = EV.ConflictSession(conflicts)
        qs = sorted((q for q in c.qa if q.category in K.QA_CATEGORIES), key=lambda q: q.qid)[:EV.QLIMIT]
        jobs, ctxs, metas, static_loc, timing = [], {}, [], [], []
        with G.fast_runtime() as dstats:
            for item in items:
                if mode == "dry":
                    rec = Recorder(chat)
                    st = ST.build(c, item["mem"], rec, embed, prompts, [q.question for q in qs], store_id=item["store"],
                                  embedded=item["embedded"])
                    metas.append({"store": item["store"], "stats": st["stats"]})
                    continue
                j, cx, m = EV.evaluate_store(c, item, Recorder(chat), embed, prompts, session, verdicts, defences,
                                             timing=timing, keep_static=item["family"] in K.PAID_PUBLISHED_FAMILIES)
                m["strata"] = EV.strata(c, item)
                static_loc += m.pop("static_export", [])
                jobs += j
                ctxs.update(cx)
                metas.append(m)
        body = {"shard": sid, "mode": mode, "jobs": jobs, "ctxs": ctxs, "metas": metas, "static_loc": static_loc,
                "timing": timing, "seconds": round(time.time() - t0, 1),
                "construction_requests": getattr(chat, "requests", {}) if mode == "dry" else {},
                "conflict_requests": getattr(conflicts, "requests", {}) if mode == "precompute" else {},
                "conflict_calls": session.calls, "conflict_contradictions": session.contradictions, "conflict_distinct_keys": sorted(session.requests), "sentinel_checked": EV._counter["checked"],
                "decide_stats": dict(dstats), "retrievals": EV._counter["n"]}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt") as fh:
            json.dump(body, fh)
        tmp.rename(path)
        return {"shard": sid, "seconds": body["seconds"], "jobs": len(jobs), "retrievals": EV._counter["n"]}
    except Exception as exc:  # noqa: BLE001  (reported; the pass fails closed)
        return {"shard": sid, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}


def reuse_precompute(final_out: Path, precompute_out: Path, conflict_cache: Path) -> dict:
    """Exact shortcut for the final pass: a precompute shard whose recorded conflict checks ALL got the
    reply the placeholder gave ('compatible', no 'contradict') produced exactly the final contexts, so
    it is copied; only shards with at least one real 'contradict' reply are recomputed."""
    db = sqlite3.connect(f"file:{conflict_cache}?mode=ro", uri=True)
    copied, todo = [], []
    (final_out / "shards").mkdir(parents=True, exist_ok=True)
    for f in sorted((precompute_out / "shards").glob("*.json.gz")):
        with gzip.open(f, "rt") as fh:
            body = json.load(fh)
        contradicts = False
        for key in body["conflict_requests"]:
            row = db.execute("SELECT payload FROM responses WHERE key = ?", (key,)).fetchone()
            check(row is not None, f"Conflict reply missing for {key[:16]}")
            contradicts |= "contradict" in json.loads(row[0])["text"].strip().lower()
        if contradicts:
            todo.append(f.name)
        else:
            body["mode"] = "final(reused precompute: no contradiction among its conflict checks)"
            with gzip.open(final_out / "shards" / f.name, "wt") as fh:
                json.dump(body, fh)
            copied.append(f.name)
    return {"copied": len(copied), "recompute": len(todo)}


def run_pass(mode: str, out: Path, convs=K.CONVS, workers: int = 8, families=None, **paths) -> dict:
    specs = [{"conv": c, "pidx": p, "draw": d, "mode": mode, "out": str(out), "families": families, **{
        k: str(v) for k, v in paths.items()}} for c, p, d in shards(convs)]
    if families and "frame" not in families:
        specs = [s for s in specs if s["draw"] is not None]
    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers, maxtasksperchild=4) as pool:
        results = list(pool.imap_unordered(work, specs))
    errors = [r for r in results if "error" in r]
    summary = {"mode": mode, "shards": len(specs), "errors": errors, "seconds": round(time.time() - t0, 1)}
    (out / f"pass_{mode}.json").write_text(json.dumps(summary, indent=1))
    return summary


def merge(out: Path, build: Path, convs=K.CONVS) -> dict:
    """Shard files -> per-conversation build files (v2 job format) + the stage exports."""
    from locomo_safemem import evaluate as EV

    stats = {"jobs": 0, "contexts": 0, "construction_requests": {}, "conflict_requests": {}, "static_loc": 0,
             "retrievals": 0, "sentinel_checked": 0, "seconds": 0.0}
    for cid in convs:
        jobs, ctxs, metas, static_loc = [], {}, [], []
        for f in sorted((out / "shards").glob(f"{cid}_o*.json.gz")):
            with gzip.open(f, "rt") as fh:
                b = json.load(fh)
            jobs += b["jobs"]
            ctxs.update(b["ctxs"])
            metas += b["metas"]
            static_loc += b["static_loc"]
            stats["construction_requests"].update(b["construction_requests"])
            stats["conflict_requests"].update(b["conflict_requests"])
            stats["retrievals"] += b.get("retrievals", 0)
            stats["sentinel_checked"] += b.get("sentinel_checked", 0)
            stats["seconds"] += b["seconds"]
        if jobs:
            EV.write_build(build, cid, jobs, ctxs, metas)
        if static_loc:
            with gzip.open(build / f"{cid}.static_loc.json.gz", "wt") as fh:
                json.dump(static_loc, fh)
        stats["jobs"] += len(jobs)
        stats["contexts"] += len(ctxs)
        stats["static_loc"] += len(static_loc)
    return stats


def write_requests(path: Path, requests: dict) -> None:
    with gzip.open(path, "wt") as fh:
        for k in sorted(requests):
            fh.write(json.dumps({"key": k, **requests[k]}) + "\n")


def read_requests(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    for r in rows:
        check(req_from(r).cache_key("openrouter") == r["key"], "Request does not reproduce its cache key")
    return rows


def digest_requests(rows) -> str:
    return digest(sorted(r["key"] for r in rows))


# ----------------------------------------------------------------------------- RandEC stage (free)
def _randec_worker(texts):
    clf = PersistentRandEC()
    return {t: clf.harmful(t) for t in texts}


def randec_stage(build: Path, convs=K.CONVS, workers: int = 10) -> dict:
    """Frozen RandEC on the static contexts of the loc stores (the scope of the paid published
    defences): every distinct entry text is decided once (exact persistent cache), in parallel, then
    `published.apply` filters each context (no refill) and the jobs are appended to the build."""
    from ams.core.prompts import PromptLibrary
    from ams.data.locomo import load_locomo
    from ams.research.workload import published as P
    from locomo_v1 import build as B1

    from locomo_safemem import evaluate as EV
    from locomo_safemem import paid as PD

    exports = {}
    for cid in convs:
        f = build / f"{cid}.static_loc.json.gz"
        if f.exists():
            with gzip.open(f, "rt") as fh:
                exports[cid] = json.load(fh)
    texts = sorted({e["text"] + "\n" for xs in exports.values() for x in xs for es in x["static"].values() for e in es})
    clf = PersistentRandEC()
    todo = [t for t in texts if clf.db.execute("SELECT 1 FROM v WHERE t = ?", (t,)).fetchone() is None]
    t0 = time.time()
    if todo:
        chunks = [todo[i::workers * 4] for i in range(workers * 4)]
        with mp.get_context("spawn").Pool(workers) as pool:
            for _ in pool.imap_unordered(_randec_worker, [c for c in chunks if c]):
                pass
    clf = PersistentRandEC()
    prompts = PromptLibrary()
    data = {c.sample_id: c for c in load_locomo(K.DATA)}
    added = 0
    for cid, xs in exports.items():
        jobs, ctxs = [], {}
        for x in xs:
            for qid in sorted(x["static"]):
                kept = P.apply(clf, {"record_owner": x["owner"]}, {"public": x["public"]}, x["questions"][qid],
                               x["static"][qid])["kept_entries"]
                text = EV._context(prompts, data[cid], kept)
                h = B1.chash(text)
                ctxs.setdefault(h, text)
                for d in x["draws"]:
                    jobs.append({"cell": f"{x['family']}|{cid}|o{x['pidx']}|{x['variant']}|d{d}|-|randec", "qid": qid,
                                 "ctx": h, "kept": [e["entry_id"] for e in kept]})
        PD._append_build(build, cid, jobs, ctxs)
        added += len(jobs)
    return {"distinct_texts": len(texts), "newly_decided": len(todo), "seconds": round(time.time() - t0, 1),
            "jobs_added": added}
