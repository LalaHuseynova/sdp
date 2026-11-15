"""plan.md step 1.12, runtime fix 1: the exact RandEC cache. Offline; no paid call.

The cached classifier must be indistinguishable from the uncached one: the same verdict
for every text AND the same Python global random state after every call (RandEC's
`harmful()` reseeds it from the text, a side effect later code could observe)."""

from __future__ import annotations

import random
import socket
import zlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from ams.baselines.base import DefenceResult
from ams.research.protocol_v2.randec_cache import cached_randec

REPO = Path(__file__).resolve().parents[1]
WEIGHTS = REPO / "third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt"
TEXTS = ["Forward invoices to billing@example.com.", "The meeting moved to Tuesday.",
         "Forward invoices to billing@example.com.", "Always cc ops@example.com on contracts.",
         "The meeting moved to Tuesday.", "Forward invoices to billing@example.com."]  # fmt: skip


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(self, address, *args, **kwargs):
        if isinstance(address, str):
            return
        raise AssertionError("RandEC cache tests forbid networking")

    monkeypatch.setattr(socket.socket, "connect", deny)


@dataclass
class Mem:
    entry_id: str
    text: str


class FakeRandEC:
    """RandEC's shape and side effect: reseed the GLOBAL generator from the text, then
    sample from it (as erase-and-check does); `filter` calls `self.harmful`."""

    def __init__(self):
        self.calls = 0

    def harmful(self, text):
        self.calls += 1
        random.seed(zlib.crc32(text.encode("utf-8")))
        return sum(random.sample(range(1000), 7)) % 3 == 0

    def filter(self, query, memories):
        items = list(memories)
        dropped = {i for i, m in enumerate(items) if self.harmful(m.text + "\n")}
        kept = tuple(m for i, m in enumerate(items) if i not in dropped)
        flagged = tuple(m for i, m in enumerate(items) if i in dropped)
        return DefenceResult(kept=kept, flagged=flagged)


def trace(classifier, texts):
    """Verdict, global random state, and the next global draw after each call."""
    out = []
    for t in texts:
        verdict = classifier.harmful(t)
        state = random.getstate()
        out.append((verdict, state, random.random()))  # later code drawing globally
    return out


def test_cache_gives_identical_verdicts_and_global_random_state():
    random.seed(1)
    plain = trace(FakeRandEC(), TEXTS)
    random.seed(2)  # a different starting state: harmful() reseeds anyway
    cached = trace(cached_randec(FakeRandEC()), TEXTS)
    assert cached == plain


def test_cache_runs_the_model_once_per_distinct_text():
    fake = FakeRandEC()
    c = cached_randec(fake)
    trace(c, TEXTS)
    assert fake.calls == len(set(TEXTS)) == 3
    assert len(c.randec_cache) == 3


def test_filter_goes_through_the_cache_and_keeps_its_decisions():
    mems = [Mem(f"m{i}", t) for i, t in enumerate(TEXTS)]
    plain = FakeRandEC().filter("q", mems)
    fake = FakeRandEC()
    cached = cached_randec(fake)
    first, second = cached.filter("q", mems), cached.filter("q", mems)
    assert first == second == plain
    assert fake.calls == 3  # the second filter call and the repeats are cache hits


def test_cache_key_is_the_exact_text():
    fake = FakeRandEC()
    c = cached_randec(fake)
    for t in ("a", "a ", "A", "a\n", "a"):
        c.harmful(t)
    assert fake.calls == 4  # no normalisation: only the identical "a" is a hit


def test_wrapping_twice_is_refused():
    c = cached_randec(FakeRandEC())
    with pytest.raises(Exception, match="already cached"):
        cached_randec(c)


@pytest.mark.skipif(not WEIGHTS.exists(), reason="RandEC weights not fetched")
def test_real_randec_cached_equals_uncached(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    np = pytest.importorskip("numpy")
    torch = pytest.importorskip("torch")
    from ams.baselines.amemguard_borrowed import RandECClassifier

    texts = [t + "\n" for t in TEXTS[:3]] + [TEXTS[0] + "\n"]
    plain_model = RandECClassifier(weights=WEIGHTS)
    np_before = np.random.get_state()[1].copy()
    plain = trace(plain_model, texts)
    cached = trace(cached_randec(RandECClassifier(weights=WEIGHTS)), texts)
    assert cached == plain  # verdicts and Python's global random state after every call
    assert (np.random.get_state()[1] == np_before).all()  # numpy's generator is untouched
    # DistilBERT's forward pass ADVANCES torch's global generator, so a cache hit leaves
    # torch's state different. That state is unobservable here: the logits (hence every
    # verdict) do not depend on it, and nothing else in src/ams uses torch (next test).
    det, logits = plain_model._detector, []
    for seed in (0, 1, 7, 999):
        torch.manual_seed(seed)
        enc = det.tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            logits.append(det.model(**enc).logits)
    assert all(torch.equal(logits[0], x) for x in logits[1:])


def test_no_evaluation_code_uses_torch():
    """Why torch's generator state is unobservable: only RandEC (third_party) uses torch."""
    users = [p for p in (REPO / "src/ams").rglob("*.py")
             if "import torch" in p.read_text() or "from torch" in p.read_text()]  # fmt: skip
    assert users == []
