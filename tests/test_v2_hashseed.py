"""Owner decision (14 Nov 2026): every protocol-v2 run uses PYTHONHASHSEED=0.

RandEC (unchanged) samples erased subsequences from `list(set(...))`, whose order
depends on Python's per-process string-hash seed; the fixed seed makes it reproducible
across processes. The seed is set by the scripts (re-exec) and checked before any run.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ams.research.dynamic.models import LedgerError
from ams.research.protocol_v2 import hashseed as HS

REPO = Path(__file__).resolve().parents[1]
SET_ORDER = "print(list({'w%d' % i for i in range(64)}))"


def _cli(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_chosen_seed_is_zero():
    assert HS.HASH_SEED == "0"


def test_ensure_reexecutes_the_script_with_the_fixed_seed(monkeypatch):
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    seen = {}

    def fake_execve(path, argv, env):
        seen.update(path=path, argv=argv, env=env)
        raise SystemExit(0)

    monkeypatch.setattr(os, "execve", fake_execve)
    with pytest.raises(SystemExit):
        HS.ensure()
    assert seen["path"] == sys.executable and seen["argv"][1:] == sys.argv
    assert seen["env"]["PYTHONHASHSEED"] == "0"


def test_ensure_does_nothing_when_the_seed_is_already_fixed(monkeypatch):
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setattr(os, "execve", lambda *a: pytest.fail("must not re-exec"))
    HS.ensure()


def test_require_refuses_another_seed(monkeypatch):
    monkeypatch.setenv("PYTHONHASHSEED", "1")
    with pytest.raises(LedgerError, match="PYTHONHASHSEED=0"):
        HS.require()


def test_fixed_seed_makes_set_order_reproducible_across_processes():
    def order(seed):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run([sys.executable, "-c", f"import sys; {SET_ORDER}; "
                              "print(sys.flags.hash_randomization)"], env=env,
                             capture_output=True, text=True, check=True).stdout  # fmt: skip
        return out

    assert order("0") == order("0") and order("0").split()[-1] == "0"
    assert len({order(s) for s in ("1", "2", "3", "4")}) > 1  # without it: process-dependent


@pytest.mark.parametrize("name", ["run_protocol_v2", "estimate_cost_v2"])
def test_scripts_fix_the_seed_before_running(name):
    src = (REPO / "scripts" / f"{name}.py").read_text()
    entry = src[src.index('if __name__ == "__main__":'):]
    assert entry.index("hashseed.ensure()") < entry.index("main()")


def test_runs_refuse_an_unfixed_interpreter_before_loading_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PYTHONHASHSEED", "1")
    missing = ["--bundle", str(tmp_path / "none"), "--stage1", str(tmp_path / "none"),
               "--out", str(tmp_path / "out")]  # fmt: skip
    with pytest.raises(LedgerError, match="PYTHONHASHSEED"):
        _cli("run_protocol_v2").main(["precompute", *missing, "--methods", "static"])
    with pytest.raises(LedgerError, match="PYTHONHASHSEED"):
        _cli("run_protocol_v2").main(["contexts", *missing, "--replies", str(tmp_path / "r")])
    with pytest.raises(LedgerError, match="PYTHONHASHSEED"):
        _cli("estimate_cost_v2").main(["measure", *missing[:4], "--group", "G-D00",
                                       "--out", str(tmp_path / "out")])  # fmt: skip
    assert not (tmp_path / "out").exists()
