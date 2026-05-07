from __future__ import annotations

from youtube_transcript_api import YouTubeTranscriptApi

from llm_landscape.domain import Transcript, TranscriptSegment


def fetch_youtube_captions(video_id: str, languages: list[str] | None = None) -> Transcript:
    transcript_items = YouTubeTranscriptApi.get_transcript(video_id, languages=languages or ["en"])
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
        source="youtube_captions",
        language=(languages or ["en"])[0],
        text=" ".join(segment.text for segment in segments),
        segments=segments,
    )
