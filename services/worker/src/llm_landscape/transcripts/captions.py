from __future__ import annotations

import html
import json
import re
from pathlib import Path

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from llm_landscape.domain import Transcript, TranscriptSegment

_YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_PROVIDER_ALIASES = {
    "youtube": "youtube_transcript_api",
    "youtube_transcript_api": "youtube_transcript_api",
    "youtube-transcript-api": "youtube_transcript_api",
    "yt_dlp": "yt_dlp",
    "yt-dlp": "yt_dlp",
}
_VTT_TIMESTAMP_RE = re.compile(
    r"(?:(?P<hours>\d+):)?(?P<minutes>\d{2}):(?P<seconds>\d{2})[.,](?P<millis>\d{3})"
)


def fetch_youtube_captions(
    video_id: str,
    languages: list[str] | None = None,
    cache_dir: Path | None = None,
    providers: list[str] | None = None,
) -> Transcript:
    requested_languages = languages or ["en"]
    if cache_dir is not None:
        cached = _read_cached_transcript(video_id, requested_languages, cache_dir)
        if cached is not None:
            return cached

    provider_order = _normalize_providers(providers or ["youtube_transcript_api", "yt_dlp"])
    errors: list[str] = []
    for provider in provider_order:
        try:
            transcript_items = _fetch_provider_transcript_items(video_id, requested_languages, provider)
            transcript = _transcript_from_items(
                video_id=video_id,
                language=requested_languages[0],
                source=f"youtube_captions:{provider}",
                transcript_items=transcript_items,
            )
            if not transcript.text.strip():
                errors.append(f"{provider}: empty transcript")
                continue
            if cache_dir is not None:
                _write_cached_transcript(transcript, requested_languages, cache_dir)
            return transcript
        except Exception as exc:
            errors.append(f"{provider}: {_compact_error(exc)}")

    raise RuntimeError(
        f"No transcript provider succeeded for {video_id}. Tried {', '.join(provider_order)}. "
        f"Errors: {'; '.join(errors)}"
    )


def _transcript_from_items(
    video_id: str,
    language: str,
    source: str,
    transcript_items: list[dict],
) -> Transcript:
    segments = tuple(
        TranscriptSegment(
            segment_index=index,
            start_seconds=float(item.get("start", 0)),
            end_seconds=float(item.get("start", 0)) + float(item.get("duration", 0)),
            text=str(item.get("text", "")).replace("\n", " ").strip(),
        )
        for index, item in enumerate(transcript_items)
        if str(item.get("text", "")).strip()
    )
    return Transcript(
        video_id=video_id,
        source=source,
        language=language,
        text=" ".join(segment.text for segment in segments),
        segments=segments,
    )


def _normalize_providers(providers: list[str]) -> list[str]:
    normalized: list[str] = []
    for provider in providers:
        key = provider.strip().lower()
        if not key:
            continue
        canonical = _PROVIDER_ALIASES.get(key)
        if canonical is None:
            raise ValueError(
                f"Unsupported transcript provider '{provider}'. "
                "Use youtube_transcript_api or yt_dlp."
            )
        if canonical not in normalized:
            normalized.append(canonical)
    if not normalized:
        raise ValueError("At least one transcript provider must be configured.")
    return normalized


def _fetch_provider_transcript_items(
    video_id: str, languages: list[str], provider: str
) -> list[dict]:
    if provider == "youtube_transcript_api":
        return _fetch_transcript_items(video_id, languages)
    if provider == "yt_dlp":
        return _fetch_ytdlp_transcript_items(video_id, languages)
    raise ValueError(f"Unsupported transcript provider '{provider}'")


def _fetch_transcript_items(video_id: str, languages: list[str]) -> list[dict]:
    get_transcript = getattr(YouTubeTranscriptApi, "get_transcript", None)
    if get_transcript is not None:
        return list(get_transcript(video_id, languages=languages))

    transcript = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    to_raw_data = getattr(transcript, "to_raw_data", None)
    if to_raw_data is not None:
        return list(to_raw_data())

    return [
        {
            "text": snippet.text,
            "start": snippet.start,
            "duration": snippet.duration,
        }
        for snippet in transcript
    ]


