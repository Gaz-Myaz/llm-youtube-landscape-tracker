from __future__ import annotations

from types import SimpleNamespace
import json

import pytest

from llm_landscape.config import load_settings
from llm_landscape.domain import Channel, Transcript, TranscriptSegment, Video
from llm_landscape.llm.factory import create_provider
from llm_landscape.llm.chat_completions import ChatCompletionsProvider


def test_chat_completions_provider_extracts_structured_insights(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "primary_speaker": "host",
                              "summary": "The video explains a new coding agent release.",
                              "content_type": "demo",
                              "stance": "positive",
                              "topics": [
                                {"slug": "agents", "relevance_score": 0.91},
                                {"slug": "coding-assistants", "relevance_score": 0.84}
                              ],
                              "evidence": [
                                {
                                  "field_name": "topic",
                                  "quote": "this coding agent can call tools",
                                  "topic_slug": "agents",
                                  "confidence_score": 0.88
                                }
                              ],
                              "confidence_score": 0.86
                            }
                            """
                        }
                    }
                ]
            }

    def fake_post(url: str, headers: dict, json: dict, timeout: float) -> FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("llm_landscape.llm.chat_completions.requests.post", fake_post)
    provider = ChatCompletionsProvider(
        api_key="test-key",
        base_url="https://example.test/v1/",
        model="test-model",
    )

    result = provider.extract_video_insights(_video(), _transcript())

    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"] == {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json",
    }
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["response_format"]["type"] == "json_schema"
    assert captured["json"]["response_format"]["json_schema"]["strict"] is True
    assert "required_json_schema" in json.loads(captured["json"]["messages"][1]["content"])
    assert result.provider == "openai"
    assert result.model == "test-model"
    assert result.primary_speaker == "host"
    assert result.content_type == "demo"
    assert [topic.slug for topic in result.topics] == ["agents", "coding-assistants"]
    assert result.evidence[0].quote == "this coding agent can call tools"
    assert result.confidence_score == 0.86


def test_chat_completions_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        ChatCompletionsProvider(api_key=None, model="test-model")


def test_factory_creates_chat_completions_provider_from_alias(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_PROVIDER", " OpenAI-Compatible ")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    provider = create_provider(load_settings())

    assert isinstance(provider, ChatCompletionsProvider)
    assert provider.model == "test-model"


def test_factory_creates_gemini_provider_from_google_api_key(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_PROVIDER", " gemini ")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    provider = create_provider(load_settings())

    assert isinstance(provider, ChatCompletionsProvider)
    assert provider.name == "gemini"
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.model == "gemini-2.5-flash"


def test_gemini_provider_prefers_gemini_key_over_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_PROVIDER", "gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai-test-model")

    provider = create_provider(load_settings())

    assert isinstance(provider, ChatCompletionsProvider)
    assert provider.name == "gemini"
    assert provider.api_key == "gemini-key"
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.model == "gemini-2.5-flash"


def test_gemini_provider_keeps_json_object_response_format(monkeypatch) -> None:
        captured: dict[str, object] = {}

        def fake_post(url: str, headers: dict, json: dict, timeout: float) -> SimpleNamespace:
                captured["json"] = json
                return SimpleNamespace(
                        raise_for_status=lambda: None,
                        json=lambda: {
                                "choices": [
                                        {
                                                "message": {
                                                        "content": """
                                                        {
                                                            "primary_speaker": null,
                                                            "summary": "The video explains a model release.",
                                                            "content_type": "analysis",
                                                            "stance": null,
                                                            "topics": [
                                                                {"slug": "model-releases", "relevance_score": 0.8}
                                                            ],
                                                            "evidence": [
                                                                {
                                                                    "field_name": "topic",
                                                                    "quote": "new coding agent release",
                                                                    "topic_slug": "model-releases",
                                                                    "confidence_score": 0.8
                                                                }
                                                            ],
                                                            "confidence_score": 0.8
                                                        }
                                                        """
                                                }
                                        }
                                ]
                        },
                )

        monkeypatch.setattr("llm_landscape.llm.chat_completions.requests.post", fake_post)
        provider = ChatCompletionsProvider(
                api_key="test-key",
                base_url="https://example.test/v1/",
                model="gemini-test-model",
                provider_name="gemini",
        )

        provider.extract_video_insights(_video(), _transcript())

        assert captured["json"]["response_format"] == {"type": "json_object"}


def test_chat_completions_provider_rejects_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.chat_completions.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"choices": [{"message": {"content": "not json"}}]},
        ),
    )
    provider = ChatCompletionsProvider(api_key="test-key", model="test-model")

    with pytest.raises(ValueError, match="valid JSON"):
        provider.extract_video_insights(_video(), _transcript())


def test_chat_completions_provider_rejects_schema_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.chat_completions.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "summary": "Missing required fields"
                            }
                            """
                        }
                    }
                ]
            },
        ),
    )
    provider = ChatCompletionsProvider(api_key="test-key", model="test-model")

    with pytest.raises(ValueError, match="insight schema"):
        provider.extract_video_insights(_video(), _transcript())


