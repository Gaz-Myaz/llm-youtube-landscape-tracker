from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

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

    fallback_error: Exception | None = None
    channel_id = _channel_id_from_rss_url(rss_url)
    if channel_id:
        try:
            return _fetch_channel_videos_with_ytdlp(channel_id, limit)
        except Exception as exc:
            fallback_error = exc

    if last_error is not None and fallback_error is not None:
        raise RuntimeError(
            f"Failed to fetch channel videos for {rss_url}: "
            f"RSS failed ({last_error}); yt-dlp fallback failed ({fallback_error})"
        ) from fallback_error
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


def _fetch_channel_videos_with_ytdlp(channel_id: str, limit: int) -> list[RssVideo]:
    from yt_dlp import YoutubeDL

    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    with YoutubeDL(_ytdlp_channel_options(limit)) as youtube_dl:
        info = youtube_dl.extract_info(channel_url, download=False) or {}
    entries = [entry for entry in (info.get("entries") or []) if entry]
    if not entries:
        raise RuntimeError(f"yt-dlp returned no channel entries for {channel_url}")
    return [_video_from_ytdlp_entry(entry) for entry in entries[:limit]]


def _video_from_ytdlp_entry(entry: dict) -> RssVideo:
    video_id = entry.get("id")
    if not video_id:
        url = str(entry.get("url") or entry.get("webpage_url") or "")
        if "v=" in url:
            video_id = url.rsplit("v=", 1)[-1]
        elif url:
            video_id = url.rsplit("/", 1)[-1]
    if not video_id:
        raise RuntimeError("yt-dlp channel entry missing video id")

    url = str(entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}")
    if not url.startswith("http"):
        if url.startswith("/"):
            url = f"https://www.youtube.com{url}"
        else:
            url = f"https://www.youtube.com/watch?v={video_id}"

    return RssVideo(
        youtube_video_id=video_id,
        title=entry.get("title", "Untitled video"),
        url=url,
        published_at=_timestamp_to_iso(entry.get("timestamp")),
    )


def _channel_id_from_rss_url(rss_url: str) -> str | None:
    query = parse_qs(urlparse(rss_url).query)
    channel_ids = query.get("channel_id") or []
    channel_id = channel_ids[0].strip() if channel_ids else ""
    return channel_id or None


def _timestamp_to_iso(timestamp: object) -> str:
    if timestamp is None:
        return ""
    try:
        parsed = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    except (OverflowError, TypeError, ValueError):
        return ""
    return parsed.isoformat().replace("+00:00", "Z")


def _ytdlp_channel_options(limit: int) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": limit,
        "skip_download": True,
        "ignore_no_formats_error": True,
    }
    cookies_path = os.getenv("YT_DLP_COOKIES_PATH")
    cookies_from_browser = os.getenv("YT_DLP_COOKIES_FROM_BROWSER")
    if cookies_path:
        options["cookiefile"] = cookies_path
    if cookies_from_browser:
        browser_parts = [part.strip() for part in cookies_from_browser.split(":") if part.strip()]
        if browser_parts:
            options["cookiesfrombrowser"] = tuple(browser_parts)
    return options
