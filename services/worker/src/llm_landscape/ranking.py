from __future__ import annotations

from datetime import datetime

from llm_landscape.domain import VideoBundle
from llm_landscape.llm.base import EnrichmentResult


def fallback_video_score(enrichment: EnrichmentResult) -> float:
    topic_scores = sorted((topic.relevance_score for topic in enrichment.topics), reverse=True)
    if not topic_scores:
        return 0.0

    strongest_topic = topic_scores[0]
    average_topic = sum(topic_scores[:3]) / min(3, len(topic_scores))
    topic_diversity = min(1.0, len(topic_scores) / 4)
    evidence_coverage = min(1.0, len(enrichment.evidence) / 3)

    return round(
        strongest_topic * 0.55
        + average_topic * 0.25
        + topic_diversity * 0.10
        + evidence_coverage * 0.10,
        3,
    )


def sort_video_bundles(
    bundles: list[VideoBundle], enrichments: dict[str, EnrichmentResult]
) -> list[VideoBundle]:
    return sorted(
        bundles,
        key=lambda bundle: (
            fallback_video_score(enrichments[bundle.video.youtube_video_id]),
            _published_timestamp(bundle.video.published_at),
            bundle.video.youtube_video_id,
        ),
        reverse=True,
    )


def _published_timestamp(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0