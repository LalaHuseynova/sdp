"""Fix 1 verification on real dev data (free, no network): uncached vs cached RandEC in ONE
process (RandEC's sampling depends on the process hash seed), every row compared."""
import gzip, json, sqlite3, sys, time
from pathlib import Path
sys.path.insert(0, "scripts")
from ams.research.protocol_v2 import ablations as AB, pipeline as PL, registry as REG
from ams.research.workload import adaptive as AD, design as D
from ams.research.workload.generator import read_rows
from ams.research.workload.stage2 import ConflictPlaceholderSession
from ams.research.recovery.offline import no_network
from ams.baselines.amemguard_borrowed import RandECClassifier
from ams.research.protocol_v2.randec_cache import cached_randec
import os
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
out = Path(sys.argv[1]); assert not out.exists(); out.mkdir(parents=True)
W = Path("third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt")
rows = read_rows(Path("research_data/controlled_workload_v3_20261108"))
cells = ["localized", "distributed", "sybil_k2_rand_d0", "random_spread_d0"]
conds = tuple(cells)  # condition names (as in the step 1.12 measurement)
methods = ("static", "randec", "R", "randec+R", "S")
def journal(p):
    with sqlite3.connect(p / "queries.sqlite") as db:
        return [(k, b) for k, b in db.execute("SELECT key, body FROM outcomes ORDER BY rowid")]
with no_network():
    with gzip.open("research_data/controlled_workload_stage1_dev_v3_20261108/stores/G-D00.json.gz", "rt") as f:
        store = json.load(f)
    store = AB.checkpoint_prompts(store, out / "prompt_mirror")
    store = AD.extend_store(rows, store, [c for c in conds if c not in D.CONDITIONS])
    res = {}
    for name, model in (("uncached", RandECClassifier(weights=W)),
                        ("cached", cached_randec(RandECClassifier(weights=W)))):
        t0 = time.monotonic()
        PL.evaluate(rows, [store], ConflictPlaceholderSession(), out / name, conditions=conds,
                    methods=methods, defences={"randec": model}, answer=False)
        res[name] = time.monotonic() - t0
        if name == "cached": res["distinct_texts"] = len(model.randec_cache)
a, b = journal(out / "uncached"), journal(out / "cached")
res.update(conditions=len(conds), rows=len(a), identical=(a == b),
           differing=sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b)))
(out / "verification.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
