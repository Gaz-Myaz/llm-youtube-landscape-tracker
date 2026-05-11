from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from llm_landscape.ingestion.rss import fetch_channel_rss


class _FakeResponse:
    def __init__(self, content: bytes = b"<feed />") -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_fetch_channel_rss_retries_transient_parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        SimpleNamespace(bozo=True, bozo_exception=ValueError("bad xml"), entries=[]),
        SimpleNamespace(
            bozo=False,
            entries=[
                {
                    "yt_videoid": "video-1",
                    "title": "Recovered video",
                    "link": "https://www.youtube.com/watch?v=video-1",
                    "published": "2026-05-10T00:00:00Z",
                }
            ],
        ),
    ]
    get_calls: list[str] = []

    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.requests.get",
        lambda url, headers, timeout: get_calls.append(url) or _FakeResponse(),
    )
    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.feedparser.parse",
        lambda _content: responses.pop(0),
    )
    monkeypatch.setattr("llm_landscape.ingestion.rss.time.sleep", lambda _seconds: None)

    videos = fetch_channel_rss("https://example.test/feed.xml", limit=5)

    assert [video.youtube_video_id for video in videos] == ["video-1"]
    assert len(get_calls) == 2


def test_fetch_channel_rss_accepts_bozo_feed_when_entries_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.requests.get",
        lambda url, headers, timeout: _FakeResponse(),
    )
    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.feedparser.parse",
        lambda _content: SimpleNamespace(
            bozo=True,
            bozo_exception=ValueError("minor issue"),
            entries=[
                {
                    "yt_videoid": "video-2",
                    "title": "Usable video",
                    "link": "https://www.youtube.com/watch?v=video-2",
                    "published": "2026-05-10T00:00:00Z",
                }
            ],
        ),
    )

    videos = fetch_channel_rss("https://example.test/feed.xml", limit=5)

    assert [video.youtube_video_id for video in videos] == ["video-2"]


def test_fetch_channel_rss_falls_back_to_ytdlp_channel_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []
    captured: dict[str, object] = {}

    def failing_get(url: str, headers: dict, timeout: float):
        attempts.append(url)
        raise RuntimeError("connection reset")

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
                "entries": [
                    {
                        "id": "video-3",
                        "title": "Recovered via yt-dlp",
                        "url": "https://www.youtube.com/watch?v=video-3",
                        "timestamp": 0,
                    }
                ]
            }

    monkeypatch.setattr("llm_landscape.ingestion.rss.requests.get", failing_get)
    monkeypatch.setattr("llm_landscape.ingestion.rss.time.sleep", lambda _seconds: None)
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    monkeypatch.setenv("YT_DLP_COOKIES_PATH", "/tmp/youtube-cookies.txt")

    videos = fetch_channel_rss(
        "https://www.youtube.com/feeds/videos.xml?channel_id=channel-3",
        limit=2,
    )

    assert len(attempts) == 3
    assert [video.youtube_video_id for video in videos] == ["video-3"]
    assert videos[0].title == "Recovered via yt-dlp"
    assert videos[0].published_at == "1970-01-01T00:00:00Z"
    assert captured["extract_url"] == "https://www.youtube.com/channel/channel-3/videos"
    assert captured["download"] is False
    assert captured["options"] == {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 2,
        "skip_download": True,
        "ignore_no_formats_error": True,
        "cookiefile": "/tmp/youtube-cookies.txt",
    }


def test_fetch_channel_rss_raises_after_all_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.requests.get",
        lambda url, headers, timeout: attempts.append(url) or _FakeResponse(),
    )
    monkeypatch.setattr(
        "llm_landscape.ingestion.rss.feedparser.parse",
        lambda _content: SimpleNamespace(bozo=True, bozo_exception=ValueError("bad xml"), entries=[]),
    )
    monkeypatch.setattr("llm_landscape.ingestion.rss.time.sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="Failed to parse RSS feed"):
        fetch_channel_rss("https://example.test/feed.xml", limit=5)

    assert len(attempts) == 3