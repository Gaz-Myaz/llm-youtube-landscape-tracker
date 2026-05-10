from __future__ import annotations

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