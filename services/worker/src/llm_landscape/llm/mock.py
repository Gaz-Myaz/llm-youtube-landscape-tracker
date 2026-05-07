from __future__ import annotations

from llm_landscape.domain import Transcript, Video
from llm_landscape.llm.base import EnrichmentResult, Evidence, Topic


TOPIC_RULES: tuple[tuple[str, str, float, tuple[str, ...]], ...] = (
    ("agents", "AI Agents", 0.95, ("agent", "tool call", "planner", "autonomous")),
    (
        "coding-assistants",
        "Coding Assistants",
        0.92,
        ("coding", "repository", "pull request", "editor", "developer"),
    ),
    (
        "open-source-models",
        "Open Source Models",
        0.91,
        ("open-weight", "open model", "open models", "open-source model"),
    ),
    ("local-inference", "Local Inference", 0.89, ("local", "privacy", "laptop", "offline")),
    (
        "rag",
        "RAG",
        0.88,
        ("rag", "retrieval", "grounded", "vector", "knowledge base"),
    ),
    (
        "multimodal",
        "Multimodal",
        0.87,
        ("multimodal", "vision", "image", "images", "audio", "video clips"),
    ),
    (
        "fine-tuning",
        "Fine Tuning",
        0.85,
        ("fine-tuning", "fine tuning", "lora", "adapter", "adapters", "sft"),
    ),
    (
        "safety-alignment",
        "Safety and Alignment",
        0.84,
        ("safety", "alignment", "aligned", "policy", "risk", "red team"),
    ),
    (
        "enterprise-adoption",
        "Enterprise Adoption",
        0.82,
        ("enterprise", "company", "companies", "team", "teams", "production", "deploy", "deployment", "rollout"),
    ),
    (
        "evals",
        "Evaluation",
        0.78,
        ("evaluation", "eval", "test suite", "scorecard", "scorecards", "regression"),
    ),
    ("benchmarks", "Benchmarks", 0.77, ("benchmark", "leaderboard")),
    (
        "model-releases",
        "Model Releases",
        0.74,
        ("release", "announced", "launch", "new model"),
    ),
)


class MockProvider:
    name = "mock"
    model = "mock-landscape-v1"
    prompt_version = "mock-2026-05-07"

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        text = transcript.text.lower()
        topics = [
            Topic(slug, label, relevance_score)
            for slug, label, relevance_score, keywords in TOPIC_RULES
            if any(keyword in text for keyword in keywords)
        ]
        if not topics:
            topics.append(Topic("model-releases", "Model Releases", 0.5))
        topics.sort(key=lambda topic: topic.relevance_score, reverse=True)

        first_segment = transcript.segments[0] if transcript.segments else None
        evidence = Evidence(
            field_name="topic",
            topic_slug=topics[0].slug,
            quote=first_segment.text if first_segment else transcript.text[:240],
            start_seconds=first_segment.start_seconds if first_segment else None,
            end_seconds=first_segment.end_seconds if first_segment else None,
            confidence_score=0.86,
        )

        if any(keyword in text for keyword in ("tutorial", "workshop", "from scratch", "walkthrough")):
            content_type = "tutorial"
        elif video.channel.title == "Lex Fridman" or "interview" in text:
            content_type = "interview"
        elif any(topic.slug in {"benchmarks", "model-releases", "multimodal"} for topic in topics):
            content_type = "benchmark"
        else:
            content_type = "analysis"
        summary = self._summary(video, topics)
        return EnrichmentResult(
            schema_version="1.0",
            video_id=video.youtube_video_id,
            provider=self.name,
            model=self.model,
            prompt_version=self.prompt_version,
            primary_speaker=f"{video.channel.title} host",
            summary=summary,
            content_type=content_type,
            stance="practical and evidence-oriented",
            topics=tuple(topics[:4]),
            evidence=(evidence,),
            confidence_score=0.84,
            raw_response={"mode": "deterministic_mock"},
        )

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        if not shared_topic_labels:
            return f"{source_channel} and {target_channel} have limited overlap in the current sample."
        topics = ", ".join(shared_topic_labels[:3])
        return (
            f"{source_channel} and {target_channel} are related through shared coverage of "
            f"{topics}. The current topic-overlap score is {score:.2f}."
        )

    @staticmethod
    def _summary(video: Video, topics: list[Topic]) -> str:
        labels = ", ".join(topic.label for topic in topics[:3]) or "LLM systems"
        return f"The video discusses {labels} and connects the theme to practical LLM system decisions."
