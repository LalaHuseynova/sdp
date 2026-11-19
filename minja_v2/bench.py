"""Per-pair benchmark, built with MINJA's own scripts (protocol §1.1, counts of paper §5.1).

The scripts are run unmodified; only their unseeded `random` is seeded from outside
(runpy after random.seed), and patient ids are drawn from the demo PATIENTS.csv. This
mirrors scripts/minja_run.sh with the paper's counts and two additions: a benign test set
(utility) and an explicitly seeded clean-stream shuffle.

Rev 3 adds the mixed-history streams: N_HISTORY ordinary queries asked by the attacker
(MINJA's data_create.py, seed + HISTORY_SEED_OFFSET) form a history phase that precedes
MINJA's attack stream, which follows byte for byte unchanged (hist_stream.json); the same
history precedes the clean stream (hist_clean_stream.json). The test sets are shared.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from . import protocol as P

SCRIPTS = P.EHR / "ehrsql-ehragent"


def _run_minja_script(script: str, args: list[str], seed: int, cwd: Path) -> None:
    """Run one of MINJA's data scripts as released, with `random` seeded first."""
    code = (
        "import random, runpy, sys\n"
        f"random.seed({int(seed)})\n"
        f"sys.argv = {[script, *args]!r}\n"
        f"runpy.run_path({str(SCRIPTS / script)!r}, run_name='__main__')\n"
    )
    env = {**os.environ, "MINJA_SEED": str(int(seed))}  # the patched scripts reseed with it
    subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, check=True,
                   stdout=subprocess.DEVNULL)  # fmt: skip


def _tag(path: Path, who) -> list[dict]:
    rows = json.loads(path.read_text())
    for n, r in enumerate(rows):
        r["principal"] = who(n)
    path.write_text(json.dumps(rows, indent=4))
    return rows


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(pair: dict, out: Path, counts: dict | None = None) -> dict:
    """Write attack_base, filler, poison_stream, clean_stream, victim_test, benign_test."""
    n = {"attack": P.N_ATTACK, "benign": P.N_BENIGN, "victim_test": P.N_VICTIM_TEST,
         "benign_test": P.N_BENIGN_TEST, "history": P.N_HISTORY, **(counts or {})}  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    v, t, s = int(pair["victim"]), int(pair["target"]), int(pair["seed"])
    csv = str(P.DEMO_TABLES / "PATIENTS.csv")
    templates = str(P.MINJA_DATA / "patient_only.json")
    filler_src = str(P.MINJA_DATA / "valid_preprocessed.json")

    _run_minja_script("data_create_poison.py", [templates, str(out / "attack_base.json"),
                      "--csv_file", csv, "--num_entries", str(n["attack"]),
                      "--generate_with_id", str(v)], s, out)  # fmt: skip
    _run_minja_script("data_create.py", [filler_src, str(out / "filler.json"), "--csv_file", csv,
                      "--num_entries", str(n["benign"])], s, out)  # fmt: skip
    _tag(out / "attack_base.json", lambda i: P.ATTACKER)
    _tag(out / "filler.json", lambda i: P.BENIGN_USERS[i % len(P.BENIGN_USERS)])
    _run_minja_script("add_poison.py", [str(out / "attack_base.json"), str(out / "filler.json"),
                      str(v), str(t), str(out / "poison_stream.json")], s, out)  # fmt: skip
    clean = json.loads((out / "attack_base.json").read_text()) + json.loads(
        (out / "filler.json").read_text())
    random.Random(s).shuffle(clean)
    (out / "clean_stream.json").write_text(json.dumps(clean, indent=4))
    _run_minja_script("data_create_poison.py", [templates, str(out / "victim_test.json"),
                      "--csv_file", csv, "--num_entries", str(n["victim_test"]),
                      "--generate_with_id", str(v)], s + P.VICTIM_TEST_SEED_OFFSET, out)  # fmt: skip
    _tag(out / "victim_test.json", lambda i: "victim")
    _run_minja_script("data_create.py", [filler_src, str(out / "benign_test.json"), "--csv_file",
                      csv, "--num_entries", str(n["benign_test"])],
                      s + P.BENIGN_TEST_SEED_OFFSET, out)  # fmt: skip
    _tag(out / "benign_test.json", lambda i: "tester")

    # rev 3: the mixed-history attacker's history phase, then MINJA's streams unchanged
    _run_minja_script("data_create.py", [filler_src, str(out / "history.json"), "--csv_file", csv,
                      "--num_entries", str(n["history"])], s + P.HISTORY_SEED_OFFSET, out)  # fmt: skip
    history = _tag(out / "history.json", lambda i: P.ATTACKER)
    for src, dst in (("poison_stream.json", "hist_stream.json"),
                     ("clean_stream.json", "hist_clean_stream.json")):
        tail = json.loads((out / src).read_text())
        (out / dst).write_text(json.dumps(history + tail, indent=4))

    stream = json.loads((out / "poison_stream.json").read_text())
    names = ("attack_base.json", "filler.json", "poison_stream.json", "clean_stream.json",
             "victim_test.json", "benign_test.json", "history.json", "hist_stream.json",
             "hist_clean_stream.json")  # fmt: skip
    info = {
        "pair": pair, "counts": n,
        "stream_length": len(stream),
        "attacker_records": sum(r.get("principal") == P.ATTACKER for r in stream),
        "history_records": len(history),
        "history_naming_victim": sum(str(v) in r["template"] for r in history),
        "benign_naming_victim": sum(str(v) in r["template"] for r in
                                    json.loads((out / "benign_test.json").read_text())
                                    + json.loads((out / "filler.json").read_text())),
        "hashes": {name: sha(out / name) for name in names},
    }  # fmt: skip
    (out / "bench.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


def questions(bench_dir: Path) -> list[str]:
    """Every question text the agent will see (stream and tests), for the precomputes."""
    names = ("poison_stream.json", "clean_stream.json", "victim_test.json", "benign_test.json",
             "hist_stream.json", "hist_clean_stream.json")  # fmt: skip
    return sorted({e["template"] for name in names
                   for e in json.loads((bench_dir / name).read_text())})  # fmt: skip
