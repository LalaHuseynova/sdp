#!/usr/bin/env python3
"""Archive (and later verify) the full research state before protocol v2.

    archive --out research_data/archive_pre_protocol_v2_20261113
    verify  --out research_data/archive_pre_protocol_v2_20261113

`archive` writes, never overwriting:
  code_and_docs.tar.gz   full copy: src/, scripts/, tests/, prompts/, configs/, root
                         *.md docs, pyproject.toml, uv.lock
  results_small.tar.gz   full copy of reports/**/*.md and every summary / analysis /
                         estimate JSON, Markdown and PNG under research_data/
  file_hashes.jsonl      SHA-256 + size of EVERY file under research_data/ and reports/
                         (multi-GB stores and journals are fingerprinted, not copied)
  manifest.json          counts, archive checksums, git HEAD, timestamp
`verify` re-hashes the two archives and every fingerprinted file still present and
reports changed or missing files. Offline; no model call.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE = ["src", "scripts", "tests", "prompts", "configs"]
ROOT_FILES = ["pyproject.toml", "uv.lock"]
SMALL_SUFFIXES = {".md", ".png"}
SMALL_JSON = ("summary", "analysis", "estimate", "comparison", "verdicts", "manifest")
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (SKIP_PARTS & set(p.parts)):
            yield p


def tar(paths, out: Path, exclude: Path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as t:
        for p in paths:
            if exclude in p.parents:
                continue
            info = tarfile.TarInfo(str(p.relative_to(REPO)))
            data = p.read_bytes()
            info.size, info.mtime, info.mode = len(data), int(p.stat().st_mtime), 0o644
            t.addfile(info, io.BytesIO(data))
    out.write_bytes(buf.getvalue())
    return hashlib.sha256(out.read_bytes()).hexdigest()


def small_result(p: Path) -> bool:
    if p.suffix in SMALL_SUFFIXES:
        return True
    return p.suffix == ".json" and any(k in p.name for k in SMALL_JSON) and p.stat().st_size < 5e6


def archive(out: Path):
    if out.exists():
        raise SystemExit(f"{out} exists; archives are never overwritten")
    out.mkdir(parents=True)
    code = [p for d in CODE for p in files(REPO / d)]
    code += [REPO / f for f in ROOT_FILES if (REPO / f).exists()]
    code += sorted(REPO.glob("*.md"))
    results = [p for d in ("reports", "research_data") for p in files(REPO / d)]
    small = [p for p in results if small_result(p)]
    code_sha = tar(code, out / "code_and_docs.tar.gz", out)
    small_sha = tar(small, out / "results_small.tar.gz", out)
    n = 0
    with (out / "file_hashes.jsonl").open("w") as f:
        for p in results:
            if out in p.parents:
                continue
            f.write(json.dumps({"path": str(p.relative_to(REPO)), "bytes": p.stat().st_size,
                                "sha256": sha(p)}) + "\n")  # fmt: skip
            n += 1
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()  # fmt: skip
    manifest = {
        "purpose": "Snapshot of all implementation and results before protocol v2 (13 Nov 2026)",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_head": head,
        "note": "Research code is untracked in git; this archive is the authoritative copy.",
        "code_and_docs": {"files": len(code), "sha256": code_sha},
        "results_small": {"files": len(small), "sha256": small_sha},
        "fingerprinted_result_files": n,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def verify(out: Path):
    m = json.loads((out / "manifest.json").read_text())
    issues = []
    for name, key in (("code_and_docs.tar.gz", "code_and_docs"), ("results_small.tar.gz",
                                                                    "results_small")):  # fmt: skip
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != m[key]["sha256"]:
            issues.append(f"archive changed: {name}")
    changed = missing = 0
    for line in (out / "file_hashes.jsonl").read_text().splitlines():
        r = json.loads(line)
        p = REPO / r["path"]
        if not p.exists():
            missing += 1
        elif p.stat().st_size != r["bytes"] or sha(p) != r["sha256"]:
            changed += 1
            if len(issues) < 20:
                issues.append(f"changed: {r['path']}")
    print(json.dumps({"status": "verified" if not issues and not missing else "differs",
                      "changed": changed, "missing": missing, "issues": issues[:20]}))  # fmt: skip


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("archive", "verify"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    out = a.out if a.out.is_absolute() else REPO / a.out
    archive(out) if a.command == "archive" else verify(out)


if __name__ == "__main__":
    main()
