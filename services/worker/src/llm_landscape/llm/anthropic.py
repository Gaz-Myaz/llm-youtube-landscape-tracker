from __future__ import annotations

import json
from typing import Any

import requests

from llm_landscape.domain import Transcript, Video
from llm_landscape.llm.base import EnrichmentResult
from llm_landscape.llm.openai_compatible import (
    _SYSTEM_PROMPT,
    _parse_json_object,
    _result_from_payload,
    _user_payload,
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
            "system": _SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(_user_payload(video, transcript_excerpt), ensure_ascii=True),
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