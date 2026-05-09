from __future__ import annotations

import csv
import re
from pathlib import Path

from llm_landscape.domain import Channel

_SEED_CHANNEL_RE = re.compile(
    r"\('(?P<youtube_channel_id>[^']+)',\s*'(?P<title>(?:''|[^'])*)',\s*"
    r"'(?P<handle>(?:''|[^'])*)',\s*'(?P<description>(?:''|[^'])*)',\s*"
    r"'(?P<url>[^']+)',\s*'(?P<rss_url>[^']+)',\s*'(?P<language>[^']+)'\)"
)


def load_seed_channels(seed_sql_path: Path) -> list[Channel]:
    content = seed_sql_path.read_text(encoding="utf-8")
    channels: list[Channel] = []
    for match in _SEED_CHANNEL_RE.finditer(content):
        channels.append(
            Channel(
                youtube_channel_id=match.group("youtube_channel_id"),
                title=_sql_unescape(match.group("title")),
                handle=_sql_unescape(match.group("handle")) or None,
                description=_sql_unescape(match.group("description")) or None,
                url=match.group("url"),
                rss_url=match.group("rss_url"),
                language=match.group("language") or "en",
            )
        )
    if not channels:
        raise RuntimeError(f"No seed channels found in {seed_sql_path}")
    return channels


def load_channels_csv(path: Path) -> list[Channel]:
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    channels = [
        Channel(
            youtube_channel_id=row["youtube_channel_id"],
            title=row["title"],
            handle=row.get("handle") or None,
            description=row.get("description") or None,
            url=row["url"],
            rss_url=row.get("rss_url") or None,
            thumbnail_url=row.get("thumbnail_url") or None,
            language=row.get("language") or "en",
        )
        for row in rows
    ]
    if not channels:
        raise RuntimeError(f"No channels found in {path}")
    return channels


def _sql_unescape(value: str) -> str:
    return value.replace("''", "'")
