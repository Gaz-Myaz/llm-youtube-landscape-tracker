from __future__ import annotations

from llm_landscape.config import Settings
from llm_landscape.llm.base import LlmProvider
from llm_landscape.llm.anthropic import AnthropicProvider
from llm_landscape.llm.mock import MockProvider
from llm_landscape.llm.openai_compatible import OpenAICompatibleProvider
from llm_landscape.llm.vertex import VertexProvider


def create_provider(settings: Settings) -> LlmProvider:
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            provider_name="openai",
        )
    if settings.provider in {"gemini", "google", "google-gemini"}:
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            provider_name="gemini",
        )
    if settings.provider in {"anthropic", "claude"}:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
        )
    if settings.provider == "vertex":
        return VertexProvider(
            project_id=settings.vertex_project_id,
            location=settings.vertex_location,
            model=settings.vertex_model,
        )
    raise ValueError(f"Unsupported WORKER_PROVIDER={settings.provider!r}")
