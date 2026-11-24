"""Protocol v2, plan.md step 1.12: dry-run cost and runtime estimate. FREE, no network.

Every figure is MEASURED or a stated BOUND:
  per-call cost  measured: actual paid USD and tokens of the completed calls in the
                 guarded dev ledger (GPT-4o-mini, by stage); published defences' own calls
                 from their dev run summaries; Claude list prices from the pricing files.
  call counts    measured: the free precompute on dev groups. Identical requests are sent
                 once, so a stage pays per DISTINCT answer prompt / judged prompt /
                 conflict request. Scaled per group to the 96 held-out groups.
  unmeasured     methods whose contexts need a paid call (A-MemGuard, MemLineage, LLM
                 sanitiser, S2-ID) or that were measured on a few cells only (RandEC, "+R"
                 variants): LOW = no prompt beyond the measured ones; HIGH = the
                 deterministic upper bound (a filter of a retrieval has at most as many
                 distinct outputs as that retrieval has distinct contexts).
  runtime        measured precompute seconds; seconds per paid call from the OpenRouter
                 generation timestamps in the ledger.
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics as st
from collections import defaultdict
from pathlib import Path

VERSION = "protocol-v2-cost-estimate-v1"
REPO = Path(__file__).resolve().parents[4]
GROUPS = 96
REPLICATION_GROUPS = 24  # v4 locked-test split (protocol §2.5)
DEV_GROUPS = 8
PROBES = 35  # questions per group (dev, v4 test and v5 alike)
JUDGED = ("attack", "copy_linked", "copy_unlinked")
CONTINGENCY = 0.30  # proposed cap = high estimate x 1.3, rounded up
ANSWER_MAX_TOKENS = 200  # runner.py: the answer request
LEDGER = REPO / "research_data/controlled_workload_session_v2_20261108/dispatch.sqlite"
PUBLISHED_DEV = REPO / "research_data/published_paid_dev_v3_20261112"
STAGE1_DEV = REPO / "research_data/controlled_workload_stage1_dev_v3_20261108"
DEV_PUBLISHED_PROBES = 280  # dev published runs: 8 groups x 35 probes, one context each
ALLOWANCE_LEFT = 26.57  # plan.md budget table, 14 Nov 2026
CEILINGS = {"v2_generation": 10, "v2_backbone_answer": 10, "v2_backbone_gemini": 10,
            "v2_stage3": 80,
            "v2_inclusion": 5, "v2_stage1": 5, "v2_published_memlineage": 0.5,
            "v2_published_amemguard": 20, "v2_published_sanitiser": 10}  # fmt: skip
# Option B for the gate/tau ablations (pending decision, README step 1.10 finding 2)
OPTION_B_FAMILIES = ("sybil_k", "sybil_own_batch", "laundering_r")


# ----------------------------------------------------------------------------- per call


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def ledger_costs(path=LEDGER) -> dict:
    """stage -> n, mean USD, mean input/output tokens, median seconds between calls."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    acc = defaultdict(list)
    try:
        q = "SELECT stage, result FROM dispatches WHERE status='completed'"
        for stage, res in db.execute(q):
            r = json.loads(res)
            md = (((r.get("dispatch") or {}).get("receipt") or {}).get("metadata")) or {}
            gen = str(md.get("generation_id") or "")
            ts = int(gen.split("-")[1]) if gen.startswith("gen-") else None
            acc[stage].append((float(r["actual_paid_usd"]), md.get("input_tokens"),
                               md.get("output_tokens"), ts))  # fmt: skip
    finally:
        db.close()
    return {stage: {"n": len(v), "usd": st.mean(x[0] for x in v),
                    "in_tokens": _mean(x[1] for x in v if x[1] is not None),
                    "out_tokens": _mean(x[2] for x in v if x[2] is not None),
                    "seconds_per_call": seconds_per_call(x[3] for x in v)}
            for stage, v in acc.items()}  # fmt: skip


def seconds_per_call(stamps) -> float | None:
    """Median gap between consecutive generation timestamps (gaps over 60 s are pauses)."""
    ts = sorted(t for t in stamps if t is not None)
    gaps = [b - a for a, b in zip(ts, ts[1:], strict=False) if b - a <= 60]
    return st.median(gaps) if gaps else None


