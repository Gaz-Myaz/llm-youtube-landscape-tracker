from __future__ import annotations

import time
from dataclasses import dataclass

import feedparser
import requests


_RSS_FETCH_ATTEMPTS = 3
_RSS_RETRY_DELAY_SECONDS = 1.0
_RSS_TIMEOUT_SECONDS = 30.0
_RSS_REQUEST_HEADERS = {
    "User-Agent": "llm-youtube-landscape-tracker/1.0",
    "Accept": "application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
}


@dataclass(frozen=True)
class RssVideo:
    youtube_video_id: str
    title: str
    url: str
    published_at: str


def fetch_channel_rss(rss_url: str, limit: int = 10) -> list[RssVideo]:
    last_error: Exception | None = None
    for attempt in range(1, _RSS_FETCH_ATTEMPTS + 1):
        try:
            response = requests.get(
                rss_url,
                headers=_RSS_REQUEST_HEADERS,
                timeout=_RSS_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.bozo and not parsed.entries:
                bozo_error = getattr(parsed, "bozo_exception", None)
                if isinstance(bozo_error, Exception):
                    raise bozo_error
                raise RuntimeError(f"Failed to parse RSS feed: {rss_url}")
            return [_video_from_entry(entry) for entry in parsed.entries[:limit]]
        except Exception as exc:
            last_error = exc
            if attempt == _RSS_FETCH_ATTEMPTS:
                break
            time.sleep(_RSS_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"Failed to parse RSS feed: {rss_url}") from last_error


def _video_from_entry(entry: dict) -> RssVideo:
    video_id = getattr(entry, "yt_videoid", None) or entry.get("yt_videoid")
    if not video_id:
        link = entry.get("link", "")
        video_id = link.rsplit("v=", 1)[-1] if "v=" in link else link.rsplit("/", 1)[-1]
    return RssVideo(
        youtube_video_id=video_id,
        title=entry.get("title", "Untitled video"),
        url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
        published_at=entry.get("published", entry.get("updated", "")),
    )
