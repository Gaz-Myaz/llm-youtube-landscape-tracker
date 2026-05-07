from llm_landscape.exports.snapshots import build_public_snapshots
from llm_landscape.fixtures import load_mock_bundles
from llm_landscape.llm.mock import MockProvider


def test_mock_snapshots_include_public_read_models() -> None:
    provider = MockProvider()
    bundles = load_mock_bundles()
    enrichments = {
        bundle.video.youtube_video_id: provider.extract_video_insights(bundle.video, bundle.transcript)
        for bundle in bundles
    }

    snapshots = build_public_snapshots(bundles, enrichments, provider)

    assert set(snapshots) == {
        "videos.json",
        "channels.json",
        "relationships.json",
        "run-metadata.json",
    }
    assert snapshots["videos.json"]["videos"]