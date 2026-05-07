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
    max_videos_per_run: int
    max_provider_calls_per_run: int
    snapshot_output_dir: Path
    contracts_dir: Path


def load_settings() -> Settings:
    root = _repo_root()
    output_dir = os.getenv("SNAPSHOT_OUTPUT_DIR", "apps/web/public/data")
    contracts_dir = os.getenv("CONTRACTS_DIR", "contracts")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://llm_tracker:llm_tracker@localhost:5432/llm_tracker"
        ),
        provider=os.getenv("WORKER_PROVIDER", "mock"),
        vertex_project_id=os.getenv("VERTEX_PROJECT_ID") or None,
        vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        vertex_model=os.getenv("VERTEX_MODEL", "gemini-1.5-flash"),
        max_videos_per_run=int(os.getenv("MAX_VIDEOS_PER_RUN", "25")),
        max_provider_calls_per_run=int(os.getenv("MAX_PROVIDER_CALLS_PER_RUN", "50")),
        snapshot_output_dir=_resolve_path(root, output_dir),
        contracts_dir=_resolve_path(root, contracts_dir),
    )


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()