def call_seconds(path=LEDGER) -> dict:
    """Seconds between consecutive completed paid calls over every stage of the dev
    ledger (gaps over 60 s are pauses): the median is about the API latency; the mean also
    includes the local work done between calls in those runs, so it is an upper value."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        q = "SELECT result FROM dispatches WHERE status='completed'"
        ts = sorted(int(str(json.loads(r)["dispatch"]["receipt"]["metadata"]["generation_id"])
                        .split("-")[1]) for (r,) in db.execute(q))  # fmt: skip
    finally:
        db.close()
    gaps = [b - a for a, b in zip(ts, ts[1:], strict=False) if b - a <= 60]
    return {"median": float(st.median(gaps)), "mean": float(st.mean(gaps))}


def price(path) -> dict:
    p = json.loads(Path(path).read_text())
    return {"model": p["model"], "in": float(p["input_usd_per_million"]) / 1e6,
            "out": float(p["output_usd_per_million"]) / 1e6}  # fmt: skip


def published_costs(calls, root=PUBLISHED_DEV) -> dict:
    """USD per context (A-MemGuard, sanitiser) and per question (MemLineage), dev runs."""
    s = {m: json.loads((Path(root) / f"{m}_summary.json").read_text())
         for m in ("amemguard", "sanitiser", "memlineage")}  # fmt: skip
    # The sanitiser ran in the v2 session (ledger) plus a resume session (its summary).
    san = calls["published_sanitiser"]["usd"] * calls["published_sanitiser"]["n"]
    san += float(s["sanitiser"]["task_spend_usd"])
    ml = s["memlineage"]
    san_calls = calls["published_sanitiser"]["n"] + s["sanitiser"]["calls_this_run"]
    return {"a_memguard_per_context": float(s["amemguard"]["task_spend_usd"])
            / DEV_PUBLISHED_PROBES,
            "a_memguard_calls_per_context": s["amemguard"]["calls_this_run"]
            / DEV_PUBLISHED_PROBES,
            "llm_sanitiser_calls_per_context": san_calls / DEV_PUBLISHED_PROBES,
            "llm_sanitiser_per_context": san / DEV_PUBLISHED_PROBES,
            "memlineage_per_question": float(ml["task_spend_usd"]) / ml["calls_this_run"],
            "memlineage_questions_per_group": ml["calls_this_run"] / DEV_GROUPS}  # fmt: skip


def stage1_per_group(root=STAGE1_DEV) -> dict:
    """Stage-1 chat requests per dev group by stage, cached ones included (held-out
    groups have no cache)."""
    s = json.loads((Path(root) / "stage1_summary.json").read_text())
    n = defaultdict(int)
    for g in s["per_group_requests"].values():
        for key, k in g["chat"].items():
            n["workload_" + key.split(":")[0]] += k
    return {k: v / len(s["per_group_requests"]) for k, v in n.items()}


# ----------------------------------------------------------------------------- counts


def journal(path: Path) -> list[dict]:
    db = sqlite3.connect(f"file:{Path(path) / 'queries.sqlite'}?mode=ro", uri=True)
    try:
        return [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes")]
    finally:
        db.close()


def distinct(rows) -> tuple[int, int]:
    """(distinct answer prompts, distinct judged prompts)."""
    rows = list(rows)
    return (len({r["prompt_hash"] for r in rows}),
            len({r["prompt_hash"] for r in rows if r["kind"] in JUDGED}))  # fmt: skip


def invariance(rows) -> dict:
    """Published defences filter Original SAFE-Mem's retrieval: they are paid once per
    probe only if that retrieval is identical in every condition."""
    by = defaultdict(set)
    for r in rows:
        by[r["probe_id"]].add(r["prompt_hash"])
    return {"probes": len(by), "varying": sum(len(v) > 1 for v in by.values()),
            "distinct": sum(len(v) for v in by.values())}  # fmt: skip


def group_counts(mdir: Path, scopes: dict) -> dict:
    """One measured group: distinct prompts over the free internal methods and per
    method, for each scope (scope name -> set of conditions)."""
    meas = json.loads((Path(mdir) / "measure.json").read_text())
    rows = {m: journal(Path(mdir) / m) for m in meas["methods"]}
    internal = [r for m, rs in rows.items() if not m.startswith("randec") for r in rs]
    out = {"seconds": {m: x["seconds"] for m, x in meas["methods"].items()},
           "conditions": {m: x["conditions"] for m, x in meas["methods"].items()},
           "conflicts": len({h for m, x in meas["methods"].items()
                             if not m.startswith("randec") for h in x["conflict_distinct"]}),
           "static_invariant": invariance(rows["static"]), "scopes": {}}  # fmt: skip
    for scope, conds in scopes.items():
        a, j = distinct(r for r in internal if r["condition"] in conds)
        per = {m: distinct(r for r in rs if r["condition"] in conds) for m, rs in rows.items()}
        out["scopes"][scope] = {"answers": a, "judged": j, "per_method": per}
    return out


# ----------------------------------------------------------------------------- stages


def answer_usd(n_answers, n_judged, n_conflicts, c) -> float:
    return (n_answers * c["workload_answer"]["usd"] + n_judged * c["workload_judge"]["usd"]
            + n_conflicts * c["workload_conflict"]["usd"])  # fmt: skip


def per_group(G: list[dict], scope: str) -> dict:
    """Per-group distinct prompts in a scope: measured (low) and upper bound (high)."""
    sc = [g["scopes"][scope] for g in G]
    A = _mean(s["answers"] for s in sc)
    J = _mean(s["judged"] for s in sc)
    d = {m: _mean(s["per_method"][m][0] for s in sc) for m in ("static", "R", "SL")}
    share = J / A if A else 0.0
    # high: 4 published filters (each <= distinct static contexts), their 4 "+R"
    # variants (each <= distinct R contexts) and S2-ID (<= distinct SL contexts)
    extra = 4 * d["static"] + 4 * d["R"] + d["SL"]
    return {"answers_low": A, "judged_low": J, "answers_high": A + extra,
            "judged_high": J + extra * share, "judged_share": share,
            "distinct_static": d["static"], "distinct_R": d["R"], "distinct_SL": d["SL"],
            "unmeasured_high": extra}  # fmt: skip


def evaluation(G, scope, groups, c, pub, conflicts) -> dict:
    """Answers/judges/conflicts (GPT-4o-mini) + the published defences' own calls."""
    p = per_group(G, scope)
    low = groups * answer_usd(p["answers_low"], p["judged_low"], conflicts, c)
    # S2-ID's conflict requests are bounded by SL's (<= all measured): at most double
    high = groups * answer_usd(p["answers_high"], p["judged_high"], 2 * conflicts, c)
    lo, hi = p["distinct_static"], p["distinct_static"] + p["distinct_R"]
    q = groups * pub["memlineage_questions_per_group"] * pub["memlineage_per_question"]
    e = {"per_group": p, "answers": {"low": low, "high": high},
         "a_memguard": {"low": groups * lo * pub["a_memguard_per_context"],
                        "high": groups * hi * pub["a_memguard_per_context"]},
         "llm_sanitiser": {"low": groups * lo * pub["llm_sanitiser_per_context"],
                           "high": groups * hi * pub["llm_sanitiser_per_context"]},
         "memlineage": {"low": q, "high": q}}  # fmt: skip
    e["total"] = {k: sum(e[x][k] for x in ("answers", "a_memguard", "llm_sanitiser",
                                           "memlineage")) for k in ("low", "high")}  # fmt: skip
    return e


