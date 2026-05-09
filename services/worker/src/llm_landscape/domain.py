from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    youtube_channel_id: str
    title: str
    handle: str | None
    description: str | None
    url: str
    rss_url: str | None = None
    thumbnail_url: str | None = None
    language: str = "en"


@dataclass(frozen=True)
class Video:
    youtube_video_id: str
    title: str
    url: str
    published_at: str
    channel: Channel
    description: str | None = None
    thumbnail_url: str | None = None


@dataclass(frozen=True)
class Transcript:
    video_id: str
    source: str
    language: str | None
    text: str
    segments: tuple["TranscriptSegment", ...]


@dataclass(frozen=True)
class TranscriptSegment:
    segment_index: int
    start_seconds: float | None
    end_seconds: float | None
    text: str


@dataclass(frozen=True)
class VideoBundle:
    video: Video
    transcript: Transcript
