"""OpenAI adapter. One of only two places in the package allowed to import `openai`."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from ams.llm import pricing
from ams.llm.base import ContentFiltered, ProviderError
from ams.llm.types import (
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    Usage,
)

_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str | Callable[[], str] | None = None,
        base_url: str | None = None,
        provider: str = "openai",
        timeout: float = 120.0,
        require_key: bool = True,
        sdk_client: Any = None,
        budget_guard: Any = None,
        allow_estimated_billing: bool = False,
    ) -> None:
        """`sdk_client` lets a subclass supply an already-built SDK object."""
        self._budget_guard = budget_guard
        self._allow_estimated_billing = (
            allow_estimated_billing or os.environ.get("AMS_BUDGET_ALLOW_ESTIMATED_USAGE") == "1"
        )
        budget_path = os.environ.get("AMS_STRICT_BUDGET_PATH")
        if self._budget_guard is None and budget_path:
            from ams.llm.budget import BudgetGuard

            self._budget_guard = BudgetGuard(
                budget_path, limit_usd=os.environ.get("AMS_STRICT_BUDGET_LIMIT_USD", "25")
            )
        if self._budget_guard is not None and provider != "openrouter":
            raise ValueError("strict experiment billing is supported only for OpenRouter")
        if sdk_client is not None:
            self._provider = provider
            self._client = (
                sdk_client.with_options(max_retries=0)
                if self._budget_guard is not None
                else sdk_client
            )
            self.base_url = str(getattr(self._client, "base_url", ""))
            self._check_budget_endpoint()
            return

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ProviderError(
                provider, "openai SDK not installed; `uv pip install -e '.[openai]'`"
            ) from exc

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if require_key and not key:
            raise ProviderError(provider, "OPENAI_API_KEY is not set")

        resolved_base_url = base_url or os.environ.get("OPENAI_BASE_URL") or None

        if require_key and key and not key.startswith("sk-") and not resolved_base_url:
            raise ProviderError(
                provider,
                "OPENAI_API_KEY does not look like an api.openai.com key (expected an "
                "'sk-' prefix) and no endpoint is set. For an OpenAI-compatible gateway, "
                "give the endpoint: `openai:<model>@https://<host>/openai/v1`, or set "
                "OPENAI_BASE_URL. For classic Azure OpenAI, use the azure provider.",
            )
        self._provider = provider
        self.base_url = resolved_base_url
        sdk_options = {"max_retries": 0} if self._budget_guard is not None else {}
        self._client = OpenAI(
            api_key=key or "not-needed", base_url=resolved_base_url, timeout=timeout, **sdk_options
        )
        self._check_budget_endpoint()

    def _check_budget_endpoint(self) -> None:
        if self._budget_guard is not None:
            endpoint = urlparse(str(self.base_url))
            if (
                endpoint.scheme != "https"
                or endpoint.hostname != "openrouter.ai"
                or endpoint.path.rstrip("/") != "/api/v1"
                or endpoint.query
                or endpoint.fragment
            ):
                raise ValueError("strict billing requires the official HTTPS OpenRouter endpoint")

    @property
    def provider(self) -> str:
        return self._provider

    def complete(self, request: ChatRequest) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.reasoning_effort is not None and self._provider == "openrouter":
            effort = request.reasoning_effort
            kwargs["extra_body"] = {
                "reasoning": {"enabled": False} if effort == "none" else {"effort": effort}
            }
        elif request.reasoning_effort is not None:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            kwargs["reasoning_effort"] = request.reasoning_effort
        if request.stop:
            kwargs["stop"] = list(request.stop)
        reservation = None
        if self._budget_guard is not None:
            from ams.llm.budget import BudgetAccountingError

            if request.reasoning_effort not in (None, "none"):
                raise BudgetAccountingError("unbudgeted reasoning is forbidden")
            extra = kwargs.setdefault("extra_body", {})
            ceiling = self._budget_guard.snapshot()
            extra["provider"] = {
                "max_price": {
                    "prompt": float(ceiling["max_input_per_mtok"]),
                    "completion": float(ceiling["max_output_per_mtok"]),
                    "request": 0,
                },
                "allow_fallbacks": False,
                "require_parameters": True,
            }
            # Explicit disabled entries override defaults unless the account prevents overrides.
            # The software guard remains scoped to requests dispatched by this run.
            extra["plugins"] = [
                {"id": plugin, "enabled": False}
                for plugin in ("web", "file-parser", "response-healing")
            ]
            reservation = self._budget_guard.reserve(
                request.model, request.max_tokens, stage="chat"
            )
        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            if reservation is not None:
                self._budget_guard.mark_unknown(
                    reservation,
                    type(exc).__name__,
                    metadata={
                        "request_id": request.cache_key(self.provider),
                        "requested_model": request.model,
                    },
                )
            raise self._wrap(exc) from exc

        estimated_usage = None
        if reservation is not None:
            estimated_usage = self._account_response(resp, request, reservation)

        choice = resp.choices[0]
        usage = estimated_usage or self._usage(getattr(resp, "usage", None), request.model)
        return ChatResponse(
            text=choice.message.content or "",
            model=resp.model,
            provider=self._provider,
            usage=usage,
            raw_finish_reason=choice.finish_reason,
        )

    def _account_response(self, resp: Any, request: ChatRequest, reservation: str) -> Usage | None:
        """Keep unverified attempts reserved; only authoritative charges release holds."""
        raw = getattr(resp, "usage", None)
        metadata = self._billing_metadata(resp, request)
        if getattr(raw, "is_byok", False):
            self._stop_billing(reservation, "byok_billing", metadata)
        raw_cost = getattr(raw, "cost", None)
        cost = None
        if raw_cost is not None:
            try:
                cost = Decimal(str(raw_cost))
                if not cost.is_finite() or cost < 0:
                    raise ValueError("invalid charge")
            except (InvalidOperation, ValueError, TypeError):
                self._stop_billing(reservation, "invalid_billing", metadata)
        if metadata["usage_details"]["native_usage_invalid"]:
            self._stop_billing(reservation, "invalid_billing", metadata)

        returned_model = getattr(resp, "model", None)
        model_matches = isinstance(returned_model, str) and (
            returned_model == request.model
            or re.fullmatch(re.escape(request.model) + r"-\d{4}-\d{2}-\d{2}", returned_model)
        )
        if returned_model and not model_matches:
            self._stop_billing(reservation, "unexpected_response_model", metadata)

        choices = getattr(resp, "choices", None)
        if (
            getattr(resp, "error", None)
            or not choices
            or getattr(choices[0], "message", None) is None
        ):
            # A parsed HTTP 200 error is not a model refusal. Retrying must reserve again.
            if cost is not None and cost > self._reservation_ceiling(request):
                self._budget_guard.settle(reservation, cost, metadata=metadata)
            self._budget_guard.mark_unknown(reservation, "IncompleteResponse", metadata=metadata)
            raise ProviderError(
                self.provider,
                "provider returned no completion; billing hold retained",
                retryable=True,
            )
        if not model_matches:
            self._stop_billing(reservation, "unexpected_response_model", metadata)

        if cost is None:
            if not self._allow_estimated_billing:
                self._stop_billing(reservation, "unverified_billing", metadata)
            settings = self._budget_guard.snapshot()
            ceiling = self._reservation_ceiling(request, settings)
            inp = metadata.get("input_tokens", 0)
            out = metadata.get("output_tokens", 0)
            details = metadata["usage_details"]
            native_estimate = Decimal(
                str(pricing.estimate_cost(self.provider, request.model, inp, out))
            )
            if (
                native_estimate > ceiling
                or inp > settings["context_token_bound"]
                or out > request.max_tokens
            ):
                self._stop_billing(reservation, "usage_price_breach", metadata)
            if details["input_tokens_known"] and details["output_tokens_known"]:
                # Native token counts are reported, never inferred from prompt text.
                estimated_cost = native_estimate
            else:
                # Unknown counts remain zero in Usage; charge its full hold in the ledger.
                estimated_cost = ceiling
            metadata.update(
                estimated_cost_usd=float(estimated_cost), cost_missing=True, billing_verified=False
            )
            self._budget_guard.mark_unknown(reservation, "MissingBillingCost", metadata=metadata)
            return Usage(inp, out, float(estimated_cost))

        # Preserve the existing authoritative receipt format for complete billed responses.
        self._budget_guard.settle(
            reservation,
            cost,
            metadata={
                "generation_id": getattr(resp, "id", ""),
                "model": returned_model,
                "input_tokens": getattr(raw, "prompt_tokens", 0),
                "output_tokens": getattr(raw, "completion_tokens", 0),
            },
        )
        return None

    def _reservation_ceiling(
        self, request: ChatRequest, settings: dict[str, Any] | None = None
    ) -> Decimal:
        settings = settings if settings is not None else self._budget_guard.snapshot()
        amount = (
            Decimal(settings["max_input_per_mtok"]) * settings["context_token_bound"]
            + Decimal(settings["max_output_per_mtok"]) * request.max_tokens
        ) / 1_000_000
        return amount.quantize(Decimal("0.000000001"), rounding=ROUND_CEILING)

    def _billing_metadata(self, resp: Any, request: ChatRequest) -> dict[str, Any]:
        raw = getattr(resp, "usage", None)
        metadata: dict[str, Any] = {
            "request_id": request.cache_key(self.provider),
            "requested_model": request.model,
            "usage_details": {"native_usage_invalid": False},
        }
        for key, value in (
            ("generation_id", getattr(resp, "id", None)),
            ("model", getattr(resp, "model", None)),
        ):
            if (
                isinstance(value, str)
                and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value)
                and "sk-" not in value.lower()
            ):
                metadata[key] = value
        for native, key in (
            ("prompt_tokens", "input_tokens"),
            ("completion_tokens", "output_tokens"),
        ):
            value = getattr(raw, native, None)
            known = isinstance(value, int) and not isinstance(value, bool) and value >= 0
            metadata["usage_details"][f"{key}_known"] = known
            if known:
                metadata[key] = value
            elif value is not None:
                metadata["usage_details"]["native_usage_invalid"] = True
        return metadata

    def _stop_billing(self, reservation: str, reason: str, metadata: dict[str, Any]) -> None:
        from ams.llm.budget import BudgetAccountingError

        self._budget_guard.mark_unknown(reservation, reason, metadata=metadata)
        self._budget_guard.halt(reason)
        raise BudgetAccountingError("provider billing could not be verified; dispatch stopped")

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        if self._budget_guard is not None:
            raise ValueError("paid embeddings are forbidden in the approved experiment")
        try:
            resp = self._client.embeddings.create(model=request.model, input=list(request.texts))
        except Exception as exc:
            raise self._wrap(exc) from exc
        return EmbedResponse(
            vectors=tuple(tuple(d.embedding) for d in resp.data),
            model=resp.model,
            provider=self._provider,
            usage=self._usage(getattr(resp, "usage", None), request.model),
        )

    def _usage(self, raw: Any, model: str) -> Usage:
        if raw is None:
            return Usage()
        inp = getattr(raw, "prompt_tokens", 0) or 0
        out = getattr(raw, "completion_tokens", 0) or 0
        cost = pricing.estimate_cost(self._provider, model, inp, out)
        if self._provider == "openrouter":
            reported = getattr(raw, "cost", None)
            if reported is not None:
                try:
                    parsed = Decimal(str(reported))
                    if parsed.is_finite() and parsed >= 0:
                        cost = float(parsed)
                except InvalidOperation:
                    pass
        return Usage(inp, out, cost)

    def _wrap(self, exc: Exception) -> Exception:
        text = str(exc)
        if any(
            m in text
            for m in ("content_filter", "ResponsibleAIPolicy", "cyber_policy", "content_policy")
        ):
            body = getattr(exc, "body", None)
            inner = (body or {}).get("innererror", {}) if isinstance(body, dict) else {}
            return ContentFiltered(self._provider, text[:200], inner.get("content_filter_result"))
        status = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        retryable = status in _RETRYABLE_STATUS if status else _looks_transient(exc)
        if "insufficient_quota" in text or "credit_balance_exhausted" in text:
            retryable = False
        return ProviderError(self._provider, f"{type(exc).__name__}: {exc}", retryable=retryable)


def _looks_transient(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    return any(k in name for k in ("timeout", "connection", "ratelimit", "apierror"))


DEFAULT_AZURE_API_VERSION = "2024-10-21"


def entra_token_provider(scope: str = "https://ai.azure.com/.default") -> Callable[[], str]:
    """A bearer-token callable for an Azure AI Services endpoint."""
    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ProviderError(
            "azure_entra",
            "azure-identity not installed; `uv pip install -e '.[azure]'`",
        ) from exc
    return get_bearer_token_provider(DefaultAzureCredential(), scope)


def resource_key_var(endpoint: str) -> str:
    """The env var holding the key for one Azure resource, so several resources
    can be used at once: https://my-res.services.ai.azure.com/... -> AZURE_AI_KEY_MY_RES."""
    from urllib.parse import urlparse

    label = (urlparse(endpoint).hostname or "").split(".")[0]
    return "AZURE_AI_KEY_" + "".join(c if c.isalnum() else "_" for c in label).upper()


