"""One free precompute (G-D00, FREE_METHODS, 5 cells) under the current PYTHONHASHSEED."""
import json, os, sys, time
from pathlib import Path
from common_dev import load
from ams.research.protocol_v2 import pipeline as PL
from ams.research.recovery.offline import no_network
from ams.research.workload.stage2 import ConflictPlaceholderSession
import run_protocol_v2 as RP
out = Path(sys.argv[1]); assert not out.exists(); out.mkdir(parents=True)
with no_network():
    rows, store, conds = load(out)
    t0 = time.monotonic()
    PL.evaluate(rows, [store], ConflictPlaceholderSession(), out, conditions=conds, methods=RP.FREE_METHODS, defences={"randec": RP.randec()}, answer=False)
(out / "run.json").write_text(json.dumps({"PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"), "hash_randomization": sys.flags.hash_randomization, "seconds": time.monotonic() - t0}) + "\n")
