from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from llm_landscape.analysis import DeterministicAnalyzer, is_landscape_relevant
from llm_landscape.channels import load_channels_csv, load_seed_channels
from llm_landscape.config import load_settings
from llm_landscape.domain import Video, VideoBundle
from llm_landscape.exports.snapshots import build_public_snapshots, write_snapshots
from llm_landscape.fixtures import load_mock_bundles
from llm_landscape.ingestion.rss import fetch_channel_rss
from llm_landscape.llm.factory import create_provider
from llm_landscape.transcripts.captions import fetch_youtube_captions


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM YouTube landscape worker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mock_export = subparsers.add_parser("mock-export", help="Export mock public snapshots")
    mock_export.add_argument("--output-dir", type=Path, default=None)

    real_export = subparsers.add_parser(
        "real-export", help="Fetch channel RSS/captions and export subtitle-backed snapshots"
    )
    real_export.add_argument("--output-dir", type=Path, default=None)
    real_export.add_argument("--channels-csv", type=Path, default=None)
    real_export.add_argument("--videos-per-channel", type=int, default=None)
    real_export.add_argument("--max-videos", type=int, default=None)
    real_export.add_argument("--language", action="append", dest="languages", default=None)
    real_export.add_argument("--transcript-provider", action="append", dest="transcript_providers", default=None)
    real_export.add_argument("--transcript-delay-seconds", type=float, default=None)

    validate = subparsers.add_parser("validate-snapshots", help="Validate public snapshots")
    validate.add_argument("--data-dir", type=Path, default=None)

    args = parser.parse_args()
    settings = load_settings()

    if settings.yt_dlp_cookies_path is not None:
        os.environ.setdefault("YT_DLP_COOKIES_PATH", str(settings.yt_dlp_cookies_path))
    if settings.yt_dlp_cookies_from_browser is not None:
        os.environ.setdefault("YT_DLP_COOKIES_FROM_BROWSER", settings.yt_dlp_cookies_from_browser)

    if args.command == "mock-export":
        output_dir = args.output_dir or settings.snapshot_output_dir
        provider = create_provider(settings)
        bundles = load_mock_bundles()[: settings.max_videos_per_run]
        enrichments = {
            bundle.video.youtube_video_id: provider.extract_video_insights(
                bundle.video, bundle.transcript
            )
            for bundle in bundles
        }
        snapshots = build_public_snapshots(bundles, enrichments, provider)
        write_snapshots(snapshots, output_dir=output_dir, contracts_dir=settings.contracts_dir)
        print(f"Exported {len(snapshots)} snapshots to {output_dir}")
        return

    if args.command == "real-export":
        output_dir = args.output_dir or settings.snapshot_output_dir
        channels = (
            load_channels_csv(args.channels_csv)
            if args.channels_csv
            else load_seed_channels(settings.seed_channels_path)
        )
        bundles, skipped = collect_real_bundles(
            channels=channels,
            videos_per_channel=args.videos_per_channel or settings.videos_per_channel,
            max_videos=args.max_videos or settings.max_videos_per_run,
            languages=args.languages or ["en"],
            transcript_cache_dir=settings.transcript_cache_dir,
            request_delay_seconds=(
                args.transcript_delay_seconds
                if args.transcript_delay_seconds is not None
                else settings.transcript_request_delay_seconds
            ),
            transcript_providers=list(args.transcript_providers or settings.transcript_providers),
        )
        if not bundles:
            details = _run_summary(skipped, []) or "No skip details were recorded."
            raise RuntimeError(
                "No caption-backed videos were collected. Try a smaller channel set, different "
                f"--language, or verify captions are available. {details}"
            )
        fetch_skipped = list(skipped)
        provider = DeterministicAnalyzer()
        candidate_enrichments = {
            bundle.video.youtube_video_id: provider.extract_video_insights(bundle.video, bundle.transcript)
            for bundle in bundles
        }
        filtered_bundles = []
        enrichments = {}
        filtered_out = []
        for bundle in bundles:
            enrichment = candidate_enrichments[bundle.video.youtube_video_id]
            if is_landscape_relevant(bundle.video, enrichment):
                filtered_bundles.append(bundle)
                enrichments[bundle.video.youtube_video_id] = enrichment
            else:
                filtered_out.append(
                    f"{bundle.video.youtube_video_id}: no deterministic LLM landscape signal"
                )
        if not filtered_bundles:
            raise RuntimeError(
                "Caption-backed videos were collected, but none matched deterministic LLM landscape rules. "
                "Try a broader channel set or increase --videos-per-channel."
            )
        snapshots = build_public_snapshots(filtered_bundles, enrichments, provider)
        snapshots["run-metadata.json"]["videos_seen"] = len(bundles) + len(fetch_skipped)
        snapshots["run-metadata.json"]["videos_failed"] = len(fetch_skipped)
        snapshots["run-metadata.json"]["status"] = "partial" if fetch_skipped else "success"
        snapshots["run-metadata.json"]["error_summary"] = _run_summary(fetch_skipped, filtered_out)
        write_snapshots(snapshots, output_dir=output_dir, contracts_dir=settings.contracts_dir)
        print(
            f"Exported {len(filtered_bundles)} caption-backed videos to {output_dir} "
            f"({len(fetch_skipped) + len(filtered_out)} skipped/filtered)"
        )
        return

    if args.command == "validate-snapshots":
        data_dir = args.data_dir or settings.snapshot_output_dir
        validate_snapshots(data_dir=data_dir, contracts_dir=settings.contracts_dir)
        print(f"Validated snapshots in {data_dir}")
        return


