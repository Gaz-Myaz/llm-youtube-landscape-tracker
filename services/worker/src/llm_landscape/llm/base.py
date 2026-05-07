from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llm_landscape.domain import Transcript, Video


@dataclass(frozen=True)
class Topic:
    slug: str
    label: str
    relevance_score: float


@dataclass(frozen=True)
class Evidence:
    field_name: str
    quote: str
    topic_slug: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    confidence_score: float | None = None


@dataclass(frozen=True)
class EnrichmentResult:
    schema_version: str
    video_id: str
    provider: str
    model: str
    prompt_version: str
    primary_speaker: str | None
    summary: str
    content_type: str
    stance: str | None
    topics: tuple[Topic, ...]
    evidence: tuple[Evidence, ...]
    confidence_score: float
    raw_response: dict | None


class LlmProvider(Protocol):
    name: str
    model: str

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        """Return structured, transcript-grounded video insight data."""

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        """Return a short grounded explanation for a channel relationship edge."""
