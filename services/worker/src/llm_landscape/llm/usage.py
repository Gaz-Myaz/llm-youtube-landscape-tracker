from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from llm_landscape.llm.base import EnrichmentResult


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def plus(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass(frozen=True)
class CostRates:
    input_usd_per_1m_tokens: float
    output_usd_per_1m_tokens: float
    source: str


_DEFAULT_RATES_USD_PER_1M_TOKENS = {
    "gemini": CostRates(0.30, 2.50, "default"),
    "google": CostRates(0.30, 2.50, "default"),
    "google-gemini": CostRates(0.30, 2.50, "default"),
    "openai": CostRates(0.40, 1.60, "default"),
    "openai-compatible": CostRates(0.40, 1.60, "default"),
    "openai_compatible": CostRates(0.40, 1.60, "default"),
    "anthropic": CostRates(0.80, 4.00, "default"),
    "claude": CostRates(0.80, 4.00, "default"),
}


def aggregate_token_usage(enrichments: Iterable[EnrichmentResult]) -> TokenUsage:
    usage = TokenUsage()
    for enrichment in enrichments:
        usage = usage.plus(token_usage_from_raw_response(enrichment.raw_response))
    return usage


def token_usage_from_raw_response(raw_response: dict | None) -> TokenUsage:
    usage = _usage_payload(raw_response)
    if not isinstance(usage, dict):
        return TokenUsage()

    input_tokens = _token_count(
        usage,
        "prompt_tokens",
        "input_tokens",
        "promptTokenCount",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    output_tokens = _token_count(
        usage,
        "completion_tokens",
        "output_tokens",
        "candidatesTokenCount",
    )
    total_tokens = _first_token_count(usage, "total_tokens", "totalTokenCount")
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    elif input_tokens == 0 and output_tokens == 0:
        input_tokens = total_tokens
    elif output_tokens == 0 and total_tokens >= input_tokens:
        output_tokens = total_tokens - input_tokens
    return TokenUsage(
        input_tokens=max(0, input_tokens),
        output_tokens=max(0, output_tokens),
        total_tokens=max(0, total_tokens),
    )


def _usage_payload(raw_response: dict | None) -> dict | None:
    if not isinstance(raw_response, dict):
        return None

    usage = raw_response.get("usage")
    if not isinstance(usage, dict):
        usage = raw_response.get("usage_metadata")
    if not isinstance(usage, dict):
        usage = raw_response.get("usageMetadata")
    if isinstance(usage, dict):
        return usage

    nested_response = raw_response.get("response")
    if isinstance(nested_response, dict):
        return _usage_payload(nested_response)

    return None


def cost_rates_for(provider_name: str) -> CostRates:
    normalized = provider_name.strip().lower()
    defaults = _DEFAULT_RATES_USD_PER_1M_TOKENS.get(normalized, CostRates(0.0, 0.0, "default"))
    prefix = _rate_prefix(normalized)
    input_rate, input_source = _rate_from_env(
        f"{prefix}_INPUT_USD_PER_1M_TOKENS",
        "LLM_INPUT_USD_PER_1M_TOKENS",
        default=defaults.input_usd_per_1m_tokens,
    )
    output_rate, output_source = _rate_from_env(
        f"{prefix}_OUTPUT_USD_PER_1M_TOKENS",
        "LLM_OUTPUT_USD_PER_1M_TOKENS",
        default=defaults.output_usd_per_1m_tokens,
    )
    source = "env" if "env" in {input_source, output_source} else defaults.source
    return CostRates(input_rate, output_rate, source)


def estimate_cost_usd(usage: TokenUsage, rates: CostRates) -> float:
    cost = (
        usage.input_tokens / 1_000_000 * rates.input_usd_per_1m_tokens
        + usage.output_tokens / 1_000_000 * rates.output_usd_per_1m_tokens
    )
    return round(max(0.0, cost), 6)


def _token_count(usage: dict, *names: str) -> int:
    return sum(_int_value(usage.get(name)) for name in names)


def _first_token_count(usage: dict, *names: str) -> int:
    for name in names:
        value = _int_value(usage.get(name))
        if value > 0:
            return value
    return 0


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _rate_prefix(provider_name: str) -> str:
    if provider_name in {"gemini", "google", "google-gemini"}:
        return "GEMINI"
    if provider_name in {"anthropic", "claude"}:
        return "ANTHROPIC"
    if provider_name in {"openai", "openai-compatible", "openai_compatible"}:
        return "OPENAI"
    return "LLM"


def _rate_from_env(provider_name: str, generic_name: str, default: float) -> tuple[float, str]:
    for name in (provider_name, generic_name):
        value = os.getenv(name)
        if value is None or not value.strip():
            continue
        try:
            return max(0.0, float(value)), "env"
        except ValueError:
            continue
    return default, "default"