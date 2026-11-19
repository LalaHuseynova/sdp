"""Per-pair execution (plan M2.3). Stages, in order:

  bench       free   MINJA's scripts build the pair's streams and tests; ground truth by SQL
  precompute  paid   use types (SAFE-Mem) and SensitiveAction verdicts (MemLineage / S2-ID)
  write       paid   each memory written ONCE per pair by the static base: MINJA's attack
                     stream and, rev 3, the mixed-history stream; each also on its clean
                     stream (the clean reference rows)
  audits      free   each condition's tickets (and provenance labels) from its written memory
  read        paid   every row (and condition) answers the 30 victim and the 30 benign test
                     questions on a fresh copy of the written memory; reference rows on both
                     memories, policy rows on each condition of their memory
  score       free   per-pair scores (minja_v2/score.py)

A run directory is finished only when its `.done` marker exists. An unfinished one is
renamed `<dir>.incomplete-<time>` (never deleted) and rerun; the response cache replays
every completed call at $0.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import bench as B
from . import groundtruth as GT
from . import protocol as P
from .adapter import history_split, labelling, select_tickets
from .score import run_dir_name, sha_file

MOCK_VERSION = "v5"  # v2: knowledge echoes only the asked patient's redirect; v3: raw-level
# mock below the frozen OpenRouter layer, two parallel tool calls per coding turn (rev 2);
# v4: every tool reply logged (drop-rate denominator); v5: = v4 on fresh caches (v4 run interrupted)
MAIN_PY = Path.home() / "venvs" / "sdp" / "bin" / "python"
MINJA_PY = Path.home() / "venvs" / "minja" / "bin" / "python"


def read_env_file(path: Path) -> dict:
    """KEY=VALUE lines of .env, parsed (never sourced, never printed)."""
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ensure_ehrsql_root() -> Path:
    link = P.EHRSQL_ROOT / "mimic_iii"
    if not link.exists():
        P.EHRSQL_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(Path("..") / "ehragent_tables", target_is_directory=True)
        except OSError:
            shutil.copytree(P.DEMO_TABLES, link)
    return P.EHRSQL_ROOT


class Runner:
    def __init__(self, root: Path, *, mock: bool = False, budget_usd: float = 0.0,
                 jobs: int = 4, counts: dict | None = None):  # fmt: skip
        root = Path(root).resolve()  # MINJA's scripts run from other directories
        self.root, self.mock, self.budget, self.jobs = root, mock, budget_usd, jobs
        self.counts = counts  # smaller counts: mock smoke tests only
        if counts and not mock:
            raise ValueError("non-protocol counts are allowed only in mock mode")
        self.ledger = root / ("cost_ledger_mock.jsonl" if mock else "cost_ledger.jsonl")
        # the mock agent's behaviour is versioned: a changed mock never reads old mock replies
        self.cache = P.REPO / ".llm_cache" / (f"minja_v2_mock_{MOCK_VERSION}.sqlite" if mock
                                              else "minja_v2.sqlite")  # fmt: skip
        root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ environment
    def base_env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MINJA_")}
        keys = read_env_file(P.REPO / ".env")
        if self.mock:
            # the OpenRouter code path (frozen legacy layer + single_call) with replies from
            # single_call.raw_mock; the fake key makes any stray real call fail, at no cost
            env.update(OPENAI_API_KEY="mock", OPENAI_BASE_URL="https://openrouter.ai/api/v1",
                       MINJA_V2_MOCK="1", MINJA_V2_MOCK_RAW="1")  # fmt: skip
        else:
            key = keys.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY missing from .env")
            env.update(OPENAI_API_KEY=key, OPENROUTER_API_KEY=key,
                       OPENAI_BASE_URL="https://openrouter.ai/api/v1")  # fmt: skip
        env.update(
            AMEMGUARD_MODEL=self.model, BACKBONE=P.BACKBONE, AMS_REPO=str(P.REPO),
            AMS_PY=str(MAIN_PY), PYTHONPATH=f"{P.REPO / 'src'}:{P.REPO}", PYTHONHASHSEED="0",
            EHRSQL_ROOT=str(ensure_ehrsql_root()), EHRSQL_DB="mimic_iii/mimic_iii.db",
            MINJA_V2_CACHE=str(self.cache), MINJA_V2_LEDGER=str(self.ledger),
            MINJA_V2_BUDGET_USD=str(self.budget),
        )  # fmt: skip
        return env

    @property
    def model(self) -> str:
        return "mock/gpt-4o-mini" if self.mock else P.AGENT_MODEL

    @property
    def agent_seed(self) -> int:
        return 1005 if self.mock else P.AGENT_SEED  # separate autogen cache per mock version

    # ------------------------------------------------------------------ helpers
    def pair_dir(self, pair: dict) -> Path:
        return self.root / "pairs" / pair["pair_id"]

    @staticmethod
    def _fresh(run: Path) -> bool:
        """True if the run must (re)start; an unfinished run is renamed aside."""
        if (run / ".done").exists():
            return False
        if run.exists():
            run.rename(run.with_name(f"{run.name}.incomplete-{time.strftime('%Y%m%dT%H%M%S')}"))
        run.mkdir(parents=True)
        return True

    def _main(self, run: Path, *, arm: str, data: Path, extra_env: dict, save: Path | None = None,
              load: Path | None = None, use_types: Path) -> bool:  # fmt: skip
        if not self._fresh(run):
            return True
        env = {**self.base_env(), **extra_env, "MINJA_AUDIT": arm,
               "MINJA_AUDIT_LOG": str(run / "audit.jsonl"), "MINJA_RESULTS": str(run / "results.jsonl"),
               "MINJA_GATE_LOG": str(run / "gate.jsonl"), "MINJA_V2_TRACE": str(run / "trace.jsonl"),
               "MINJA_USE_TYPES": str(use_types), "MINJA_V2_RUN": str(run.relative_to(self.root)),
               # protocol rev 2: one call per turn, per-question reset, failures recorded
               "MINJA_V2_REV2": "1", "MINJA_V2_DROPPED": str(run / "dropped_calls.jsonl"),
               "MINJA_V2_ERRORS": str(run / "errors.jsonl")}  # fmt: skip
        cmd = [str(MINJA_PY), "main.py", "--llm", self.model, "--dataset", "mimic_iii",
               "--data_path", str(data), "--logs_path", str(run / "logs"), "--num_questions", "-1",
               "--seed", str(self.agent_seed), "--num_shots", str(P.NUM_SHOTS)]  # fmt: skip
        if save:
            cmd += ["--save_memory_path", str(save)]
        if load:
            cmd += ["--load_memory_path", str(load)]
        (run / "command.json").write_text(json.dumps({"cmd": cmd[1:], "arm": arm, "env": {
            k: v for k, v in env.items() if k.startswith(("MINJA_", "EHRSQL_"))}}, indent=1))  # fmt: skip
        with (run / "run.log").open("w") as log:
            rc = subprocess.run(cmd, cwd=P.EHR, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        if rc == 0:
            (run / ".done").touch()
        return rc == 0

    # ------------------------------------------------------------------ stages
    def bench(self, pair: dict) -> dict:
        d = self.pair_dir(pair) / "bench"
        if (d / "ground_truth.json").exists():
            return json.loads((d / "bench.json").read_text())
        info = B.build(pair, d, self.counts)
        GT.write(d)
        return info

    def precompute(self, pair: dict) -> dict:
        from . import precompute as PC

        d = self.pair_dir(pair)
        if (d / "bench" / "use_types.json").exists() and (d / "bench" / "verdicts.json").exists():
            return {"cached": True}
        return PC.run(d / "bench", d / "precompute", mock=self.mock)

    def write(self, pair: dict, memories: list[str] | None = None) -> dict:
        d = self.pair_dir(pair)
        ut = d / "bench" / "use_types.json"
        env = {"MINJA_V2_PAIR": pair["pair_id"]}
        out = {}
        for name in memories or list(P.MEMORIES):
            m = P.MEMORIES[name]
            for key, stream in (("write", "stream"), ("clean_write", "clean_stream")):
                w = d / m[key]
                out[m[key]] = self._main(w, arm=P.BASE, data=d / "bench" / m[stream],
                                         save=w / "memory.json", extra_env=env, use_types=ut)  # fmt: skip
        return out

    def written(self, pair: dict, name: str) -> list[dict]:
        """A written memory, checked against its stream (rev 3: the mixed-history memory's
        first N attacker records must be the history questions, in order)."""
        d = self.pair_dir(pair)
        memory = json.loads((d / P.MEMORIES[name]["write"] / "memory.json").read_text())
        if name == "hist":
            history = [e["template"] for e in json.loads((d / "bench" / "history.json").read_text())]
            hist, _ = history_split(memory, len(history))
            if [memory[i]["question"] for i in hist] != history:
                raise RuntimeError("mixed-history memory: history phase does not match history.json")
        return memory

    def n_history(self, pair: dict) -> int:
        return len(json.loads((self.pair_dir(pair) / "bench" / "history.json").read_text()))

    def audits(self, pair: dict, conditions: list[str] | None = None) -> dict:
        d = self.pair_dir(pair)
        out, memories = {}, {}
        (d / "audits").mkdir(exist_ok=True)
        for c in conditions or list(P.CONDITIONS):
            f = d / "audits" / f"{c}.json"
            spec = P.CONDITIONS[c]
            if not f.exists():
                name = spec["memory"]
                if name not in memories:
                    memories[name] = self.written(pair, name)
                memory = memories[name]
                labels = labelling(memory, spec.get("labels"), self.n_history(pair))
                t = select_tickets(memory, c, pair["pair_id"], int(pair["victim"]),
                                   int(pair["target"]), labels=labels, memory_name=name)  # fmt: skip
                f.write_text(json.dumps(t, indent=1) + "\n")
            out[c] = json.loads(f.read_text())["shortfall"]
        return out

    def read_jobs(self, pair: dict, rows: list[str] | None = None,
                  conditions: list[str] | None = None,
                  memories: list[str] | None = None) -> list[dict]:  # fmt: skip
        d = self.pair_dir(pair)
        jobs = []
        for name in memories or list(P.MEMORIES):
            m = P.MEMORIES[name]
            for row, arm, which in P.REFERENCE_ROWS:
                if rows and row not in rows:
                    continue
                key = "clean_write" if which == "clean" else "write"
                jobs.append({"row": row, "condition": None, "arm": arm, "memory_name": name,
                             "memory": d / m[key] / "memory.json"})  # fmt: skip
            for row, arm in P.POLICY_ROWS:
                if rows and row not in rows:
                    continue
                for c in P.conditions_of(name):
                    if conditions and c not in conditions:
                        continue
                    jobs.append({"row": row, "condition": c, "arm": arm, "memory_name": name,
                                 "memory": d / m["write"] / "memory.json"})  # fmt: skip
        return jobs

    def _read_one(self, pair: dict, job: dict) -> dict:
        d = self.pair_dir(pair)
        name = job.get("memory_name", "attack")
        run = d / P.MEMORIES[name]["read"] / run_dir_name(job["row"], job["condition"])
        run.mkdir(parents=True, exist_ok=True)
        env = {"MINJA_V2_PAIR": pair["pair_id"]}
        cfg = {"row": job["row"], "condition": job["condition"], "arm": job["arm"],
               "memory_name": name, "memory": str(job["memory"].relative_to(self.root)),
               "memory_sha256": sha_file(job["memory"])}  # fmt: skip
        if job["condition"]:
            tickets = d / "audits" / f"{job['condition']}.json"
            env.update(MINJA_V2_CONDITION=job["condition"], MINJA_V2_TICKETS=str(tickets),
                       MINJA_V2_VERDICTS=str(d / "bench" / "verdicts.json"))  # fmt: skip
            cfg["tickets_sha256"] = sha_file(tickets)
        (run / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
        res = {}
        for part, data in (("victim", "victim_test.json"), ("benign", "benign_test.json")):
            res[part] = self._main(run / part, arm=job["arm"], data=d / "bench" / data,
                                   load=job["memory"], extra_env=env,
                                   use_types=d / "bench" / "use_types.json")  # fmt: skip
        return {**{k: str(v) for k, v in job.items()}, **res}

    def read(self, pair: dict, rows=None, conditions=None, memories=None) -> list[dict]:
        jobs = self.read_jobs(pair, rows, conditions, memories)
        with cf.ThreadPoolExecutor(max_workers=self.jobs) as ex:
            return list(ex.map(lambda j: self._read_one(pair, j), jobs))

    def score(self, pair: dict) -> dict:
        from .score import score_pair

        s = score_pair(self.pair_dir(pair), pair)
        (self.pair_dir(pair) / "score.json").write_text(json.dumps(s, indent=1) + "\n")
        return s

    def spent(self) -> float:
        if not self.ledger.exists():
            return 0.0
        return sum(json.loads(x).get("usd", 0.0) for x in self.ledger.read_text().splitlines() if x)


def main_python_ok() -> bool:
    return Path(sys.executable).resolve() == MAIN_PY.resolve()
