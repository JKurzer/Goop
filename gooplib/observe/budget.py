"""Fail-closed, per-request reservation for the staged private Astra trials.

Invoke using the installed Code Puppy Python, never by editing global config.
The token-count endpoint and any unknown provider-side fees remain outside this
local guard; the launcher treats uncertain accounting as a stop, not a success.
"""

import json
import os
from decimal import Decimal
from pathlib import Path

HARD_CAP = Decimal(7)
MAX_INPUT = 150_000
MAX_OUTPUT = 8_192
# Conservative ceilings for this fixed model's text-token input/output rates.
INPUT_USD_PER_MILLION = Decimal("12.5")
OUTPUT_USD_PER_MILLION = Decimal(50)
MAX_REQUEST_USD = (
    MAX_INPUT * INPUT_USD_PER_MILLION + MAX_OUTPUT * OUTPUT_USD_PER_MILLION
) / 1_000_000


def install_guard():
    from code_puppy import model_factory, private_inference
    from code_puppy.agents import _builder, _runtime, retry_profiles
    from code_puppy.tools import subagent_invocation
    from pydantic_ai._genai_prices import best_effort_price
    from pydantic_ai.models import openai as openai_model
    from pydantic_ai.usage import RequestUsage, UsageLimitExceeded, UsageLimits

    previous = Decimal(os.environ["GOOP_PREVIOUS_USD"])
    if previous < 0 or previous >= HARD_CAP:
        raise RuntimeError("Invalid or exhausted previous-spend ledger")
    remaining = HARD_CAP - previous
    ledger = Path(os.environ["GOOP_GUARD_LEDGER"]).resolve()
    if ledger.exists() or not ledger.parent.is_dir():
        raise RuntimeError("Require a new existing private ledger parent")
    if remaining < MAX_REQUEST_USD:
        raise RuntimeError("Insufficient reserved budget for the first request")
    prices = {
        "model_name": "gpt-6-astra",
        "provider_api_url": "https://api.openai.com/v1",
        "provider_name": "openai",
    }
    priced = best_effort_price(
        RequestUsage(
            input_tokens=MAX_INPUT,
            cache_write_tokens=MAX_INPUT,
            output_tokens=MAX_OUTPUT,
        ),
        **prices,
    )
    if priced is None or priced.total_price > MAX_REQUEST_USD:
        raise RuntimeError("Published model price exceeds per-request reservation")

    class ReservedLimits(UsageLimits):
        def __init__(self, **kwargs):
            if kwargs.keys() != {"request_limit"}:
                raise RuntimeError(
                    "Unexpected usage-limit signature; refusing model call"
                )
            kwargs["request_limit"] = None
            super().__init__(
                **kwargs,
                cost_limit=remaining,
                per_request_input_tokens_limit=MAX_INPUT,
                count_tokens_before_request=True,
            )
            self._last_counted_input = None
            self._last_actual_cost = Decimal(0)
            self._last_actual_requests = 0

        def check_per_request_input_tokens(self, input_tokens):
            self._last_counted_input = input_tokens
            return super().check_per_request_input_tokens(input_tokens)

        def check_before_request(self, usage):
            super().check_before_request(usage)
            if usage.requests != self._last_actual_requests:
                raise UsageLimitExceeded("Unreconciled model response; no next request")
            if self._last_counted_input is None:
                reserved = MAX_REQUEST_USD
            else:
                if usage.cost is None or usage.cost < self._last_actual_cost:
                    raise UsageLimitExceeded("Cannot price outgoing counted request")
                reserved = (
                    self._last_counted_input * INPUT_USD_PER_MILLION
                    + MAX_OUTPUT * OUTPUT_USD_PER_MILLION
                ) / 1_000_000
            if self._last_actual_cost + reserved > remaining:
                raise UsageLimitExceeded(
                    "Insufficient dollar reservation for next request"
                )

        def check_cost(self, usage, *, warn_if_cost_unavailable=True):
            if usage.cost is None and usage.requests:
                raise UsageLimitExceeded("Missing provider price; stop immediately")
            if usage.cost is not None:
                if usage.cost < self._last_actual_cost:
                    raise UsageLimitExceeded("Cost went backwards; stop")
                self._last_actual_cost = usage.cost
                self._last_actual_requests = usage.requests
                self._last_counted_input = None
                payload = {
                    "actual_cell_usd": str(usage.cost),
                    "previous_usd": str(previous),
                    "total_usd": str(previous + usage.cost),
                    "requests": usage.requests,
                }
                temporary = ledger.with_name(ledger.name + ".tmp")
                with temporary.open("w", encoding="ascii") as stream:
                    json.dump(payload, stream, indent=2)
                    stream.write("\n")
                os.replace(temporary, ledger)
            super().check_cost(usage, warn_if_cost_unavailable=warn_if_cost_unavailable)

    _runtime.UsageLimits = ReservedLimits
    original_settings = model_factory.make_model_settings

    def capped_settings(*args, **kwargs):
        settings = original_settings(*args, **kwargs)
        settings["max_tokens"] = min(int(settings["max_tokens"]), MAX_OUTPUT)
        settings["max_retries"] = 0
        return settings

    model_factory.make_model_settings = capped_settings
    _builder.make_model_settings = capped_settings

    async def refuse_subagents(*args, **kwargs):
        raise RuntimeError("Subagents disabled for the per-test budget")

    subagent_invocation._invoke_agent_impl = refuse_subagents
    private_inference.run_private_prompt = refuse_subagents
    original_with_retries = openai_model.with_max_retries
    openai_model.with_max_retries = lambda client, settings, **kwargs: (
        original_with_retries(client, {**settings, "max_retries": 0}, **kwargs)
    )
    original_resolve = retry_profiles.resolve
    retry_profiles.resolve = lambda role, model_name=None: retry_profiles.make(
        role, original_resolve(role, model_name).strategy, 1
    )

    async def once(call, *, agent):
        return await call()

    _runtime.run_with_exception_retry = once
    print(
        f"GUARD_READY previous={previous} remaining={remaining} "
        f"max_input={MAX_INPUT} max_output={MAX_OUTPUT} "
        f"first_request_reserve={MAX_REQUEST_USD}",
        flush=True,
    )
    return ReservedLimits
