"""Apply the v2 ASR-eligibility rule to every frozen scenario (free; no outcome read).

Writes, per attack, how many targets the rule keeps and why the others are dropped, and
checks that every (conversation x orientation x shape x draw) scenario keeps >= 1 target.
Usage (WSL): python -m locomo_v2.target_filter OUT.json
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from locomo_v1 import build as B
from locomo_v1 import config as K
from locomo_v2.metrics import asr_eligible

from ams.data.locomo import load_locomo
from ams.eval.locomo import normalize_answer

F = B.F


def main(out: str):
    convs = load_locomo(K.DATA)
    p1, p2 = B.pools(convs)
    gold = {q.qid: q.answer for c in convs for q in c.qa}
    reasons = defaultdict(Counter)
    per_scenario = defaultdict(list)
    for c in convs:
        text = normalize_answer(" ".join(t.render() for s in c.sessions for t in s.turns))
        for pidx in K.ORIENTATIONS:
            for shape in K.SHAPES:
                for draw in range(K.DRAWS_MAX):
                    for attack in K.ATTACKS:
                        rng = random.Random(f"{F.SEED}|{c.sample_id}|{pidx}|{shape}|{draw}")
                        mem = F.build_memory(c, pidx, shape, rng, p1 if attack == "P1" else p2[c.sample_id])
                        kept = 0
                        for r in mem["records"]:
                            if r["target"]:
                                ok, why = asr_eligible(B.WRONG.search(r["text"]).group(1), gold[r["target"]], text)
                                reasons[attack][why] += 1
                                kept += ok
                        per_scenario[attack].append(kept)
    res = {a: {"reasons": dict(reasons[a]),
               "kept_share": round(reasons[a]["ok"] / sum(reasons[a].values()), 4),
               "scenarios_with_zero_eligible": sum(k == 0 for k in per_scenario[a]),
               "mean_eligible_per_scenario": round(sum(per_scenario[a]) / len(per_scenario[a]), 3)}
           for a in reasons}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
