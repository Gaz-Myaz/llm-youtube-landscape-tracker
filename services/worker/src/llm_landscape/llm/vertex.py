from __future__ import annotations

from llm_landscape.domain import Transcript, Video
from llm_landscape.llm.base import EnrichmentResult


class VertexProvider:
    name = "vertex"

    def __init__(self, project_id: str | None, location: str, model: str) -> None:
        self.project_id = project_id
        self.location = location
        self.model = model

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        raise NotImplementedError(
            "Vertex provider contract is scaffolded. Wire Google Vertex AI SDK calls here after "
            "mock export and schema validation are stable."
        )

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        topics = ", ".join(shared_topic_labels[:3]) or "the current topic profile"
        return (
            f"{source_channel} and {target_channel} are connected through {topics}; "
            f"topic-overlap score {score:.2f}."
        )
