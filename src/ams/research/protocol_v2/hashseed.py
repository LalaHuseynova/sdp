"""Protocol v2: a fixed Python string-hash seed for every run (owner decision, 14 Nov 2026).

`PYTHONHASHSEED` must be set before the interpreter starts, so the scripts re-execute
themselves with it (`ensure`, first line of `__main__`) and every run command checks the
live interpreter (`require`) before loading data. Seed 0 disables hash randomization.
Why: RandEC (`amemguard_borrowed`, unchanged) samples erased subsequences from
`list(set(...))`, whose order otherwise differs between processes. No algorithm is
changed; the frozen methods' outputs are identical under any seed except RandEC's
cross-process sampling order (checked on dev data, step 1.12 runtime fixes).
"""

from __future__ import annotations

import os
import sys

from ams.research.dynamic.models import check

HASH_SEED = "0"


def ensure():
    """Re-execute this script with PYTHONHASHSEED=0 unless it already runs with it."""
    if os.environ.get("PYTHONHASHSEED") != HASH_SEED:
        os.execve(sys.executable, [sys.executable, *sys.argv],
                  {**os.environ, "PYTHONHASHSEED": HASH_SEED})  # fmt: skip


def require():
    check(os.environ.get("PYTHONHASHSEED") == HASH_SEED and sys.flags.hash_randomization == 0,
          f"Protocol v2 runs need PYTHONHASHSEED={HASH_SEED} (run the script directly: it "
          "re-executes itself with it)")  # fmt: skip
