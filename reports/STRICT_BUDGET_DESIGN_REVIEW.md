# Strict budget design review

Reviewed 2026-10-28 using public official documentation only. No account settings, environment variables, credentials, or paid endpoints were accessed for this review. This reviews a proposed transport design; it does not certify its implementation or an unconditional billing guarantee.

## Result

The proposed atomic pre-dispatch reservation can bound the run's model-token charges under the conditions below. The old after-response ledger poll cannot provide that bound. A dedicated non-resetting provider cap below $25 is useful additional protection, but account defaults and BYOK must be checked before launch.

## Request controls

The following provider object follows OpenRouter's documented routing interface:

```json
{
  "provider": {
    "max_price": {"prompt": 0.15, "completion": 0.60, "request": 0},
    "allow_fallbacks": false,
    "require_parameters": true
  }
}
```

`prompt` and `completion` ceilings are USD per million tokens; `request` is the ceiling on per-request pricing. These filter eligible endpoints rather than setting a total dollar cap. `require_parameters` excludes endpoints that do not support the supplied parameters. Disabling provider fallbacks changes transport routing and must be recorded, while keeping model identity and prompts fixed. [Official provider routing](https://openrouter.ai/docs/guides/routing/provider-selection#max-price).

The public [GPT-4o-mini endpoint catalog](https://openrouter.ai/api/v1/models/openai/gpt-4o-mini/endpoints) currently lists a 128,000-token context and 16,384 maximum completion tokens. OpenAI's endpoint lists `max_tokens`; the Azure entries list `max_completion_tokens`. With `max_tokens` plus required-parameter support, compatible endpoint selection may therefore narrow. The ordinary OpenAI endpoint currently has the proposed $0.15/$0.60 rates. Recheck this public metadata before launch; reject unsupported or differently priced requests.

## Reservation invariant

For each physical request attempt, reserve at least:

```text
R = 128000 * 0.15 / 1000000
  + request.max_tokens * 0.60 / 1000000
```

This deliberately overcounts context rather than relying on an approximate local tokenizer. Require a positive output limit no greater than the verified model output limit, plaintext messages only, and the exact approved model. Using input-context size plus output is conservative even where the context ceiling includes both.

In one persistent atomic database, ensure `settled + uncertain + reserved + R <= approved_budget` before dispatch. Reserve separately for every managed retry. Disable SDK hidden retries (`max_retries=0`) so there are no unreserved physical attempts. On timeout, interruption, malformed response, missing cost, or ambiguous failure, retain the maximum hold. Do not automatically release holds at process restart. Persist attempts before sending, and do not allow another process to bypass the same shared budget.

On a normal response, use OpenRouter's reported cost and token counts, reject negative/nonfinite/missing values, and retain enough information to reconcile request IDs. A response exceeding its reserved maximum is a contract/configuration violation: stop immediately and do not pretend the invariant still proves the bill. [Official usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

## Important hole: an empty plugin list does not disable defaults

`plugins: []` is insufficient. OpenRouter applies an enabled account-default plugin when that plugin is omitted from the request. The documented per-plugin disable shape is:

```json
{"plugins": [{"id": "web", "enabled": false}]}
```

An account or organization can enable **Prevent overrides**, which stops a request from disabling or changing that plugin. Verify default plugins are off and there are no enforced overrides. Explicitly disabling known IDs provides defense in depth, not proof against an unknown or enforced account default. [Plugin defaults and precedence](https://openrouter.ai/docs/guides/features/plugins#default-plugin-settings).

Known relevant IDs documented on official pages are `web`, `file-parser`, `response-healing`, `alignment`, and `armor`. Web search and some PDF engines introduce separate charges. Alignment can evaluate and retry model outputs; even a free modifier can change reproduction behavior. The general overview documents `enabled: false`, but not every plugin-specific schema demonstrates that field, so account-side absence is the clearest prerequisite. No server tools, search options, model variants such as `:online`, file/image inputs, presets, or automatic prompt transforms should be enabled for these plaintext original-method runs. [PDF parser](https://openrouter.ai/docs/guides/overview/multimodal/pdfs), [Alignment](https://openrouter.ai/docs/guides/features/plugins/alignment), [Armor](https://openrouter.ai/docs/guides/features/plugins/armor), [Response Healing](https://openrouter.ai/docs/guides/features/plugins/response-healing).

## BYOK and cash charges

OpenRouter account cost is not necessarily the whole cost under BYOK: the upstream provider bills inference separately. Verify BYOK is disabled or cannot apply to the run's key/model. Otherwise a budget must include upstream inference plus any OpenRouter fee, and the key's default exclusion of BYOK spend must not hide usage. [BYOK documentation](https://openrouter.ai/docs/guides/overview/auth/byok).

For ordinary OpenRouter credits, token inference uses provider list rates. Standard/Business platform fees occur when credits are purchased, not on each inference request. Do not purchase credits during this run. If the user's $25 refers to new card charges as well as consumed credits, also verify account auto-top-up is disabled: an automatic credit purchase is outside this local inference ledger. [Official pricing](https://openrouter.ai/pricing).

## Provider-side cap

Use a dedicated key with a lower non-resetting total cap, for example $20, and verify `limit`, `limit_reset: null`, `limit_remaining`, and baseline usage with the free current-key endpoint. It must not be shared with another workload. Configuring the cap through the API requires a management key; an ordinary inference key can inspect itself but cannot administer caps. [Update-key API](https://openrouter.ai/docs/api/api-reference/api-keys/update-keys).

The provider's documented budget checks allow already-dispatched requests to finish, so the provider cap alone is not an exact concurrency-safe ceiling. The local reservation invariant supplies the missing preauthorization, provided the pricing and account prerequisites are verified. [Workspace-budget FAQ](https://openrouter.ai/docs/guides/features/workspaces/workspace-budgets#faq).

## Launch prerequisites

Before paid execution: verify the dedicated non-resetting cap; confirm no applicable account-default/enforced plugins, BYOK, or automatic credit purchases; validate price and token ceilings; test simultaneous reservations, restart/unknown-failure retention, and every retry path offline; freeze the updated transport code and configs into a new plan. If those normal-contract conditions cannot be verified, inform the user that an exact $25 cap is not yet established and do not launch the experiment.
