#!/usr/bin/env python3
"""Archive (and later re-verify) exactly the files locked protocol v1 hashed.

    archive --protocol research_data/workload_freeze_v4_20261108/locked_protocol_v1.json
    verify  --protocol research_data/workload_freeze_v4_20261108/locked_protocol_v1.json

The locked test is complete. New research code (adaptive attacks, protocol v2)
adds source files, so `freeze_locked_protocol.py verify` on the live tree will
report differences from then on. This archive keeps protocol v1 checkable for
ever: `archive` first runs the live verify (it must pass), then writes every
hashed file (dataset, src/ams, prompts, scripts, configs) into one tar.gz next
to the protocol, with its own SHA-256. `verify` re-reads the archive and checks
every member against the protocol hashes, with no dependence on the live tree.
Offline; no model call.
"""

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GROUPS = ("dataset_files", "source_files", "prompt_files", "scripts", "configs")


def expected(protocol: dict) -> dict:
    out = {}
    for group in GROUPS:
        out.update(protocol["hashes"][group])
    return out


def paths(protocol_path: Path):
    archive = protocol_path.with_name(protocol_path.stem + "_frozen_files.tar.gz")
    return archive, archive.with_suffix("").with_suffix(".json")


def archive(args):
    subprocess.run(
        [sys.executable, str(REPO / "scripts/freeze_locked_protocol.py"), "verify",
         "--protocol", str(args.protocol)],
        check=True,
    )  # fmt: skip
    protocol = json.loads(args.protocol.read_text())
    files = expected(protocol)
    out, record = paths(args.protocol)
    if out.exists():
        raise SystemExit(f"{out} exists; archives are never overwritten")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=9) as tar:
        for rel in sorted(files):
            data = (REPO / rel).read_bytes()
            if hashlib.sha256(data).hexdigest() != files[rel]:
                raise SystemExit(f"{rel} changed since the freeze")
            info = tarfile.TarInfo(rel)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    body = buf.getvalue()
    out.write_bytes(body)
    summary = {
        "protocol": str(args.protocol.relative_to(REPO)),
        "protocol_digest": protocol["protocol_digest"],
        "archive": str(out.relative_to(REPO)),
        "archive_sha256": hashlib.sha256(body).hexdigest(),
        "files": len(files),
        "by_group": {g: len(protocol["hashes"][g]) for g in GROUPS},
    }
    record.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def verify(args):
    protocol = json.loads(args.protocol.read_text())
    files = expected(protocol)
    out, record = paths(args.protocol)
    meta = json.loads(record.read_text())
    body = out.read_bytes()
    diffs = []
    if hashlib.sha256(body).hexdigest() != meta["archive_sha256"]:
        diffs.append("archive checksum")
    seen = {}
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
        for m in tar.getmembers():
            seen[m.name] = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
    diffs += [f for f in files if seen.get(f) != files[f]]
    diffs += [f for f in seen if f not in files]
    print(json.dumps({"status": "verified" if not diffs else "differs", "files": len(seen),
                      "diffs": diffs[:20]}))  # fmt: skip
    if diffs:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("archive", "verify"))
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    args.protocol = args.protocol.resolve()
    archive(args) if args.command == "archive" else verify(args)


if __name__ == "__main__":
    main()
