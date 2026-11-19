"""Determinism check: rebuild conv-30 into a temp dir; compare decompressed content and bytes."""
import gzip, hashlib, tempfile
from pathlib import Path
from locomo_v1.build import build_conversation
d = Path(tempfile.mkdtemp())
build_conversation("conv-30", d)
ref = Path("research_data/locomo_v1_freeze/build")
for suf in ("jobs.jsonl.gz", "contexts.jsonl.gz", "scenarios.json"):
    a, b = (p / f"conv-30.{suf}" for p in (d, ref))
    ra, rb = a.read_bytes(), b.read_bytes()
    ca, cb = (gzip.decompress(x) if suf.endswith(".gz") else x for x in (ra, rb))
    print(suf, "content_equal", ca == cb, "bytes_equal", ra == rb)
