"""Archive a finished run folder into a verified .tar.gz (owner-approved 17 Nov 2026, to free disk).

Usage: python3 archive_dir.py DIR OUT_DIR
1. SHA-256 of every file in DIR -> OUT_DIR/DIR.sha256.json
2. DIR -> OUT_DIR/DIR.tar.gz
3. Re-read every archive member and compare its SHA-256 with the manifest
4. Only if all match (same file set, same hashes): delete DIR.
Restore: tar xzf OUT_DIR/DIR.tar.gz (then compare with the manifest).
"""

import hashlib, json, shutil, sys, tarfile
from pathlib import Path


def sha(f):
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
    return h.hexdigest()


src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(exist_ok=True)
manifest_path, archive = out / f"{src.name}.sha256.json", out / f"{src.name}.tar.gz"
assert src.is_dir() and not archive.exists() and not manifest_path.exists()
files = sorted(p for p in src.rglob("*") if p.is_file())
manifest = {}
for p in files:
    with open(p, "rb") as f:
        manifest[str(p)] = sha(f)
manifest_path.write_text(json.dumps({"files": manifest, "bytes": sum(p.stat().st_size for p in files)}, indent=1))
with tarfile.open(archive, "w:gz") as t:
    for p in files:
        t.add(p, arcname=str(p))
seen = {}
with tarfile.open(archive, "r:gz") as t:
    for m in t:
        if m.isfile():
            seen[m.name] = sha(t.extractfile(m))
assert seen == manifest, "archive does not match the manifest; originals kept"
shutil.rmtree(src)
print(json.dumps({"archived": str(src), "files": len(manifest), "archive": str(archive),
                  "archive_bytes": archive.stat().st_size, "verified": True, "original_deleted": True}))
