from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from llm_landscape.domain import VideoBundle
from llm_landscape.llm.base import EnrichmentResult
from llm_landscape.llm.usage import aggregate_token_usage, cost_rates_for, estimate_cost_usd
from llm_landscape.ranking import sort_video_bundles
from llm_landscape.relationships.scoring import build_relationships


def build_public_snapshots(
    bundles: list[VideoBundle],
    enrichments: dict[str, EnrichmentResult],
    provider: Any,
    run_metadata_overrides: dict[str, Any] | None = None,
    usage_enrichments: Iterable[EnrichmentResult] | None = None,
) -> dict[str, dict]:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    videos = _build_videos_snapshot(bundles, enrichments, generated_at)
    channels = _build_channels_snapshot(bundles, enrichments, generated_at)
    relationships_body = build_relationships(bundles, enrichments, provider)
    relationships = {"schema_version": "1.0", "generated_at": generated_at, **relationships_body}
    hashes = {
        "videos": content_hash(videos),
        "channels": content_hash(channels),
        "relationships": content_hash(relationships),
    }
    token_usage = aggregate_token_usage(
        enrichments.values() if usage_enrichments is None else usage_enrichments
    )
    cost_rates = cost_rates_for(provider.name)
    run_metadata = {
        "schema_version": "1.0",
        "last_successful_run_at": generated_at,
        "status": "success",
        "provider": provider.name,
        "model": provider.model,
        "videos_seen": len(bundles),
        "videos_processed": len(enrichments),
        "videos_failed": max(0, len(bundles) - len(enrichments)),
        "estimated_cost_usd": estimate_cost_usd(token_usage, cost_rates),
        "token_usage": {
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "total_tokens": token_usage.total_tokens,
        },
        "cost_rates": {
            "input_usd_per_1m_tokens": cost_rates.input_usd_per_1m_tokens,
            "output_usd_per_1m_tokens": cost_rates.output_usd_per_1m_tokens,
            "source": cost_rates.source,
        },
        "provider_call_count": 0,
        "provider_success_count": 0,
        "provider_fallback_count": 0,
        "provider_fallback_reasons": [],
        "error_summary": None,
        "content_hashes": hashes,
    }
    if run_metadata_overrides:
        run_metadata = {**run_metadata, **run_metadata_overrides}
    return {
        "videos.json": videos,
        "channels.json": channels,
        "relationships.json": relationships,
        "run-metadata.json": run_metadata,
    }


def write_snapshots(snapshots: dict[str, dict], output_dir: Path, contracts_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    validators = _load_validators(contracts_dir)
    schema_map = {
        "videos.json": "public-videos.schema.json",
        "channels.json": "public-channels.schema.json",
        "relationships.json": "public-relationships.schema.json",
        "run-metadata.json": "run-metadata.schema.json",
    }
    for filename, payload in snapshots.items():
        validator = validators[schema_map[filename]]
        validator.validate(payload)
        destination = output_dir / filename
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, destination)


def content_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_validators(contracts_dir: Path) -> dict[str, Draft202012Validator]:
    validators: dict[str, Draft202012Validator] = {}
    for path in contracts_dir.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        validators[path.name] = Draft202012Validator(schema)
    return validators


def _build_videos_snapshot(
    bundles: list[VideoBundle], enrichments: dict[str, EnrichmentResult], generated_at: str
) -> dict:
    rows = []
    for bundle in sort_video_bundles(bundles, enrichments):
        video = bundle.video
        enrichment = enrichments[video.youtube_video_id]
        rows.append(
            {
                "youtube_video_id": video.youtube_video_id,
                "title": video.title,
                "url": video.url,
                "thumbnail_url": video.thumbnail_url,
                "published_at": video.published_at,
                "channel": {
                    "youtube_channel_id": video.channel.youtube_channel_id,
                    "title": video.channel.title,
                    "url": video.channel.url,
                },
                "primary_speaker": enrichment.primary_speaker,
                "summary": enrichment.summary,
                "content_type": enrichment.content_type,
                "topics": [topic.__dict__ for topic in enrichment.topics],
                "evidence": [_evidence_to_dict(video.url, evidence) for evidence in enrichment.evidence],
                "transcript_text": bundle.transcript.text,
                "transcript_status": "ready",
                "enrichment_status": "ready",
            }
        )
    return {"schema_version": "1.0", "generated_at": generated_at, "videos": rows}


def _build_channels_snapshot(
    bundles: list[VideoBundle], enrichments: dict[str, EnrichmentResult], generated_at: str
) -> dict:
    grouped: dict[str, dict] = {}
    for bundle in bundles:
        channel = bundle.video.channel
        entry = grouped.setdefault(
            channel.youtube_channel_id,
            {
                "youtube_channel_id": channel.youtube_channel_id,
                "title": channel.title,
                "handle": channel.handle,
                "description": channel.description,
                "url": channel.url,
                "thumbnail_url": channel.thumbnail_url,
                "video_count": 0,
                "latest_video_at": None,
                "topic_scores": {},
            },
        )
        entry["video_count"] += 1
        if entry["latest_video_at"] is None or bundle.video.published_at > entry["latest_video_at"]:
            entry["latest_video_at"] = bundle.video.published_at
        enrichment = enrichments[bundle.video.youtube_video_id]
        for topic in enrichment.topics:
            current = entry["topic_scores"].get(topic.slug)
            if current is None or topic.relevance_score > current["score"]:
                entry["topic_scores"][topic.slug] = {
                    "slug": topic.slug,
                    "label": topic.label,
                    "score": topic.relevance_score,
                }

    channels = []
    for entry in grouped.values():
        topic_scores = sorted(
            entry.pop("topic_scores").values(), key=lambda item: item["score"], reverse=True
        )
        channels.append({**entry, "top_topics": topic_scores[:5]})
    channels = sorted(
        channels,
        key=lambda channel: (
            -channel["video_count"],
            -_timestamp(channel["latest_video_at"]),
            channel["title"].lower(),
        ),
    )
    return {"schema_version": "1.0", "generated_at": generated_at, "channels": channels}


def _evidence_to_dict(video_url: str, evidence: Any) -> dict:
    timestamp_url = None
    if evidence.start_seconds is not None and "youtube.com/watch?v=" in video_url:
        timestamp_url = f"{video_url}&t={int(evidence.start_seconds)}s"
    return {
        "field_name": evidence.field_name,
        "topic_slug": evidence.topic_slug,
        "quote": evidence.quote,
        "start_seconds": evidence.start_seconds,
        "end_seconds": evidence.end_seconds,
        "timestamp_url": timestamp_url,
    }


def _timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0
