"""LLM / embedding clients for construction and query time.

  EmbedCache       local MiniLM (`ams.llm.providers.local_client`, the model SAFE-Mem uses) behind a
                   persistent text->vector cache, so identical texts are embedded once (free).
  Recorder         wraps a chat backend (paid strict client or mock); records every request key and
                   response so the query-time replay tables can be frozen exactly (MPBench's
                   `freeze_queries` pattern).
  MockLLM          deterministic stand-in for GPT-4o-mini in tests and dry runs only. It reads the
                   original rendered prompts (dialogue extraction, use-type classifier, conflict,
                   LoCoMo answer and judge) and replies in the formats the original parsers expect.
                   Mock outcomes have no scientific meaning.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from pathlib import Path

from ams.llm.types import ChatResponse, EmbedRequest, EmbedResponse, Usage

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHAT_MODEL = "openai/gpt-4o-mini"


def _h(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


class EmbedCache:
    """Local MiniLM with a persistent sqlite cache keyed by the exact text."""

    provider = "local"

    def __init__(self, path: Path | None, backend=None):
        self.path, self._backend, self._mem, self._lock = path, backend, {}, threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(str(path), timeout=300, check_same_thread=False)
            self.db.execute("CREATE TABLE IF NOT EXISTS v (k TEXT PRIMARY KEY, vec TEXT)")
        else:
            self.db = None

    def backend(self):
        if self._backend is None:
            from ams.llm.providers.local_client import LocalEmbeddingClient

            self._backend = LocalEmbeddingClient(model=EMBED_MODEL)
        return self._backend

    def _get(self, text):
        if text in self._mem:
            return self._mem[text]
        if self.db is not None:
            row = self.db.execute("SELECT vec FROM v WHERE k=?", (text,)).fetchone()
            if row:
                self._mem[text] = tuple(json.loads(row[0]))
                return self._mem[text]
        return None

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        with self._lock:
            out = {t: self._get(t) for t in request.texts}
            miss = list(dict.fromkeys(t for t, v in out.items() if v is None))
            if miss:
                vecs = self.backend().embed(EmbedRequest(tuple(miss), request.model)).vectors
                for t, v in zip(miss, vecs, strict=True):
                    v = tuple(float(x) for x in v)
                    self._mem[t] = out[t] = v
                    if self.db is not None:
                        self.db.execute("INSERT OR IGNORE INTO v VALUES (?,?)", (t, json.dumps(v)))
                if self.db is not None:
                    self.db.commit()
            return EmbedResponse(tuple(out[t] for t in request.texts), request.model, "local", Usage(0, 0, 0.0))


class Recorder:
    """Chat wrapper that records (request key -> response) for exact replay tables."""

    def __init__(self, backend):
        self.backend, self.chats, self.n = backend, {}, 0
        self._lock = threading.Lock()

    @property
    def provider(self):
        return getattr(self.backend, "provider", "recorder")

    def complete(self, request):
        key = request.cache_key("openrouter")
        with self._lock:
            if key in self.chats:
                return self.chats[key]
        response = self.backend.complete(request)
        with self._lock:
            self.chats[key] = response
            self.n += 1
        return response


# ----------------------------------------------------------------------------- mock (tests only)
WRONG_RE = re.compile(r"By the way, about (.+?): it is (.+?)\.?\"?$")


class MockLLM:
    """Prompt-aware deterministic mock. `contradict_share` of same-predicate pairs contradict."""

    provider = "mock"

    def __init__(self, contradict_share: int = 3):
        self.served, self.contradict_share = [], contradict_share

    def _r(self, text, request):
        return ChatResponse(text, request.model, "mock", Usage(len(request.messages[-1].content) // 4, 8, 0.0),
                            raw_finish_reason="stop")

    def complete(self, request):
        body = request.messages[-1].content
        if "Return a JSON object with at most" in body and "Session:\n" in body:
            self.served.append("extract")
            return self._r(self._extract(body), request)
        if "Answer on one line as: kind | person" in body:
            self.served.append("classify")
            q = body.split("Question:\n", 1)[1].split("\n\nAnswer on one", 1)[0]
            who = re.findall(r"\b([A-Z][a-z]+)\b", q[1:])
            return self._r(("attribute" if _h(q) % 4 == 0 else "description") + " | "
                           + (who[0] if who else "none"), request)
        if "Answer with one word and nothing else." in body and "Claim A:" in body:
            self.served.append("conflict")
            return self._r("contradict" if _h(body) % self.contradict_share == 0 else "compatible", request)
        if "Short answer:" in body:
            self.served.append("answer")
            return self._r(self._answer(body), request)
        if "Answer with one word, CORRECT or WRONG." in body:
            self.served.append("judge")
            gold = body.split("Gold answer: ", 1)[1].split("\n", 1)[0].lower()
            pred = body.split("Generated answer: ", 1)[1].split("\n", 1)[0].lower()
            ok = bool(set(re.findall(r"\w{3,}", gold)) & set(re.findall(r"\w{3,}", pred)))
            return self._r("CORRECT" if ok else "WRONG", request)
        raise AssertionError("MockLLM received an unrecognised prompt")

    def _extract(self, body: str) -> str:
        limit = int(re.search(r"at most (\d+) claims", body).group(1))
        lines = [ln for ln in body.split("Session:\n", 1)[1].split("\n\nReturn a JSON", 1)[0].split("\n")
                 if ": " in ln]
        claims = []
        for ln in lines:
            who, text = ln.split(": ", 1)
            text = text.strip().strip('"')
            m = WRONG_RE.search(text)
            if m:
                claims.append({"text": f"{who} said that {m.group(1)} is {m.group(2)}.", "type": "attribute",
                               "subject": who, "relation": "fact " + m.group(1)[:20], "object": ""})
            elif len(text.split()) >= 4:
                rel = ("said", "likes", "plans", "did", "has")[_h(text) % 5]
                claims.append({"text": f"{who}: {text[:160]}", "type": "description", "subject": who,
                               "relation": rel, "object": ""})
        return json.dumps({"claims": claims[:limit]})

    def _answer(self, body: str) -> str:
        q = body.rsplit("Question:", 1)[1].split("Short answer:", 1)[0].strip().lower()
        for ln in body.split("\n"):
            m = re.search(r"said that (.+?) is (.+?)\.", ln)
            if m and set(re.findall(r"\w{4,}", m.group(1).lower())) & set(re.findall(r"\w{4,}", q)):
                return m.group(2)
        words = re.findall(r"[A-Za-z0-9]+", " ".join(body.split("\n")[2:6]))
        return " ".join(words[:4]) or "unknown"

    def embed(self, request):  # not used: embeddings are always the local MiniLM
        raise AssertionError("MockLLM does not embed")
