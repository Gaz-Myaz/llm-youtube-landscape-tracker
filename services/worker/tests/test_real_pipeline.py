import sys
from pathlib import Path
from types import SimpleNamespace

from llm_landscape.analysis import DeterministicAnalyzer, is_landscape_relevant
from llm_landscape.channels import load_seed_channels
from llm_landscape.config import load_settings
from llm_landscape.domain import Channel, Transcript, TranscriptSegment, Video, VideoBundle
from llm_landscape.llm.base import EnrichmentResult, Evidence, Topic
from llm_landscape.main import _as_iso_datetime, collect_real_bundles
from llm_landscape.ranking import fallback_video_score, sort_video_bundles
from llm_landscape.transcripts.captions import _fetch_ytdlp_transcript_items, fetch_youtube_captions


def test_seed_channels_load_from_sql() -> None:
    root = Path(__file__).resolve().parents[3]
    channels = load_seed_channels(root / "infra" / "db" / "seed_channels.sql")

    assert len(channels) >= 5
    assert all(channel.rss_url for channel in channels)
    assert any(channel.handle == "@Droiderru" and channel.language == "ru" for channel in channels)


def test_deterministic_analyzer_extracts_subtitle_topics() -> None:
    channel = Channel(
        youtube_channel_id="channel-1",
        title="Example Channel",
        handle="@example",
        description=None,
        url="https://www.youtube.com/@example",
    )
    video = Video(
        youtube_video_id="video-1",
        title="Build a local coding agent",
        url="https://www.youtube.com/watch?v=video-1",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
    )
    transcript = Transcript(
        video_id="video-1",
        source="youtube_captions",
        language="en",
        text=(
            "In this tutorial we build a coding agent that reads a repository. "
            "The local inference setup protects privacy and keeps data offline."
        ),
        segments=(
            TranscriptSegment(
                0,
                0,
                12,
                "In this tutorial we build a coding agent that reads a repository.",
            ),
            TranscriptSegment(
                1,
                13,
                26,
                "The local inference setup protects privacy and keeps data offline.",
            ),
        ),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert result.provider == "deterministic"
    assert result.content_type == "tutorial"
    assert {topic.slug for topic in result.topics} >= {
        "agents",
        "coding-assistants",
        "local-inference",
    }
    assert result.evidence
    assert is_landscape_relevant(video, result)


def test_deterministic_analyzer_avoids_substring_topic_matches() -> None:
    channel = Channel(
        youtube_channel_id="channel-1",
        title="Example Channel",
        handle="@example",
        description=None,
        url="https://www.youtube.com/@example",
    )
    video = Video(
        youtube_video_id="video-2",
        title="A history of dragons and local economies",
        url="https://www.youtube.com/watch?v=video-2",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
    )
    transcript = Transcript(
        video_id="video-2",
        source="youtube_captions",
        language="en",
        text="The dragon story discusses local economies and average village income.",
        segments=(
            TranscriptSegment(
                0,
                0,
                8,
                "The dragon story discusses local economies and average village income.",
            ),
        ),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert result.topics == ()
    assert not is_landscape_relevant(video, result)


def test_landscape_relevance_accepts_single_model_release_topic() -> None:
    channel = Channel(
        youtube_channel_id="channel-2",
        title="Example Channel",
        handle="@example",
        description=None,
        url="https://www.youtube.com/@example",
    )
    video = Video(
        youtube_video_id="video-3",
        title="Weekly developer news",
        url="https://www.youtube.com/watch?v=video-3",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
    )
    transcript = Transcript(
        video_id="video-3",
        source="youtube_captions",
        language="en",
        text="The main segment covers a model release and why developers should care.",
        segments=(
            TranscriptSegment(
                0,
                0,
                8,
                "The main segment covers a model release and why developers should care.",
            ),
        ),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert [topic.slug for topic in result.topics] == ["model-releases"]
    assert is_landscape_relevant(video, result)


def test_deterministic_analyzer_uses_video_metadata_for_topics() -> None:
    channel = Channel(
        youtube_channel_id="channel-2",
        title="AI Channel",
        handle="@ai",
        description=None,
        url="https://www.youtube.com/@ai",
    )
    video = Video(
        youtube_video_id="video-3",
        title="OpenAI launches GPT coding agent for Cursor and Copilot workflows",
        url="https://www.youtube.com/watch?v=video-3",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
        description="Coverage of a new model release and coding assistant tooling.",
    )
    transcript = Transcript(
        video_id="video-3",
        source="youtube_captions",
        language="en",
        text="Today we walk through what shipped and why it matters.",
        segments=(
            TranscriptSegment(
                0,
                0,
                8,
                "Today we walk through what shipped and why it matters.",
            ),
        ),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert {topic.slug for topic in result.topics} >= {"model-releases", "coding-assistants", "agents"}
    assert is_landscape_relevant(video, result)


def test_deterministic_analyzer_falls_back_to_title_signals() -> None:
    channel = Channel(
        youtube_channel_id="channel-3",
        title="Research Channel",
        handle="@research",
        description=None,
        url="https://www.youtube.com/@research",
    )
    video = Video(
        youtube_video_id="video-4",
        title="Sakana AI's God Simulator Is Brilliant",
        url="https://www.youtube.com/watch?v=video-4",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
        description="A look at a new AI system.",
    )
    transcript = Transcript(
        video_id="video-4",
        source="youtube_captions",
        language="en",
        text="Let's look at how this system behaves in practice.",
        segments=(
            TranscriptSegment(
                0,
                0,
                8,
                "Let's look at how this system behaves in practice.",
            ),
        ),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert {topic.slug for topic in result.topics} >= {"model-releases"}
    assert is_landscape_relevant(video, result)


def test_deterministic_analyzer_falls_back_to_analysis_content_type() -> None:
    channel = Channel(
        youtube_channel_id="channel-5",
        title="AI Channel",
        handle="@ai",
        description=None,
        url="https://www.youtube.com/@ai",
    )
    video = Video(
        youtube_video_id="video-5",
        title="NVIDIA's New AI Shouldn't Work But It Does",
        url="https://www.youtube.com/watch?v=video-5",
        published_at="2026-05-07T00:00:00Z",
        channel=channel,
        description=None,
    )
    transcript = Transcript(
        video_id="video-5",
        source="youtube_captions",
        language="en",
        text="This system behaves differently than expected.",
        segments=(TranscriptSegment(0, 0, 5, "This system behaves differently than expected."),),
    )

    result = DeterministicAnalyzer().extract_video_insights(video, transcript)

    assert result.content_type == "analysis"


def test_iso_datetime_normalization() -> None:
    assert _as_iso_datetime("2026-05-07T12:34:56+00:00") == "2026-05-07T12:34:56Z"


def test_fallback_video_ranking_prefers_deterministic_relevance() -> None:
    channel = Channel(
        youtube_channel_id="channel-4",
        title="Fallback Channel",
        handle="@fallback",
        description=None,
        url="https://www.youtube.com/@fallback",
    )
    older_high_signal = Video(
        youtube_video_id="older-high-signal",
        title="Older high signal",
        url="https://www.youtube.com/watch?v=older-high-signal",
        published_at="2026-05-01T00:00:00Z",
        channel=channel,
    )
    newer_low_signal = Video(
        youtube_video_id="newer-low-signal",
        title="Newer low signal",
        url="https://www.youtube.com/watch?v=newer-low-signal",
        published_at="2026-05-08T00:00:00Z",
        channel=channel,
    )
    bundles = [
        _bundle(older_high_signal),
        _bundle(newer_low_signal),
    ]
    enrichments = {
        older_high_signal.youtube_video_id: _enrichment(
            older_high_signal.youtube_video_id,
            topics=(
                Topic("agents", "AI Agents", 0.91),
                Topic("coding-assistants", "Coding Assistants", 0.83),
            ),
            evidence=(Evidence("topic", "agent evidence"), Evidence("topic", "coding evidence")),
        ),
        newer_low_signal.youtube_video_id: _enrichment(
            newer_low_signal.youtube_video_id,
            topics=(Topic("model-releases", "Model Releases", 0.61),),
            evidence=(Evidence("topic", "model evidence"),),
        ),
    }

    ranked = sort_video_bundles(bundles, enrichments)

    assert fallback_video_score(enrichments[older_high_signal.youtube_video_id]) > fallback_video_score(
        enrichments[newer_low_signal.youtube_video_id]
    )
    assert ranked[0].video.youtube_video_id == older_high_signal.youtube_video_id


def test_caption_fetch_uses_cache(tmp_path, monkeypatch) -> None:
    calls = []

    def fake_fetch(video_id: str, languages: list[str]) -> list[dict]:
        calls.append((video_id, languages))
        return [{"text": "cached caption", "start": 1, "duration": 2}]

    monkeypatch.setattr("llm_landscape.transcripts.captions._fetch_transcript_items", fake_fetch)

    first = fetch_youtube_captions("video-3", ["en"], cache_dir=tmp_path)
    second = fetch_youtube_captions("video-3", ["en"], cache_dir=tmp_path)

    assert first.text == "cached caption"
    assert second.text == "cached caption"
    assert calls == [("video-3", ["en"])]


def test_caption_fetch_falls_back_to_ytdlp(tmp_path, monkeypatch) -> None:
    calls = []

    def unavailable(video_id: str, languages: list[str]) -> list[dict]:
        calls.append(("youtube", video_id, languages))
        raise RuntimeError("blocked")

    def ytdlp(video_id: str, languages: list[str]) -> list[dict]:
        calls.append(("yt_dlp", video_id, languages))
        return [{"text": "fallback caption", "start": 3, "duration": 4}]

    monkeypatch.setattr("llm_landscape.transcripts.captions._fetch_transcript_items", unavailable)
    monkeypatch.setattr("llm_landscape.transcripts.captions._fetch_ytdlp_transcript_items", ytdlp)

    transcript = fetch_youtube_captions(
        "video-4",
        ["en"],
        cache_dir=tmp_path,
        providers=["youtube_transcript_api", "yt_dlp"],
    )

    assert transcript.text == "fallback caption"
    assert transcript.source == "youtube_captions:yt_dlp"
    assert calls == [("youtube", "video-4", ["en"]), ("yt_dlp", "video-4", ["en"])]


def test_caption_fetch_respects_provider_order(monkeypatch) -> None:
    calls = []

    def youtube(video_id: str, languages: list[str]) -> list[dict]:
        calls.append(("youtube", video_id, languages))
        return [{"text": "primary caption", "start": 1, "duration": 2}]

    monkeypatch.setattr("llm_landscape.transcripts.captions._fetch_transcript_items", youtube)

    transcript = fetch_youtube_captions(
        "video-5",
        ["en"],
        providers=["youtube_transcript_api", "yt_dlp"],
    )

    assert transcript.text == "primary caption"
    assert transcript.source == "youtube_captions:youtube_transcript_api"
    assert calls == [("youtube", "video-5", ["en"])]


def test_collect_real_bundles_uses_channel_language_when_not_overridden(monkeypatch) -> None:
    channel = Channel(
        youtube_channel_id="channel-ru",
        title="Russian AI Channel",
        handle="@ru-ai",
        description=None,
        url="https://www.youtube.com/@ru-ai",
        rss_url="https://www.youtube.com/feeds/videos.xml?channel_id=channel-ru",
        language="ru",
    )
    calls = []

    monkeypatch.setattr(
        "llm_landscape.main.fetch_channel_rss",
        lambda rss_url, limit: [
            SimpleNamespace(
                youtube_video_id="video-ru",
                title="Russian AI news",
                url="https://www.youtube.com/watch?v=video-ru",
                published_at="2026-05-09T00:00:00Z",
            )
        ],
    )

    def fake_fetch_captions(video_id, languages, cache_dir=None, providers=None):
        calls.append(languages)
        return Transcript(
            video_id=video_id,
            source="test",
            language=languages[0],
            text="russian transcript",
            segments=(TranscriptSegment(0, 0, 1, "russian transcript"),),
        )

    monkeypatch.setattr("llm_landscape.main.fetch_youtube_captions", fake_fetch_captions)

    bundles, skipped = collect_real_bundles(
        channels=[channel],
        videos_per_channel=1,
        max_videos=1,
        languages=None,
    )

    assert not skipped
    assert bundles[0].transcript.language == "ru"
    assert calls == [["ru", "en"]]


def test_load_settings_reads_optional_ytdlp_cookie_config(monkeypatch) -> None:
    monkeypatch.setenv("YT_DLP_COOKIES_PATH", ".github/yt-dlp-cookies.txt")
    monkeypatch.setenv("YT_DLP_COOKIES_FROM_BROWSER", "chrome:Default")
    monkeypatch.setenv("WORKER_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://example.test/v1beta/openai")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")

    settings = load_settings()

    assert settings.provider == "gemini"
    assert settings.openai_api_key == "test-key"
    assert settings.openai_base_url == "https://example.test/v1beta/openai"
    assert settings.openai_model == "gemini-test-model"
    assert settings.yt_dlp_cookies_path is not None
    assert settings.yt_dlp_cookies_path.as_posix().endswith(".github/yt-dlp-cookies.txt")
    assert settings.yt_dlp_cookies_from_browser == "chrome:Default"


def test_ytdlp_caption_fetch_reuses_ytdlp_cookie_session(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def read(self) -> bytes:
            return (
                "WEBVTT\n\n"
                "00:00:00.000 --> 00:00:01.000\n"
                "cookie-backed subtitle\n"
            ).encode("utf-8")

        def close(self) -> None:
            return None

    class FakeYoutubeDL:
        def __init__(self, options: dict) -> None:
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def extract_info(self, url: str, download: bool = False) -> dict:
            captured["extract_url"] = url
            captured["download"] = download
            return {
                "subtitles": {
                    "en": [
                        {
                            "url": "https://example.com/subtitles.vtt",
                            "ext": "vtt",
                        }
                    ]
                }
            }

        def urlopen(self, url: str) -> FakeResponse:
            captured["caption_url"] = url
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    monkeypatch.setenv("YT_DLP_COOKIES_PATH", "/tmp/youtube-cookies.txt")

    items = _fetch_ytdlp_transcript_items("video-6", ["en"])

    assert items[0]["text"] == "cookie-backed subtitle"
    assert captured["caption_url"] == "https://example.com/subtitles.vtt"
    assert captured["options"] == {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignore_no_formats_error": True,
        "cookiefile": "/tmp/youtube-cookies.txt",
    }


def _bundle(video: Video) -> VideoBundle:
    transcript = Transcript(
        video_id=video.youtube_video_id,
        source="test",
        language="en",
        text="test transcript",
        segments=(TranscriptSegment(0, 0, 1, "test transcript"),),
    )
    return VideoBundle(video=video, transcript=transcript)


def _enrichment(
    video_id: str, topics: tuple[Topic, ...], evidence: tuple[Evidence, ...]
) -> EnrichmentResult:
    return EnrichmentResult(
        schema_version="1.0",
        video_id=video_id,
        provider="deterministic",
        model="keyword-transcript-v1",
        prompt_version="test",
        primary_speaker=None,
        summary="summary",
        content_type="unknown",
        stance=None,
        topics=topics,
        evidence=evidence,
        confidence_score=0.8,
        raw_response=None,
    )
