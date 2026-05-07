from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from llm_landscape.config import load_settings
from llm_landscape.exports.snapshots import build_public_snapshots, write_snapshots
from llm_landscape.fixtures import load_mock_bundles
from llm_landscape.llm.factory import create_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM YouTube landscape worker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mock_export = subparsers.add_parser("mock-export", help="Export mock public snapshots")
    mock_export.add_argument("--output-dir", type=Path, default=None)

    validate = subparsers.add_parser("validate-snapshots", help="Validate public snapshots")
    validate.add_argument("--data-dir", type=Path, default=None)

    args = parser.parse_args()
    settings = load_settings()

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


if __name__ == "__main__":
    main()
