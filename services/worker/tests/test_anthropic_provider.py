from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_landscape.config import load_settings
from llm_landscape.domain import Channel, Transcript, TranscriptSegment, Video
from llm_landscape.llm.anthropic import AnthropicProvider
from llm_landscape.llm.factory import create_provider


def test_anthropic_provider_extracts_structured_insights(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """
                        {
                          "primary_speaker": "host",
                          "summary": "The video explains a coding assistant workflow.",
                          "content_type": "tutorial",
                          "stance": "positive",
                          "topics": [
                            {"slug": "coding-assistants", "relevance_score": 0.93}
                          ],
                          "evidence": [
                            {
                              "field_name": "topic",
                              "quote": "edit repositories safely",
                              "topic_slug": "coding-assistants",
                              "confidence_score": 0.9
                            }
                          ],
                          "confidence_score": 0.87
                        }
                        """,
                    }
                ]
            }

    def fake_post(url: str, headers: dict, json: dict, timeout: float) -> FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("llm_landscape.llm.anthropic.requests.post", fake_post)
    provider = AnthropicProvider(
        api_key="test-key",
        base_url="https://example.test/v1/",
        model="claude-test-model",
    )

    result = provider.extract_video_insights(_video(), _transcript())

    assert captured["url"] == "https://example.test/v1/messages"
    assert captured["headers"] == {
        "x-api-key": "test-key",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    assert captured["json"]["model"] == "claude-test-model"
    assert captured["json"]["max_tokens"] == 1200
    assert result.provider == "anthropic"
    assert result.model == "claude-test-model"
    assert result.content_type == "tutorial"
    assert [topic.slug for topic in result.topics] == ["coding-assistants"]
    assert result.evidence[0].quote == "edit repositories safely"
    assert result.raw_response["mode"] == "anthropic_messages"


def test_anthropic_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(api_key=None, model="claude-test-model")


def test_factory_creates_anthropic_provider(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_PROVIDER", " claude ")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")

    provider = create_provider(load_settings())

    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-test-model"


def test_anthropic_provider_rejects_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.anthropic.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"content": [{"type": "text", "text": "not json"}]},
        ),
    )
    provider = AnthropicProvider(api_key="test-key", model="claude-test-model")

    with pytest.raises(ValueError, match="valid JSON"):
        provider.extract_video_insights(_video(), _transcript())


def _video() -> Video:
    channel = Channel(
        youtube_channel_id="channel-1",
        title="AI Channel",
        handle="@ai",
        description=None,
        url="https://www.youtube.com/@ai",
    )
    return Video(
        youtube_video_id="video-1",
        title="Coding assistant workflow",
        url="https://www.youtube.com/watch?v=video-1",
        published_at="2026-05-09T00:00:00Z",
        channel=channel,
    )


def _transcript() -> Transcript:
    return Transcript(
        video_id="video-1",
        source="youtube_captions",
        language="en",
        text="Today this coding assistant can call tools and edit repositories safely.",
        segments=(
            TranscriptSegment(
                0,
                0,
                5,
                "Today this coding assistant can call tools and edit repositories safely.",
            ),
        ),
    )