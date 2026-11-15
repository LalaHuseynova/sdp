"""Protocol v2, plan.md step 1.12 runtime fix 1 (owner-approved): an exact RandEC cache.

RandEC (`ams.baselines.amemguard_borrowed.RandECClassifier`, unchanged) decides each
memory with `harmful(text)`, which reseeds Python's GLOBAL random generator from the text
and then samples erased subsequences. So both its verdict and the global random state it
leaves behind are functions of the text alone. Its input, Original SAFE-Mem's retrieval,
is identical in every condition (step 1.12 measurement), so the same texts are decided in
all 272 conditions.

`cached_randec` memoizes `harmful` by the exact text and, on a hit, restores the global
random state the real call left, so the cached classifier is indistinguishable from the
uncached one, side effect included. RandEC touches neither torch's nor numpy's generator
(tested on the real model).
"""

from __future__ import annotations

import random

from ams.research.dynamic.models import check


def cached_randec(classifier):
    """Wrap `classifier.harmful` in place (an instance attribute, so the class's own
    `filter` uses it); returns the same object. The frozen class is not modified."""
    check(not hasattr(classifier, "randec_cache"), "RandEC classifier is already cached")
    inner = classifier.harmful
    memo: dict[str, tuple[bool, object]] = {}

    def harmful(text: str) -> bool:
        if text not in memo:
            verdict = inner(text)
            memo[text] = (verdict, random.getstate())
        verdict, state = memo[text]
        random.setstate(state)
        return verdict

    classifier.harmful = harmful
    classifier.randec_cache = memo
    return classifier
