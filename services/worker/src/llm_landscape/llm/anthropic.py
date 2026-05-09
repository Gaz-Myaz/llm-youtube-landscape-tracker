from __future__ import annotations

import json
from typing import Any

import requests

from llm_landscape.domain import Transcript, Video
from llm_landscape.llm.base import EnrichmentResult
from llm_landscape.llm.openai_compatible import (
    _CONTENT_TYPES,
    _TOPIC_LABELS,
    _parse_json_object,
    _result_from_payload,
)

_DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when WORKER_PROVIDER=anthropic")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        response = requests.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json=self._messages_payload(video, transcript),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        raw_response = response.json()
        parsed = _parse_json_object(_message_content(raw_response))
        return _result_from_payload(
            parsed,
            raw_response=raw_response,
            video=video,
            model=self.model,
            provider=self.name,
            mode="anthropic_messages",
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

    def _messages_payload(self, video: Video, transcript: Transcript) -> dict[str, Any]:
        transcript_excerpt = transcript.text[:12000]
        return {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": 0.1,
            "system": (
                "You extract transcript-grounded LLM landscape metadata. "
                "Return only valid JSON matching the requested shape. "
                "Use only the controlled topic slugs provided. "
                "Only tag topics when the video is primarily about LLMs, AI models, "
                "agents, AI coding tools, RAG, AI evals, AI safety, or AI deployment. "
                "Do not map general open-source software, video codecs, infrastructure, "
                "or business/team language to LLM topics unless the transcript explicitly "
                "connects them to AI/LLM systems."
            ),
            "messages": [
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
                }
            ],
        }


def _message_content(response: dict[str, Any]) -> str:
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("Anthropic response did not include content")
    text_parts = [item.get("text") for item in content if isinstance(item, dict)]
    text = "".join(part for part in text_parts if isinstance(part, str)).strip()
    if not text:
        raise ValueError("Anthropic response content is empty")
    return text