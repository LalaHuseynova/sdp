"""Transparent conditional estimates; not token measurements or a live spending guard."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal, InvalidOperation

from ams.research.dynamic.models import LedgerError, check, integer

from .study import validate_config


def money(value) -> Decimal:
    check(type(value) in {str, int, float, Decimal}, "Invalid monetary value")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise LedgerError("Invalid monetary amount") from exc
    check(result.is_finite() and result >= 0, "Nonfinite/negative amount")
    return result


def usd(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_CEILING))


def price_snapshot(pricing: dict) -> tuple[Decimal, Decimal]:
    check(
        pricing["schema"] == "dynamic-pricing-observation-v1"
        and pricing["provider"] == "openrouter"
        and pricing["model"] == "openai/gpt-4o-mini"
        and pricing["currency"] == "USD",
        "Unsupported/unknown pricing; never treat an unpriced model as free",
    )
    inp, out = money(pricing["input_usd_per_million"]), money(pricing["output_usd_per_million"])
    check(inp > 0 and out > 0, "Chat prices must be positive")
    return inp, out


def counts(bags: int, config: dict, grounded: int, attacks: int) -> dict:
    integer(bags, "bags", 1)
    check(grounded in {12, 16} and attacks in {15, 19}, "Use declared planning endpoints")
    variants, arms = len(config["scenarios"]), len(config["arms"])
    trajectories = bags * variants * arms
    return {
        "bags": bags,
        "trajectories": trajectories,
        "original_questions": trajectories * 27,
        "grounded_questions": trajectories * grounded,
        "memory_answers": trajectories * (27 + grounded),
        "no_memory_answers": bags * 36,
        # Every original question plus every safe-source QA control at most once.
        "classifier_response_catalog": bags * 48,
        "original_answer_judgments": trajectories * 27,
        "retrieved_entry_judgments": trajectories * attacks,
        "written_entry_judgments": bags * 20,
        "no_memory_attack_judgments": bags * 20,
        "logical_audit_tickets_all_arms": trajectories * 5,
        "logical_audit_tickets_per_arm": bags * variants * 5,
        "shared_audit_jobs": bags * variants * 5,
    }


def estimate_scope(bags: int, config: dict, pricing: dict, *, high: bool, maximum: bool) -> dict:
    validate_config(config)
    check(config["chat_model"] == pricing["model"], "Pricing model differs from planned model")
    inp, out = price_snapshot(pricing)
    c = counts(bags, config, 16 if high else 12, 19 if high else 15)
    profiles = {
        "memory_answers": (8000 if maximum else 3500, 200),
        "no_memory_answers": (1500 if maximum else 750, 200),
        "classifier_response_catalog": (1500 if maximum else 350, 24),
        "original_answer_judgments": (2500 if maximum else 1000, 120),
        "retrieved_entry_judgments": (8000 if maximum else 3000, 120),
        "written_entry_judgments": (4000 if maximum else 1500, 120),
        "no_memory_attack_judgments": (2500 if maximum else 1000, 120),
        "conflict_checks": (2048 if maximum else 900, 6),
    }
    c["conflict_checks"] = c["memory_answers"] * (6 if maximum else 1)
    stages = []
    total = Decimal(0)
    full_context = Decimal(0)
    attempts = config["max_physical_attempts_per_logical_call"]
    for name, (input_tokens, output_tokens) in profiles.items():
        calls = c[name]
        cost = Decimal(calls) * (input_tokens * inp + output_tokens * out) / 1_000_000
        reservation = (
            Decimal(calls * attempts)
            * (config["context_reservation_tokens"] * inp + output_tokens * out)
            / 1_000_000
        )
        total += cost
        full_context += reservation
        stages.append(
            {
                "stage": name,
                "cold_logical_calls_budgeted": calls,
                "input_tokens_assumed_per_call": input_tokens,
                "output_ceiling_per_call": output_tokens,
                "one_attempt_estimate_usd": usd(cost),
                "max_physical_attempts": calls * attempts,
            }
        )
    retry = money(attempts) if maximum else money(config["working_retry_multiplier"])
    factor = money(config["stress_extra_headroom_multiplier"]) if maximum else Decimal(1)
    total_with_retries = total * retry
    recommended = total_with_retries * factor
    return {
        "counts": c,
        "stages": stages,
        "one_attempt_estimate_usd": usd(total),
        "retry_multiplier": str(retry),
        "with_retries_usd": usd(total_with_retries),
        "extra_headroom_multiplier": str(factor),
        "with_headroom_usd": usd(recommended),
        "full_context_all_attempts_reservation_usd": usd(full_context),
        "proposed_cap_covers_this_scenario": recommended
        <= money(config["proposed_total_spending_cap_usd"]),
        "completion_within_cap_guaranteed": False,
    }


def estimate(config: dict, pricing: dict) -> dict:
    validate_config(config)
    price_snapshot(pricing)
    scopes = {
        "development": config["development_bags"],
        "locked_primary": config["locked_bags"],
        "all_selected": config["development_bags"] + config["locked_bags"],
    }
    result = {}
    for scope, bags in scopes.items():
        result[scope] = {
            "working_low": estimate_scope(bags, config, pricing, high=False, maximum=False),
            "working_high": estimate_scope(bags, config, pricing, high=True, maximum=False),
            "stress": estimate_scope(bags, config, pricing, high=True, maximum=True),
        }
    return {
        "schema": "dynamic-conditional-cost-v1",
        "model": pricing["model"],
        "pricing_source": pricing["model_page"],
        "pricing_checked_on": pricing["checked_on"],
        "input_usd_per_million": pricing["input_usd_per_million"],
        "output_usd_per_million": pricing["output_usd_per_million"],
        "scopes": result,
        "proposed_cap_usd": config["proposed_total_spending_cap_usd"],
        "cap_activated": False,
        "measured_token_estimate": False,
        "basis": "conditional token-length/conflict-rate assumptions, no answer cache discounts",
        "zero_paid_stages": {
            "memory_reconstruction": (
                "exact frozen records only; cache misses abort, no fresh extraction"
            ),
            "embeddings": "existing local MiniLM/cache only; no download or paid fallback",
            "content_detector": "disabled uniformly",
            "oracle_verification": (
                "preannotated shared tickets; annotation labor not free or priced here"
            ),
            "grounded_qa_judging": (
                "validated aliases and blinded human review, no LLM judge scheduled"
            ),
        },
        "unbudgeted_expansions": [
            "new extraction/reannotation",
            "real verifier",
            "grid tuning",
            "optional reference arms",
            "robustness suite",
            "second model",
            "full MPBench",
        ],
        "unknown_costs": list(pricing["not_included"]),
        "guard_note": "The proposed stop cap is not the full-context worst-case completion cost. "
        "Future transport must reserve every physical attempt; unknown outcomes retain holds.",
    }