def haiku_answers(p, groups, c, haiku) -> dict:
    """Second backbone: every answer prompt re-answered by Claude Haiku. Low: GPT's
    measured tokens; high: 1.3x input tokens (tokenizer difference), max_tokens out."""
    tin, tout = c["workload_answer"]["in_tokens"], c["workload_answer"]["out_tokens"]
    return {"low": groups * p["answers_low"] * (tin * haiku["in"] + tout * haiku["out"]),
            "high": groups * p["answers_high"]
            * (1.3 * tin * haiku["in"] + ANSWER_MAX_TOKENS * haiku["out"])}  # fmt: skip


def generation(sonnet) -> dict:
    """Step 3.1: input tokens from the rendered frozen requests (UTF-8 bytes / 4).
    Output: the prompts' document word ranges (attack 180-450, benign 120-380) x 1.4
    tokens per word + 200 tokens of JSON fields; low = midpoint, high = upper limit.
    The hard bound (max_tokens on every call) is reported; the approved cap stops the
    stage before it could be reached."""
    from ams.research.protocol_v2 import generation as GEN

    attacks = GEN.attack_specs(GEN.reachable_distribution(GEN.load_reachable_cases(REPO)))
    benign = GEN.benign_specs()

    def size(req):
        return sum(len(m.content.encode()) for m in req.messages) / 4

    a_in = _mean(size(GEN.attack_request(s)) for s in attacks)
    b_in = _mean(size(GEN.benign_request(s)) for s in benign)
    return generation_usd(len(attacks), len(benign), a_in, b_in, sonnet,
                          GEN.ATTACK_TOKENS, GEN.BENIGN_TOKENS)  # fmt: skip


