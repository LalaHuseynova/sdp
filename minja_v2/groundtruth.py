"""Ground truth for accuracy (protocol §1.6).

MINJA's data_create_poison.py / data_create.py substitute the patient id in the question
and its SQL but not in the stored answer, which therefore belongs to another patient. The
answer is recomputed here by running the question's (substituted) SQL on the demo
database. Correctness uses MINJA's own `judge` from its main.py, extracted verbatim.
"""

from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

from . import protocol as P


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def answer(con: sqlite3.Connection, sql: str) -> list[str] | None:
    """Distinct non-empty values in result order; None if the query fails or is empty."""
    try:
        rows = con.execute(sql).fetchall()
    except sqlite3.Error:
        return None
    out = []
    for r in rows:
        for v in r:
            if v is not None and str(v) != "" and _fmt(v) not in out:
                out.append(_fmt(v))
    return out or None


def recompute(db: Path, entries: list[dict]) -> list[dict]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return [{"index": i, "id": e["id"], "question": e["template"],
             "answer": answer(con, e["query"])} for i, e in enumerate(entries)]  # fmt: skip


def write(bench_dir: Path, db: Path = P.DEMO_TABLES / "mimic_iii.db") -> dict:
    out = {}
    for name in ("victim_test", "benign_test"):
        entries = json.loads((bench_dir / f"{name}.json").read_text())
        out[name] = recompute(db, entries)
    (bench_dir / "ground_truth.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def minja_judge():
    """MINJA's `judge(pred, ans)` from EHR/ehragent/main.py, compiled from its own source
    (main.py imports autogen at module level, so it is not imported as a whole)."""
    src = (P.EHR / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "judge")
    ns: dict = {}
    exec(compile(ast.Module([node], []), str(P.EHR / "main.py"), "exec"), ns)
    return ns["judge"]


def correct(judge, prediction: str, gt: list[str] | None) -> bool | None:
    """None when the ground truth is empty (excluded from accuracy)."""
    if gt is None:
        return None
    return bool(judge(prediction or "", ", ".join(gt)))
