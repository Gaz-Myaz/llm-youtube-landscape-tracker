from __future__ import annotations

from llm_landscape.config import Settings
from llm_landscape.llm.base import LlmProvider
from llm_landscape.llm.mock import MockProvider
from llm_landscape.llm.vertex import VertexProvider


def create_provider(settings: Settings) -> LlmProvider:
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "vertex":
        return VertexProvider(
            project_id=settings.vertex_project_id,
            location=settings.vertex_location,
            model=settings.vertex_model,
        )
    raise ValueError(f"Unsupported WORKER_PROVIDER={settings.provider!r}")