WORDS = {"attack": (180, 450), "benign": (120, 380)}  # v2_generator_*_system prompts
TOKENS_PER_WORD, JSON_TOKENS = 1.4, 200


def generation_usd(n_a, n_b, a_in, b_in, sonnet, a_max, b_max) -> dict:
    def out(words):
        return words * TOKENS_PER_WORD + JSON_TOKENS

    tin = n_a * a_in + n_b * b_in
    mid = n_a * out(sum(WORDS["attack"]) / 2) + n_b * out(sum(WORDS["benign"]) / 2)
    top = n_a * out(WORDS["attack"][1]) + n_b * out(WORDS["benign"][1])
    hard = n_a * a_max + n_b * b_max
    return {"attacks": n_a, "benign": n_b, "attack_in_tokens": a_in,
            "benign_in_tokens": b_in, "in_tokens": tin, "out_tokens_mid": mid,
            "out_tokens_top": top, "out_tokens_hard": hard,
            "low": tin * sonnet["in"] + mid * sonnet["out"],
            "high": tin * sonnet["in"] + top * sonnet["out"],
            "hard_bound": tin * sonnet["in"] + hard * sonnet["out"]}  # fmt: skip


def ablations(root, G, c) -> dict:
    """Step 6.2. Option A (current cells): measured distinct prompts over all free dev
    ablation jobs; low = dev only, high = dev + replication split (protocol §8), scaled by
    groups. Option B also runs the 4 source-gate/tau variants on the Sybil and
    laundering cells (bound: 4 x S's distinct prompts in those cells, measured)."""
    rows = [r for j in sorted(Path(root).iterdir()) if (j / "queries.sqlite").exists()
            for r in journal(j)]  # fmt: skip
    a, j = distinct(rows)
    dev = answer_usd(a, j, 0, c)
    share = per_group(G, "option_b")["judged_share"]
    extra = 4 * _mean(g["scopes"]["option_b"]["per_method"]["S"][0] for g in G)
    extra_usd = answer_usd(extra, extra * share, 0, c)
    scale = (DEV_GROUPS + REPLICATION_GROUPS) / DEV_GROUPS
    return {"dev_answers": a, "dev_judged": j, "dev_usd": dev,
            "option_a": {"low": dev, "high": dev * scale},
            "option_b": {"low": dev + DEV_GROUPS * extra_usd,
                         "high": (dev + DEV_GROUPS * extra_usd) * scale},
            "option_b_extra_prompts_per_group": extra}  # fmt: skip


# ----------------------------------------------------------------------------- total


def cap(x: float) -> float:
    """Round a proposed cap up to a readable figure."""
    step = 0.05 if x < 1 else 0.5 if x < 10 else 1.0
    return round(math.ceil(round(x / step, 9)) * step, 2)


def merge(*parts) -> dict:
    """Sum {purpose: {low, high}} dicts."""
    out = defaultdict(lambda: {"low": 0.0, "high": 0.0})
    for part in parts:
        for purpose, v in part.items():
            for k in ("low", "high"):
                out[purpose][k] += v[k]
    return dict(out)


def by_purpose(stages: dict) -> dict:
    return caps(merge(*({s["purpose"]: s} for s in stages.values())))


def caps(purposes: dict) -> dict:
    out = {p: {"low": v["low"], "high": v["high"]} for p, v in purposes.items()}
    for p, v in out.items():
        v["proposed_cap"] = cap(v["high"] * (1 + CONTINGENCY))
        v["code_ceiling"] = CEILINGS[p]
        v["fits_ceiling"] = v["proposed_cap"] <= v["code_ceiling"]
    return dict(out)


