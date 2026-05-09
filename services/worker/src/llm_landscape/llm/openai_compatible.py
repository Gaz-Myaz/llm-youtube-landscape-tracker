from __future__ import annotations

import json
from typing import Any

import requests

from llm_landscape.domain import Transcript, Video
from llm_landscape.llm.base import EnrichmentResult, Evidence, Topic
from llm_landscape.llm.mock import TOPIC_RULES

_TOPIC_LABELS = {slug: label for slug, label, _score, _keywords in TOPIC_RULES}
_CONTENT_TYPES = {
    "tutorial",
    "benchmark",
    "interview",
    "research",
    "demo",
    "analysis",
    "opinion",
    "unknown",
}
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_PROMPT_VERSION = "openai-compatible-2026-05-09"


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        provider_name: str = "openai",
    ) -> None:
        if not api_key:
            missing_key_name = (
                "GEMINI_API_KEY or GOOGLE_API_KEY"
                if provider_name == "gemini"
                else "OPENAI_API_KEY"
            )
            raise ValueError(
                f"{missing_key_name} is required when WORKER_PROVIDER={provider_name}"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.name = provider_name

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        payload = self._chat_completion_payload(video, transcript)
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        raw_response = response.json()
        content = _message_content(raw_response)
        parsed = _parse_json_object(content)
        return _result_from_payload(
            parsed,
            raw_response=raw_response,
            video=video,
            model=self.model,
            provider=self.name,
        )

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        if not shared_topic_labels:
            return f"{source_channel} and {target_channel} have limited transcript-derived overlap."
        topics = ", ".join(shared_topic_labels[:3])
        return (
            f"{source_channel} and {target_channel} overlap around {topics}; "
            f"topic-overlap score {score:.2f}."
        )

    def _chat_completion_payload(self, video: Video, transcript: Transcript) -> dict[str, Any]:
        transcript_excerpt = transcript.text[:12000]
        return {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract transcript-grounded LLM landscape metadata. "
                        "Return only valid JSON matching the requested shape. "
                        "Use only the controlled topic slugs provided. "
                        "Only tag topics when the video is primarily about LLMs, AI models, "
                        "agents, AI coding tools, RAG, AI evals, AI safety, or AI deployment. "
                        "Do not map general open-source software, video codecs, infrastructure, "
                        "or business/team language to LLM topics unless the transcript explicitly "
                        "connects them to AI/LLM systems."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "video": {
                                "id": video.youtube_video_id,
                                "title": video.title,
                                "channel": video.channel.title,
                                "published_at": video.published_at,
                            },
                            "allowed_topic_slugs": sorted(_TOPIC_LABELS),
                            "allowed_content_types": sorted(_CONTENT_TYPES),
                            "classification_rule": (
                                "If LLM/AI coverage is only incidental, return an empty topics array, "
                                "content_type unknown, and a low confidence_score."
                            ),
                            "required_json_shape": {
                                "primary_speaker": "string or null",
                                "summary": "one concise sentence grounded in transcript",
                                "content_type": "one allowed content type",
                                "stance": "string or null",
                                "topics": [
                                    {
                                        "slug": "allowed topic slug",
                                        "relevance_score": "0.0 to 1.0",
                                    }
                                ],
                                "evidence": [
                                    {
                                        "field_name": "topic or summary",
                                        "quote": "short exact transcript quote",
                                        "topic_slug": "allowed topic slug or null",
                                        "confidence_score": "0.0 to 1.0",
                                    }
                                ],
                                "confidence_score": "0.0 to 1.0",
                            },
                            "transcript_excerpt": transcript_excerpt,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        }


def _message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response did not include choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM response message content is empty")
    return content


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response content was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object")
    return parsed


def _result_from_payload(
    payload: dict[str, Any],
    raw_response: dict[str, Any],
    video: Video,
    model: str,
    provider: str,
    mode: str = "openai_compatible",
) -> EnrichmentResult:
    topics = tuple(_topic_from_payload(topic) for topic in _as_list(payload.get("topics")))
    evidence = tuple(_evidence_from_payload(item) for item in _as_list(payload.get("evidence")))
    content_type = str(payload.get("content_type") or "unknown").strip().lower()
    if content_type not in _CONTENT_TYPES:
        content_type = "unknown"
    return EnrichmentResult(
        schema_version="1.0",
        video_id=video.youtube_video_id,
        provider=provider,
        model=model,
        prompt_version=_PROMPT_VERSION,
        primary_speaker=_optional_string(payload.get("primary_speaker")),
        summary=str(payload.get("summary") or video.title).strip()[:600],
        content_type=content_type,
        stance=_optional_string(payload.get("stance")),
        topics=tuple(topic for topic in topics if topic.slug in _TOPIC_LABELS)[:4],
        evidence=tuple(item for item in evidence if item.quote)[:4],
        confidence_score=_clamp_float(payload.get("confidence_score"), default=0.5),
        raw_response={"mode": mode, "response": raw_response},
    )


def _topic_from_payload(payload: Any) -> Topic:
    data = payload if isinstance(payload, dict) else {}
    slug = str(data.get("slug") or "").strip()
    return Topic(
        slug=slug,
        label=_TOPIC_LABELS.get(slug, slug),
        relevance_score=_clamp_float(data.get("relevance_score"), default=0.5),
    )


def _evidence_from_payload(payload: Any) -> Evidence:
    data = payload if isinstance(payload, dict) else {}
    topic_slug = _optional_string(data.get("topic_slug"))
    if topic_slug not in _TOPIC_LABELS:
        topic_slug = None
    return Evidence(
        field_name=str(data.get("field_name") or "topic").strip()[:80],
        quote=str(data.get("quote") or "").strip()[:500],
        topic_slug=topic_slug,
        confidence_score=_clamp_float(data.get("confidence_score"), default=0.5),
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clamp_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, round(number, 3)))
