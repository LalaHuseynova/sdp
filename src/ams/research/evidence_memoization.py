"""Scoped memoization of an immutable evidence revision; no decision-rule changes."""

from contextlib import contextmanager

from ams.research.dynamic.ledger import EvidenceSnapshot


@contextmanager
def memoized_evidence_revisions():
    """Cache by exact object identity, retaining the object to prevent ID reuse.

    Events/config are frozen dataclasses and tuples. Original serialization and
    hashing run on the first access; subsequent reads return that exact string.
    New snapshots, including corrections, always receive their own calculation.
    The class descriptor is restored even if execution raises. This is a scoped
    runtime optimization, not an edit to the original ledger or SAFE-Mem files.
    """
    original = EvidenceSnapshot.revision
    cache = {}
    stats = {"calculations": 0, "cache_hits": 0}

    def revision(snapshot):
        key = id(snapshot)
        if key not in cache:
            if len(cache) >= 128:
                cache.clear()
            cache[key] = (snapshot, original.fget(snapshot))
            stats["calculations"] += 1
        else:
            stats["cache_hits"] += 1
        return cache[key][1]

    EvidenceSnapshot.revision = property(revision)
    try:
        yield stats
    finally:
        EvidenceSnapshot.revision = original