def estimate(measured_dirs, ablations_dir, *, groups=GROUPS) -> dict:
    from ams.research.protocol_v2 import registry as REG

    c = ledger_costs()
    pub = published_costs(c)
    haiku = price(REPO / "configs/research/pricing_claude_haiku_5_5_20261114.json")
    sonnet = price(REPO / "configs/research/pricing_claude_sonnet_5_5_20261114.json")
    table = REG.cells()
    scopes = {"all": {x for v in table.values() for x in v["conditions"]},
              "core": {x for cell in REG.SECOND_BACKBONE for x in table[cell]["conditions"]},
              "option_b": {x for v in table.values() if v["family"] in OPTION_B_FAMILIES
                           for x in v["conditions"]}}  # fmt: skip
    G = [group_counts(d, scopes) for d in measured_dirs]
    conflicts = _mean(g["conflicts"] for g in G)
    main = evaluation(G, "all", groups, c, pub, conflicts)
    core = per_group(G, "core")
    s1 = stage1_per_group()
    s1_usd = sum(n * c[k]["usd"] for k, n in s1.items())
    gen = generation(sonnet)
    # I1 runs the frozen write path on each generated attack, as Stage 1 does per
    # document (cost per extracted document); E2 adds one classifier call per attack.
    i1 = gen["attacks"] * (s1_usd / s1["workload_extraction"]
                           + c["workload_classifier"]["usd"])  # fmt: skip
    abl = ablations(ablations_dir, G, c)
    judge = c["workload_judge"]["usd"]
    # replication: Table 1 + hypothesis cells (low/high) or every cell (variant)
    rep = evaluation(G, "core", REPLICATION_GROUPS, c, pub, conflicts)
    rep_core = rep["total"]
    rep_all = evaluation(G, "all", REPLICATION_GROUPS, c, pub, conflicts)["total"]
    raw = {
        "3.1 generation (Claude Sonnet)": ("v2_generation", gen),
        "3.3 inclusion E2 + I1": ("v2_inclusion", {"low": i1, "high": 2 * i1}),
        "3.5 Stage 1 memory, 96 groups": ("v2_stage1", {"low": groups * s1_usd,
                                                         "high": 2 * groups * s1_usd}),
        "4.2+4.3 answers, judges, conflicts": ("v2_stage3", main["answers"]),
        "4.3 A-MemGuard own calls": ("v2_published_amemguard", main["a_memguard"]),
        "4.3 LLM sanitiser own calls": ("v2_published_sanitiser", main["llm_sanitiser"]),
        "4.3 MemLineage SensitiveAction": ("v2_published_memlineage", main["memlineage"]),
        "4.4 replication (24 groups, Table 1 + hypothesis cells): answers, judges": (
            "v2_stage3", rep["answers"]),
        "4.4 replication: A-MemGuard own calls": ("v2_published_amemguard", rep["a_memguard"]),
        "4.4 replication: LLM sanitiser own calls": ("v2_published_sanitiser",
                                                     rep["llm_sanitiser"]),
        "4.4 replication: MemLineage SensitiveAction": ("v2_published_memlineage",
                                                        rep["memlineage"]),
        "4.5 Haiku answers": ("v2_backbone_answer", haiku_answers(core, groups, c, haiku)),
        "4.5 GPT judges of Haiku answers": ("v2_stage3", {
            "low": groups * core["judged_low"] * judge,
            "high": groups * core["judged_high"] * judge}),
        "6.2 ablations, option A (current cells)": ("v2_stage3", abl["option_a"]),
    }  # fmt: skip
    stages = {k: {"purpose": p, "low": v["low"], "high": v["high"]}
              for k, (p, v) in raw.items()}  # fmt: skip
    total = {k: sum(s[k] for s in stages.values()) for k in ("low", "high")}
    variants = {
        "4.4 replication on every cell instead": {k: rep_all[k] - rep_core[k]
                                                  for k in total},
        "6.2 ablations option B instead of A": {k: abl["option_b"][k] - abl["option_a"][k]
                                                for k in total},
        # changes owner decision 22 (generator = Claude Sonnet); shown for scope only
        "3.1 with Claude Haiku as generator instead": {
            k: generation_usd(gen["attacks"], gen["benign"], gen["attack_in_tokens"],
                              gen["benign_in_tokens"], haiku, 0, 0)[k] - gen[k]
            for k in total},
    }  # fmt: skip
    b = {
        k: evaluation(G, "all", 32, c, pub, conflicts)["total"][k]
        + evaluation(G, "core", groups - 32, c, pub, conflicts)["total"][k]
        for k in total
    }

    def evals(n, scope):  # one evaluation stage, by paid purpose
        e = evaluation(G, scope, n, c, pub, conflicts)
        return {"v2_stage3": e["answers"], "v2_published_amemguard": e["a_memguard"],
                "v2_published_sanitiser": e["llm_sanitiser"],
                "v2_published_memlineage": e["memlineage"]}  # fmt: skip

    def fresh(n):  # n generated groups: specs, inclusion and Stage 1 scale with groups
        f = n / groups
        return merge({"v2_generation": {k: f * gen[k] for k in total},
                      "v2_inclusion": {"low": f * i1, "high": 2 * f * i1},
                      "v2_stage1": {"low": n * s1_usd, "high": 2 * n * s1_usd}},
                     evals(n, "all"))  # fmt: skip

    def haiku_on(n):
        return {
            "v2_backbone_answer": haiku_answers(core, n, c, haiku),
            "v2_stage3": {k: n * core[f"judged_{k}"] * judge for k in total},
        }

    mp, abl_a = REPLICATION_GROUPS, {"v2_stage3": abl["option_a"]}
    scenario_purposes = {
        "A. full plan: 96 generated groups + MPBench v4 replication": merge(
            fresh(groups), haiku_on(groups), evals(mp, "core"), abl_a),
        "B. MPBench only: v4 split (24 groups) is the main result": merge(
            evals(mp, "all"), haiku_on(mp), abl_a),
        "C. MPBench v4 main + 32 generated groups (every cell)": merge(
            evals(mp, "all"), haiku_on(mp), abl_a, fresh(32)),
    }  # fmt: skip
    scenarios = {k: add(*v.values()) for k, v in scenario_purposes.items()}
    scenario_caps = {k: caps(v) for k, v in scenario_purposes.items()}
    return {"version": VERSION, "groups": groups, "measured_groups": len(G),
            "per_call": c, "published": pub, "prices": {"haiku": haiku, "sonnet": sonnet},
            "generation": gen, "stage1_calls_per_group": s1, "stage1_usd_per_group": s1_usd,
            "conflicts_per_group": conflicts, "per_group": {"all": main["per_group"],
                                                            "core": core},
            "static_invariance": [g["static_invariant"] for g in G], "ablations": abl,
            "stages": stages, "by_purpose": by_purpose(stages), "total": total,
            "variants": variants, "contingency": CONTINGENCY, "allowance_left": ALLOWANCE_LEFT,
            "scope_reduction": {"full_96": main["total"], "b_32_all_64_core": b},
            "scenarios": scenarios, "scenario_caps": scenario_caps,
            "runtime": runtime(G, main["per_group"], groups, pub, conflicts,
                               call_seconds())}  # fmt: skip


