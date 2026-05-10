from dataclasses import replace

from llm_landscape.exports.snapshots import build_public_snapshots
from llm_landscape.fixtures import load_mock_bundles
from llm_landscape.llm.mock import MockProvider


def test_mock_snapshots_include_public_read_models() -> None:
    provider = MockProvider()
    bundles = load_mock_bundles()
    enrichments = {
        bundle.video.youtube_video_id: provider.extract_video_insights(bundle.video, bundle.transcript)
        for bundle in bundles
    }

    snapshots = build_public_snapshots(bundles, enrichments, provider)

    assert set(snapshots) == {
        "videos.json",
        "channels.json",
        "relationships.json",
        "run-metadata.json",
    }
    assert snapshots["videos.json"]["videos"]


def test_run_metadata_includes_token_usage_cost_and_fallback_counts(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_INPUT_USD_PER_1M_TOKENS", "1.25")
    monkeypatch.setenv("GEMINI_OUTPUT_USD_PER_1M_TOKENS", "2.50")
    provider = _UsageProvider()
    fallback_provider = MockProvider()
    bundles = load_mock_bundles()[:1]
    base_enrichment = fallback_provider.extract_video_insights(bundles[0].video, bundles[0].transcript)
    enrichments = {
        bundles[0].video.youtube_video_id: replace(
            base_enrichment,
            provider="gemini",
            model="gemini-2.5-flash",
            raw_response={
                "mode": "chat_completions",
                "response": {
                    "usage": {
                        "prompt_tokens": 1_000_000,
                        "completion_tokens": 2_000_000,
                        "total_tokens": 3_000_000,
                    }
                }
            },
        )
    }

    snapshots = build_public_snapshots(
        bundles,
        enrichments,
        provider,
        run_metadata_overrides={
            "provider_call_count": 2,
            "provider_success_count": 1,
            "provider_fallback_count": 1,
            "provider_fallback_reasons": ["video-1: gemini provider failed"],
        },
    )
    metadata = snapshots["run-metadata.json"]

    assert metadata["token_usage"] == {
        "input_tokens": 1_000_000,
        "output_tokens": 2_000_000,
        "total_tokens": 3_000_000,
    }
    assert metadata["cost_rates"]["source"] == "env"
    assert metadata["estimated_cost_usd"] == 6.25
    assert metadata["provider_call_count"] == 2
    assert metadata["provider_success_count"] == 1
    assert metadata["provider_fallback_count"] == 1
    assert metadata["provider_fallback_reasons"] == ["video-1: gemini provider failed"]


class _UsageProvider:
    name = "gemini"
    model = "gemini-2.5-flash"

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        topics = ", ".join(shared_topic_labels[:3]) or "current topics"
        return f"{source_channel} and {target_channel} overlap around {topics}; score {score:.2f}."