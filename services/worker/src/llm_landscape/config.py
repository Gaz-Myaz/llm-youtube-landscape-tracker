from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "Project.md").exists() or (parent / "contracts").exists():
            return parent
    return Path(os.getenv("REPO_ROOT", Path.cwd())).resolve()


@dataclass(frozen=True)
class Settings:
    database_url: str
    provider: str
    vertex_project_id: str | None
    vertex_location: str
    vertex_model: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    anthropic_api_key: str | None
    anthropic_base_url: str
    anthropic_model: str
    max_videos_per_run: int
    max_provider_calls_per_run: int
    videos_per_channel: int
    transcript_request_delay_seconds: float
    transcript_providers: tuple[str, ...]
    yt_dlp_cookies_path: Path | None
    yt_dlp_cookies_from_browser: str | None
    transcript_cache_dir: Path
    snapshot_output_dir: Path
    contracts_dir: Path
    seed_channels_path: Path


def load_settings() -> Settings:
    root = _repo_root()
    output_dir = os.getenv("SNAPSHOT_OUTPUT_DIR", "apps/web/public/data")
    contracts_dir = os.getenv("CONTRACTS_DIR", "contracts")
    seed_channels_path = os.getenv("SEED_CHANNELS_PATH", "infra/db/seed_channels.sql")
    transcript_cache_dir = os.getenv("TRANSCRIPT_CACHE_DIR", "data/transcripts")
    transcript_request_delay_seconds = os.getenv("TRANSCRIPT_REQUEST_DELAY_SECONDS", "0.75")
    transcript_providers = os.getenv("TRANSCRIPT_PROVIDERS", "youtube_transcript_api,yt_dlp")
    yt_dlp_cookies_path = os.getenv("YT_DLP_COOKIES_PATH") or None
    yt_dlp_cookies_from_browser = os.getenv("YT_DLP_COOKIES_FROM_BROWSER") or None
    provider = os.getenv("WORKER_PROVIDER", "mock").strip().lower()
    if provider in {"gemini", "google", "google-gemini"}:
        compatible_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None
        compatible_base_url = os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
        )
        compatible_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    else:
        compatible_api_key = os.getenv("OPENAI_API_KEY") or None
        compatible_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        compatible_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://llm_tracker:llm_tracker@localhost:5432/llm_tracker"
        ),
        provider=provider,
        vertex_project_id=os.getenv("VERTEX_PROJECT_ID") or None,
        vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        vertex_model=os.getenv("VERTEX_MODEL", "gemini-1.5-flash"),
        openai_api_key=compatible_api_key,
        openai_base_url=compatible_base_url,
        openai_model=compatible_model,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        max_videos_per_run=int(os.getenv("MAX_VIDEOS_PER_RUN", "25")),
        max_provider_calls_per_run=int(os.getenv("MAX_PROVIDER_CALLS_PER_RUN", "50")),
        videos_per_channel=int(os.getenv("VIDEOS_PER_CHANNEL", "5")),
        transcript_request_delay_seconds=float(transcript_request_delay_seconds),
        transcript_providers=tuple(
            provider.strip() for provider in transcript_providers.split(",") if provider.strip()
        ),
        yt_dlp_cookies_path=_resolve_path(root, yt_dlp_cookies_path) if yt_dlp_cookies_path else None,
        yt_dlp_cookies_from_browser=yt_dlp_cookies_from_browser,
        transcript_cache_dir=_resolve_path(root, transcript_cache_dir),
        snapshot_output_dir=_resolve_path(root, output_dir),
        contracts_dir=_resolve_path(root, contracts_dir),
        seed_channels_path=_resolve_path(root, seed_channels_path),
    )


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()

