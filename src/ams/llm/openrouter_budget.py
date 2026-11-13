"""Free, credential-safe checks for an experiment's provider credit allowance."""

from __future__ import annotations

import hashlib

import httpx


class ProviderBudgetNotVerified(RuntimeError):
    pass


def current_key_budget(api_key: str, *, client: httpx.Client | None = None) -> dict:
    """Read current-key metadata; never return the token, its label, or a key hash."""
    if not api_key:
        raise ProviderBudgetNotVerified("OPENROUTER_API_KEY is missing")
    owned = client is None
    session = client or httpx.Client(timeout=30)
    try:
        try:
            response = session.get(
                "https://openrouter.ai/api/v1/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()["data"]
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise ProviderBudgetNotVerified("could not verify provider credit controls") from exc
    finally:
        if owned:
            session.close()
    fields = (
        "limit",
        "limit_remaining",
        "limit_reset",
        "usage",
        "include_byok_in_limit",
        "is_management_key",
        "effective_budget",
        "budgets",
    )
    return {key: data.get(key) for key in fields}


def credential_fingerprint(api_key: str) -> str:
    """One-way identity for detecting accidental key changes between approved jobs."""
    return hashlib.sha256(api_key.encode()).hexdigest()
