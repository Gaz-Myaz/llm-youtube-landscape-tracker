from __future__ import annotations

from dataclasses import dataclass

import feedparser


@dataclass(frozen=True)
class RssVideo:
    youtube_video_id: str
    title: str
    url: str
    published_at: str


def fetch_channel_rss(rss_url: str, limit: int = 10) -> list[RssVideo]:
    parsed = feedparser.parse(rss_url)
    if parsed.bozo:
        raise RuntimeError(f"Failed to parse RSS feed: {rss_url}")

    videos: list[RssVideo] = []
    for entry in parsed.entries[:limit]:
        video_id = getattr(entry, "yt_videoid", None) or entry.get("yt_videoid")
        if not video_id:
            link = entry.get("link", "")
            video_id = link.rsplit("v=", 1)[-1] if "v=" in link else link.rsplit("/", 1)[-1]
        videos.append(
            RssVideo(
                youtube_video_id=video_id,
                title=entry.get("title", "Untitled video"),
                url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                published_at=entry.get("published", entry.get("updated", "")),
            )
        )
    return videos
