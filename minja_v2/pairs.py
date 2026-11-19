"""Victim–target pairs on the MIMIC-III demo (protocol §1.3): valid, disjoint, drawn by seed.

A patient is valid if it answers at least MIN_ANSWERABLE of MINJA's patient-question SQL
templates (patient id substituted exactly as data_create_poison.py does) with a non-empty
result on the demo database. Pairs never share a patient. No outcome is used.
"""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

from . import protocol as P


def substitute(entry: dict, new_id: int) -> dict:
    """data_create_poison.replace_subject_id_consistently, without the optional note."""
    cur = entry["value"]["patient_id"]
    out = dict(entry)
    for s in ("value", "query", "question", "tag", "template"):
        if s in out:
            out[s] = str(out[s]).replace(str(cur), str(new_id))
    return out


def answerable(con: sqlite3.Connection, sql: str) -> bool:
    try:
        rows = con.execute(sql).fetchall()
    except sqlite3.Error:
        return False
    return any(any(v is not None and str(v) != "" for v in r) for r in rows)


def answerable_counts(db: Path, templates: list[dict]) -> dict[int, int]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    patients = [r[0] for r in con.execute("select distinct subject_id from patients order by 1")]
    return {p: sum(answerable(con, substitute(t, p)["query"]) for t in templates) for p in patients}


def draw(counts: dict[int, int], seed: int = P.PAIR_SEED, n_pilot: int = P.N_PILOT_PAIRS,
         n_result: int = P.N_RESULT_PAIRS, minimum: int = P.MIN_ANSWERABLE) -> dict:  # fmt: skip
    """Pilot pairs first, then result pairs; every patient at most once."""
    valid = sorted(p for p, c in counts.items() if c >= minimum)
    need = 2 * (n_pilot + n_result)
    if len(valid) < need:
        raise ValueError(f"{len(valid)} valid patients; {need} needed for disjoint pairs")
    order = valid[:]
    random.Random(seed).shuffle(order)
    pairs = []
    for k in range(n_pilot + n_result):
        victim, target = order[2 * k], order[2 * k + 1]
        role = "pilot" if k < n_pilot else "result"
        idx = k if role == "pilot" else k - n_pilot
        pairs.append({
            "pair_id": f"{'PILOT' if role == 'pilot' else 'P'}{idx:02d}",
            "role": role, "victim": victim, "target": target,
            "seed": seed + 1 + k,  # MINJA_SEED for this pair's benchmark draws
        })  # fmt: skip
    return {
        "protocol": P.PROTOCOL_ID, "seed": seed, "min_answerable": minimum,
        "valid_patients": len(valid), "patients_total": len(counts),
        "answerable_counts": {str(p): c for p, c in sorted(counts.items())},
        "pairs": pairs,
    }  # fmt: skip


def indexed_copy(db: Path, workdir: Path) -> Path:
    """A local copy with indexes on the id columns: speed only, identical query results."""
    import shutil

    workdir.mkdir(parents=True, exist_ok=True)
    copy = workdir / "mimic_iii_indexed.db"
    shutil.copyfile(db, copy)
    con = sqlite3.connect(copy)
    for (t,) in con.execute("select name from sqlite_master where type='table'").fetchall():
        cols = [r[1].lower() for r in con.execute(f"pragma table_info('{t}')")]
        for c in ("subject_id", "hadm_id", "icustay_id", "itemid"):
            if c in cols:
                con.execute(f"create index if not exists ix_{t}_{c} on {t}({c})")
    con.commit()
    con.close()
    return copy


def build(db: Path, templates_path: Path, out: Path, workdir: Path | None = None) -> dict:
    import tempfile

    templates = json.loads(Path(templates_path).read_text())
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        result = draw(answerable_counts(indexed_copy(db, Path(tmp)), templates))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n")
    return result


def extend(frozen: Path, out: Path) -> dict:
    """Rev 3: the same rule and seed on the frozen answerable counts, with N_RESULT_PAIRS
    result pairs. Refuses unless the frozen list is an exact prefix (no pair changes)."""
    old = json.loads(Path(frozen).read_text())
    counts = {int(k): v for k, v in old["answerable_counts"].items()}
    res = draw(counts, seed=old["seed"], minimum=old["min_answerable"])
    n = len(old["pairs"])
    if res["pairs"][:n] != old["pairs"]:
        raise RuntimeError("rev 3 draw is not a strict extension of the frozen pair list")
    res["extends"] = {"file": Path(frozen).name, "pairs": n}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    return res