def add(*parts) -> dict:
    return {k: sum(p[k] for p in parts) for k in ("low", "high")}


def runtime(G, p, groups, pub, conflicts, gaps) -> dict:
    """Wall time of the single paid 4.2+4.3 process, which (pipeline answer=True)
    recomputes every retrieval before sending its calls one at a time. CPU from the
    measured precompute; API latency from the dev ledger (low: measured calls at the
    median gap; high: upper-bound calls at the mean gap). No rate-limit delay was ever
    observed (11,785 dev calls, none throttled), so none is added."""

    def sec(m):
        return _mean(g["seconds"][m] for g in G)

    internal = sum(sec(m) for m in G[0]["seconds"] if not m.startswith("randec"))
    per_cond = _mean(g["seconds"][m] / g["conditions"][m] for g in G for m in g["seconds"]
                     if m.startswith("randec"))  # fmt: skip
    n_cond = max(g["conditions"]["static"] for g in G)
    # A-MemGuard, sanitiser, MemLineage filter static; their "+R" filter R; S2-ID ~ SL
    published = 3 * sec("static") + 3 * sec("R") + sec("SL")
    randec = {
        "current": 2 * per_cond * n_cond,  # RandEC and RandEC+R in every condition
        # fix 1 (implemented): once per distinct context it filters (static, R)
        "randec_cached": per_cond / PROBES * (p["distinct_static"] + p["distinct_R"]),
    }
    ctx = {"low": p["distinct_static"], "high": p["distinct_static"] + p["distinct_R"]}
    per_ctx = pub["a_memguard_calls_per_context"] + pub["llm_sanitiser_calls_per_context"]
    calls = {k: p[f"answers_{k}"] + p[f"judged_{k}"] + conflicts * (1 if k == "low" else 2)
             + per_ctx * ctx[k] + pub["memlineage_questions_per_group"]
             for k in ("low", "high")}  # fmt: skip
    api = {"low": calls["low"] * gaps["median"], "high": calls["high"] * gaps["mean"]}
    sizes = (groups, REPLICATION_GROUPS, 32)
    cpu = {v: internal + randec[v] + published for v in randec}
    # both fixes (two_phase): the internal arms' and the published bases' contexts are
    # read from the free precompute; only S2-ID (timed as SL) is recomputed, and RandEC
    # runs (cached) on the stored contexts
    cpu["both_fixes"] = sec("SL") + randec["randec_cached"]
    wall = {v: {n: {k: n * (c + api[k]) / 3600 for k in ("low", "high")} for n in sizes}
            for v, c in cpu.items()}  # fmt: skip
    return {
        "precompute_internal_seconds_per_group": internal,
        "published_retrieval_seconds_per_group": published,
        "randec_seconds_per_condition": per_cond,
        "randec_seconds_per_group": randec,
        "calls_per_group": calls,
        "seconds_per_call": gaps,
        "api_seconds_per_group": api,
        "precompute_cpu_hours": {**{v: groups * (internal + r) / 3600 for v, r in randec.items()},
                                 "both_fixes": groups * 2 * internal / 3600},  # steps 1 + 2
        "paid_stage_wall_hours": wall,
    }