def test_chat_completions_provider_accepts_evidence_without_optional_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.chat_completions.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "primary_speaker": "host",
                              "summary": "The video explains a model release.",
                              "content_type": "analysis",
                              "stance": "mixed",
                              "topics": [
                                {"slug": "model-releases", "relevance_score": 0.88}
                              ],
                              "evidence": [
                                {
                                  "field_name": "primary_speaker",
                                  "quote": "Dear fellow scholars"
                                },
                                {
                                  "field_name": "summary",
                                  "quote": "OpenAI released a new instant model"
                                }
                              ],
                              "confidence_score": 0.83
                            }
                            """
                        }
                    }
                ]
            },
        ),
    )
    provider = ChatCompletionsProvider(api_key="test-key", model="test-model", provider_name="gemini")

    result = provider.extract_video_insights(_video(), _transcript())

    assert len(result.evidence) == 2
    assert result.evidence[0].topic_slug is None
    assert result.evidence[0].confidence_score == 0.5


def test_chat_completions_provider_trims_arrays_before_schema_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.chat_completions.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "primary_speaker": "host",
                              "summary": "The video compares several model release topics.",
                              "content_type": "analysis",
                              "stance": "mixed",
                              "topics": [
                                {"slug": "model-releases", "relevance_score": 0.91},
                                {"slug": "benchmarks", "relevance_score": 0.82},
                                {"slug": "evals", "relevance_score": 0.78},
                                {"slug": "safety-alignment", "relevance_score": 0.72},
                                {"slug": "agents", "relevance_score": 0.61}
                              ],
                              "evidence": [
                                {"field_name": "summary", "quote": "quote one", "topic_slug": null, "confidence_score": 0.9},
                                {"field_name": "summary", "quote": "quote two", "topic_slug": null, "confidence_score": 0.8},
                                {"field_name": "summary", "quote": "quote three", "topic_slug": null, "confidence_score": 0.7},
                                {"field_name": "summary", "quote": "quote four", "topic_slug": null, "confidence_score": 0.6},
                                {"field_name": "summary", "quote": "quote five", "topic_slug": null, "confidence_score": 0.5}
                              ],
                              "confidence_score": 0.84
                            }
                            """
                        }
                    }
                ]
            },
        ),
    )
    provider = ChatCompletionsProvider(api_key="test-key", model="test-model", provider_name="gemini")

    result = provider.extract_video_insights(_video(), _transcript())

    assert [topic.slug for topic in result.topics] == [
        "model-releases",
        "benchmarks",
        "evals",
        "safety-alignment",
    ]
    assert [item.quote for item in result.evidence] == [
        "quote one",
        "quote two",
        "quote three",
        "quote four",
    ]


def test_chat_completions_provider_normalizes_topic_aliases_and_drops_unknown_topics(monkeypatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.llm.chat_completions.requests.post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "primary_speaker": "host",
                              "summary": "The video covers agent systems and model evaluation.",
                              "content_type": "analysis",
                              "stance": "mixed",
                              "topics": [
                                {"slug": "AI Agents", "relevance_score": 0.91},
                                {"slug": "research", "relevance_score": 0.77},
                                {"slug": "evaluation", "relevance_score": 0.74}
                              ],
                              "evidence": [
                                {"field_name": "topic", "quote": "the agent can plan", "topic_slug": "AI Agents", "confidence_score": 0.84},
                                {"field_name": "topic", "quote": "the paper benchmarks the system", "topic_slug": "research", "confidence_score": 0.72}
                              ],
                              "confidence_score": 0.81
                            }
                            """
                        }
                    }
                ]
            },
        ),
    )
    provider = ChatCompletionsProvider(api_key="test-key", model="test-model", provider_name="gemini")

    result = provider.extract_video_insights(_video(), _transcript())

    assert [topic.slug for topic in result.topics] == ["agents", "evals"]
    assert [item.topic_slug for item in result.evidence] == ["agents", None]


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
        title="New coding agent release",
        url="https://www.youtube.com/watch?v=video-1",
        published_at="2026-05-09T00:00:00Z",
        channel=channel,
    )


def _transcript() -> Transcript:
    return Transcript(
        video_id="video-1",
        source="youtube_captions",
        language="en",
        text="Today this coding agent can call tools and edit repositories safely.",
        segments=(
            TranscriptSegment(
                0,
                0,
                5,
                "Today this coding agent can call tools and edit repositories safely.",
            ),
        ),
    )
