import gzip, json, os, sqlite3, sys
from pathlib import Path
REPO = Path("/Users/ulkerhuseynova/Desktop/SAFE-Mem")
os.chdir(REPO); sys.path.insert(0, str(REPO / "scripts"))
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
from ams.research.protocol_v2 import ablations as AB, registry as REG
from ams.research.workload import adaptive as AD, design as D
from ams.research.workload.generator import read_rows
# condition names (not registry cells); the late-audit condition exercises pre-reveal states
CONDS = ("localized", "distributed", "sybil_k2_rand_d0", "random_spread_d0", "imp_localized_late_d0")
def conditions():
    return CONDS
def load(out, group="G-D00"):
    rows = read_rows(REPO / "research_data/controlled_workload_v3_20261108")
    with gzip.open(REPO / f"research_data/controlled_workload_stage1_dev_v3_20261108/stores/{group}.json.gz", "rt") as f:
        store = json.load(f)
    store = AB.checkpoint_prompts(store, out / "prompt_mirror")
    conds = conditions()
    return rows, AD.extend_store(rows, store, [c for c in conds if c not in D.CONDITIONS]), conds
def journal(p):
    with sqlite3.connect(p / "queries.sqlite") as db:
        return [(k, json.loads(b)) for k, b in db.execute("SELECT key, body FROM outcomes ORDER BY rowid")]
