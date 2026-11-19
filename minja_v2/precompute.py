"""Before a pair's runs (main environment): SAFE-Mem's use types for every question, and
MemLineage's SensitiveAction verdicts for every test question (S2-ID's gate).

Both use the existing objects, prompts and cached, ledgered client of the existing MINJA
arms (scripts/minja_use_types.py; ams.eval.defences.build_defence "memlineage_coarse"), so
the MemLineage row and S2-ID read identical verdicts from the shared response cache.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import bench
from . import protocol as P

REPO = P.REPO


def run(bench_dir: Path, results_root: Path, mock: bool = False) -> dict:
    questions = bench.questions(bench_dir)
    tests = sorted({e["template"] for name in ("victim_test.json", "benign_test.json")
                    for e in json.loads((bench_dir / name).read_text())})  # fmt: skip
    if mock:
        use = {q: "description" for q in questions}
        verdicts = {q: "ORDINARY" for q in tests}
    else:
        from ams.baselines.memlineage import SensitiveAction
        from ams.core.env import load_env
        from ams.eval.backbone import apply_backbone
        from ams.eval.context import Config, RunContext
        from ams.eval.use_type import UseTypeClassifier
        from ams.llm import map_concurrent, model_of

        load_env()
        cfg = Config.load(REPO / "configs" / "minja_typed.yaml")
        apply_backbone(cfg, P.BACKBONE)
        ctx = RunContext(cfg, results_root=results_root, run_id="use_types")
        clf = UseTypeClassifier(client=ctx.client(cfg.require("models.memory"), stage="use_type"),
                                model=model_of(cfg.require("models.memory")), prompts=ctx.prompts,
                                version=cfg.get("prompts.classify_use_type", "v1"))  # fmt: skip
        rungs = map_concurrent(lambda q: clf.required(q).name.lower(), questions,
                               workers=cfg.get("runtime.workers", 8))  # fmt: skip
        use = dict(zip(questions, rungs, strict=True))
        ctx.finalise({"minja_v2": "use_types"})

        cfg2 = Config.load(REPO / "configs" / "minja_baselines.yaml")
        apply_backbone(cfg2, P.BACKBONE)
        ctx2 = RunContext(cfg2, results_root=results_root, run_id="sensitive_action")
        spec = cfg2.require("models.agent")
        sens = SensitiveAction(ctx2.client(spec, stage="sensitive_action"), model_of(spec),
                               prompts=ctx2.prompts)  # fmt: skip
        flags = map_concurrent(sens, tests, workers=cfg2.get("runtime.workers", 8))
        verdicts = {q: ("SENSITIVE" if f else "ORDINARY") for q, f in zip(tests, flags, strict=True)}
        ctx2.finalise({"minja_v2": "sensitive_action"})
    (bench_dir / "use_types.json").write_text(json.dumps(use, indent=1) + "\n")
    (bench_dir / "verdicts.json").write_text(json.dumps(verdicts, indent=1) + "\n")
    return {"use_types": len(use), "verdicts": len(verdicts),
            "sensitive": sum(v == "SENSITIVE" for v in verdicts.values())}  # fmt: skip