def _fetch_ytdlp_transcript_items(video_id: str, languages: list[str]) -> list[dict]:
    from yt_dlp import YoutubeDL

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with YoutubeDL(options) as youtube_dl:
        info = youtube_dl.extract_info(_YOUTUBE_WATCH_URL.format(video_id=video_id), download=False)

    track = _select_ytdlp_caption_track(info or {}, languages)
    if track is None:
        raise RuntimeError(f"yt-dlp found no subtitle track for languages {languages}")

    response = requests.get(
        str(track["url"]),
        headers={"User-Agent": _USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()

    extension = str(track.get("ext") or "").lower()
    body = response.text
    if extension == "json3" or body.lstrip().startswith("{"):
        return _parse_json3_subtitles(body)
    return _parse_vtt_subtitles(body)


def _select_ytdlp_caption_track(info: dict, languages: list[str]) -> dict | None:
    for source_name in ("subtitles", "automatic_captions"):
        caption_map = info.get(source_name) or {}
        if not isinstance(caption_map, dict):
            continue
        for language_key in _language_keys(caption_map, languages):
            tracks = caption_map.get(language_key) or []
            preferred = _preferred_caption_track(tracks)
            if preferred is not None:
                return preferred
    return None


def _language_keys(caption_map: dict, languages: list[str]) -> list[str]:
    keys = list(caption_map.keys())
    selected: list[str] = []
    for language in languages:
        lowered = language.lower()
        for key in keys:
            key_lowered = str(key).lower()
            if key_lowered == lowered and key not in selected:
                selected.append(key)
        for key in keys:
            key_lowered = str(key).lower()
            if key_lowered.startswith(f"{lowered}-") and key not in selected:
                selected.append(key)
    return selected


def _preferred_caption_track(tracks: list[dict]) -> dict | None:
    if not tracks:
        return None
    for extension in ("json3", "vtt"):
        for track in tracks:
            if str(track.get("ext") or "").lower() == extension and track.get("url"):
                return track
    for track in tracks:
        if track.get("url"):
            return track
    return None


def _parse_json3_subtitles(body: str) -> list[dict]:
    payload = json.loads(body)
    items: list[dict] = []
    for event in payload.get("events", []):
        parts = event.get("segs") or []
        text = "".join(str(part.get("utf8", "")) for part in parts).replace("\n", " ").strip()
        if not text:
            continue
        start_seconds = float(event.get("tStartMs", 0)) / 1000
        duration_seconds = float(event.get("dDurationMs", 0)) / 1000
        items.append({"text": text, "start": start_seconds, "duration": duration_seconds})
    return items


def _parse_vtt_subtitles(body: str) -> list[dict]:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    items: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if "-->" not in line:
            index += 1
            continue
        start_text, end_text = [part.strip().split(" ")[0] for part in line.split("-->", 1)]
        start_seconds = _parse_vtt_timestamp(start_text)
        end_seconds = _parse_vtt_timestamp(end_text)
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = _clean_vtt_text(" ".join(text_lines))
        if text:
            items.append(
                {
                    "text": text,
                    "start": start_seconds,
                    "duration": max(0.0, end_seconds - start_seconds),
                }
            )
        index += 1
    return items


def _parse_vtt_timestamp(value: str) -> float:
    match = _VTT_TIMESTAMP_RE.match(value)
    if not match:
        return 0.0
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    millis = int(match.group("millis"))
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _clean_vtt_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(without_tags).strip()


def _read_cached_transcript(
    video_id: str, languages: list[str], cache_dir: Path
) -> Transcript | None:
    path = _cache_path(video_id, languages, cache_dir)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = tuple(
        TranscriptSegment(
            segment_index=int(item["segment_index"]),
            start_seconds=item.get("start_seconds"),
            end_seconds=item.get("end_seconds"),
            text=str(item["text"]),
        )
        for item in payload.get("segments", [])
    )
    return Transcript(
        video_id=str(payload.get("video_id", video_id)),
        source=str(payload.get("source", "youtube_captions_cache")),
        language=payload.get("language") or languages[0],
        text=" ".join(segment.text for segment in segments),
        segments=segments,
    )


def _write_cached_transcript(transcript: Transcript, languages: list[str], cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "video_id": transcript.video_id,
        "source": transcript.source,
        "language": transcript.language,
        "segments": [
            {
                "segment_index": segment.segment_index,
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "text": segment.text,
            }
            for segment in transcript.segments
        ],
    }
    _cache_path(transcript.video_id, languages, cache_dir).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cache_path(video_id: str, languages: list[str], cache_dir: Path) -> Path:
    language_key = "-".join(language.replace("/", "_") for language in languages)
    return cache_dir / f"{video_id}.{language_key}.json"


def _compact_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:420]