# ----------------------------------------------------------------------------- render


def usd(x):
    return f"−${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def render(res) -> str:
    rt, pa = res["runtime"], res["per_group"]["all"]
    L = ["## Protocol v2 dry-run cost and runtime estimate (step 1.12; free, no paid call)",
         "", f"Measured on {res['measured_groups']} dev groups (free precompute), scaled to "
         f"{res['groups']} held-out groups. Per-call costs are the actual USD of completed "
         "dev calls. **Low** = measured counts; **high** = upper bound for methods that "
         "cannot be measured free (each published filter, \"+R\" variant and S2-ID gives a "
         "new prompt for every distinct context of the retrieval it filters).", "",
         "| Stage | Purpose | Low | High |", "|---|---|---|---|"]  # fmt: skip
    for name, s in res["stages"].items():
        L.append(f"| {name} | {s['purpose']} | {usd(s['low'])} | {usd(s['high'])} |")
    t = res["total"]
    L += [
        f"| **Total** | | **{usd(t['low'])}** | **{usd(t['high'])}** |",
        "",
        "**Pending-scope variants** (change in cost if chosen):",
        "",
    ]
    for name, v in res["variants"].items():
        L.append(f"- {name}: {usd(v['low'])} to {usd(v['high'])}")
    g = res["generation"]
    L.append(
        f"- 3.1 hard bound (every call uses max_tokens; the cap stops it first): "
        f"{usd(g['hard_bound'])}"
    )
    L += ["", "**Scope scenarios** (every paid stage, with generation where it applies; "
          "ablations option A):", "", "| Scenario | Low | High | Within allowance? |",
          "|---|---|---|---|"]  # fmt: skip
    for name, v in res["scenarios"].items():
        fits = "yes" if v["high"] * (1 + res["contingency"]) <= res["allowance_left"] else (
            "only at low" if v["low"] <= res["allowance_left"] else "no")  # fmt: skip
        L.append(f"| {name} | {usd(v['low'])} | {usd(v['high'])} | {fits} |")
    L += ["", "**Proposed caps per scenario** (high × 1.3, rounded up; ✗ = above the code "
          "ceiling in `transport.V2_PURPOSES`):", ""]  # fmt: skip
    for name, cs in res["scenario_caps"].items():
        total_cap = sum(v["proposed_cap"] for v in cs.values())
        parts = ", ".join(f"{p.removeprefix('v2_')} {usd(v['proposed_cap'])}"
                          + ("" if v["fits_ceiling"] else " ✗") for p, v in cs.items())  # fmt: skip
        L.append(f"- {name.split(':')[0]}: {parts}; **sum {usd(total_cap)}**")
    sr = res["scope_reduction"]
    L += ["", "**Protocol §11 option (b)** (4.2+4.3 incl. published defences' calls): full "
          f"96 groups {usd(sr['full_96']['low'])}–{usd(sr['full_96']['high'])}; every cell on "
          "32 groups + Table 1/hypothesis cells on the other 64: "
          f"{usd(sr['b_32_all_64_core']['low'])}–{usd(sr['b_32_all_64_core']['high'])}.", "",
          f"**By paid purpose** (proposed cap = high × {1 + res['contingency']:.1f}, rounded "
          "up; each cap needs its own owner approval):", "",
          "| Purpose | Low | High | Proposed cap | Code ceiling | Fits |",
          "|---|---|---|---|---|---|"]  # fmt: skip
    for p, v in res["by_purpose"].items():
        L.append(
            f"| {p} | {usd(v['low'])} | {usd(v['high'])} | {usd(v['proposed_cap'])} "
            f"| {usd(v['code_ceiling'])} | {'yes' if v['fits_ceiling'] else '**no**'} |"
        )
    caps = sum(v["proposed_cap"] for v in res["by_purpose"].values())
    inv = res["static_invariance"]
    L += [
        "",
        f"Sum of proposed caps: {usd(caps)}. Remaining research allowance: about "
        f"{usd(res['allowance_left'])}.",
        "",
        f"**Per group (measured mean):** {pa['answers_low']:,.0f} distinct answer prompts, "
        f"{pa['judged_low']:,.0f} judged, {res['conflicts_per_group']:,.0f} distinct conflict "
        f"checks; the unmeasured methods add at most {pa['unmeasured_high']:,.0f} prompts. "
        "Original SAFE-Mem's retrieval varies across conditions for "
        f"{sum(i['varying'] for i in inv)} of {sum(i['probes'] for i in inv)} measured probes "
        f"({_mean(i['distinct'] for i in inv):,.0f} distinct contexts per group).",
        "",
        "**Runtime** (the paid 4.2+4.3 stage is ONE process that recomputes retrieval, "
        "then sends calls one at a time):",
        "",
        f"- CPU per group: internal methods "
        f"{rt['precompute_internal_seconds_per_group'] / 3600:.2f} h;"
        f" published methods' retrieval {rt['published_retrieval_seconds_per_group'] / 3600:.2f} h;"
        f" RandEC {rt['randec_seconds_per_group']['current'] / 3600:.2f} h in every condition, "
        f"{rt['randec_seconds_per_group']['randec_cached'] / 3600:.2f} h cached (fix 1);",
        f"- API: {rt['calls_per_group']['low']:,.0f}–{rt['calls_per_group']['high']:,.0f} calls "
        f"per group at {rt['seconds_per_call']['median']:.1f}–{rt['seconds_per_call']['mean']:.2f}"
        f" s per call = {rt['api_seconds_per_group']['low'] / 3600:.2f}–"
        f"{rt['api_seconds_per_group']['high'] / 3600:.2f} h per group; rate-limit delay: none "
        "observed in 11,785 dev calls;",
        "",
        "| Groups | Current code | Fix 1 (RandEC cache) | Fixes 1 + 2 (three steps) |",
        "|---|---|---|---|",
    ]  # fmt: skip
    w = rt["paid_stage_wall_hours"]
    for n in w["current"]:
        a, b, c = w["current"][n], w["randec_cached"][n], w["both_fixes"][n]
        L.append(f"| {n} | {a['low'] / 24:,.1f}–{a['high'] / 24:,.1f} days "
                 f"| {b['low'] / 24:,.1f}–{b['high'] / 24:,.1f} days "
                 f"| {c['low']:,.0f}–{c['high']:,.0f} h |")  # fmt: skip
    L.append(f"\nFree precompute CPU ({rt['precompute_cpu_hours']['current']:,.0f} h "
             f"current; {rt['precompute_cpu_hours']['both_fixes']:,.0f} h for steps 1 + 2 of "
             "fix 2), parallel across groups.")  # fmt: skip
    return "\n".join(L) + "\n"