class AzureAIServicesClient(OpenAIClient):
    """Azure AI Services v1, reached as a plain OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        deployment: str,
        endpoint: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        resolved = (
            endpoint
            or os.environ.get("AZURE_AI_ENDPOINT")
            or os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        if not resolved:
            raise ProviderError(
                "aiservices",
                "no endpoint. Set AZURE_AI_ENDPOINT, or use the spec form "
                "`aiservices:<deployment>@https://<resource>.services.ai.azure.com/openai/v1`",
            )
        resolved = resolved.rstrip("/")
        if not resolved.endswith("/openai/v1"):
            resolved = f"{resolved}/openai/v1"
        key = (
            api_key
            or os.environ.get(resource_key_var(resolved))
            or os.environ.get("AZURE_AI_API_KEY")
            or os.environ.get("AZURE_AI_KEY")
        )
        self.deployment = deployment
        super().__init__(
            api_key=key or entra_token_provider(),
            base_url=resolved,
            provider="aiservices",
            timeout=timeout,
            require_key=False,
        )


class AzureOpenAIClient(OpenAIClient):
    """Azure OpenAI. Same wire format, different addressing."""

    def __init__(
        self,
        *,
        deployment: str,
        endpoint: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ProviderError(
                "azure", "openai SDK not installed; `uv pip install -e '.[openai]'`"
            ) from exc

        key = api_key or os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("azure", "AZURE_OPENAI_API_KEY (or OPENAI_API_KEY) is not set")

        resolved_endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not resolved_endpoint:
            raise ProviderError(
                "azure",
                "no endpoint. Set AZURE_OPENAI_ENDPOINT, or use the spec form "
                "`azure:<deployment>@https://<resource>.openai.azure.com`",
            )
        version = (
            api_version or os.environ.get("AZURE_OPENAI_API_VERSION") or DEFAULT_AZURE_API_VERSION
        )
        self.deployment = deployment
        super().__init__(
            provider="azure",
            sdk_client=AzureOpenAI(
                api_key=key,
                azure_endpoint=resolved_endpoint.rstrip("/"),
                api_version=version,
                timeout=timeout,
            ),
        )


class VLLMClient(OpenAIClient):
    """Self-hosted open-weight backbone behind an OpenAI-compatible server."""

    def __init__(self, *, base_url: str, timeout: float = 600.0) -> None:
        super().__init__(
            api_key="EMPTY",
            base_url=base_url,
            provider="vllm",
            timeout=timeout,
            require_key=False,
        )