def validate_snapshots(data_dir: Path, contracts_dir: Path) -> None:
    schema_map = {
        "videos.json": "public-videos.schema.json",
        "channels.json": "public-channels.schema.json",
        "relationships.json": "public-relationships.schema.json",
        "run-metadata.json": "run-metadata.schema.json",
    }
    for snapshot_name, schema_name in schema_map.items():
        snapshot = json.loads((data_dir / snapshot_name).read_text(encoding="utf-8"))
        schema = json.loads((contracts_dir / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(snapshot)


def collect_real_bundles(
    channels: list,
    videos_per_channel: int,
    max_videos: int,
    languages: list[str],
    transcript_cache_dir: Path | None = None,
    request_delay_seconds: float = 0.0,
    transcript_providers: list[str] | None = None,
) -> tuple[list[VideoBundle], list[str]]:
    bundles: list[VideoBundle] = []
    skipped: list[str] = []
    seen_video_ids: set[str] = set()
    for channel in channels:
        if not channel.rss_url:
            skipped.append(f"{channel.title}: missing RSS URL")
            continue
        try:
            rss_videos = fetch_channel_rss(channel.rss_url, limit=videos_per_channel)
        except Exception as exc:
            skipped.append(f"{channel.title}: RSS fetch failed ({_compact_error(exc)})")
            continue
        for rss_video in rss_videos:
            if rss_video.youtube_video_id in seen_video_ids:
                continue
            if len(seen_video_ids) >= max_videos:
                return bundles, skipped
            seen_video_ids.add(rss_video.youtube_video_id)
            if request_delay_seconds > 0 and len(seen_video_ids) > 1:
                time.sleep(request_delay_seconds)
            try:
                transcript = fetch_youtube_captions(
                    rss_video.youtube_video_id,
                    languages=languages,
                    cache_dir=transcript_cache_dir,
                    providers=transcript_providers,
                )
            except Exception as exc:
                skipped.append(
                    f"{rss_video.youtube_video_id}: captions unavailable ({_compact_error(exc)})"
                )
                continue
            if not transcript.text.strip():
                skipped.append(f"{rss_video.youtube_video_id}: empty captions")
                continue
            bundles.append(
                VideoBundle(
                    video=Video(
                        youtube_video_id=rss_video.youtube_video_id,
                        title=rss_video.title,
                        url=rss_video.url,
                        published_at=_as_iso_datetime(rss_video.published_at),
                        channel=channel,
                    ),
                    transcript=transcript,
                )
            )
    return bundles, skipped


def _as_iso_datetime(value: str) -> str:
    if not value:
        return "1970-01-01T00:00:00Z"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_summary(fetch_skipped: list[str], filtered_out: list[str]) -> str | None:
    summaries = []
    if fetch_skipped:
        examples = "; ".join(fetch_skipped[:3])
        suffix = f"; {len(fetch_skipped) - 3} more" if len(fetch_skipped) > 3 else ""
        summaries.append(
            f"Skipped {len(fetch_skipped)} videos/channels while fetching real captions: {examples}{suffix}"
        )
    if filtered_out:
        examples = "; ".join(filtered_out[:3])
        suffix = f"; {len(filtered_out) - 3} more" if len(filtered_out) > 3 else ""
        summaries.append(
            f"Filtered {len(filtered_out)} caption-backed videos outside deterministic LLM landscape rules: {examples}{suffix}"
        )
    if not summaries:
        return None
    return " ".join(summaries)


def _compact_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:420]


if __name__ == "__main__":
    main()
