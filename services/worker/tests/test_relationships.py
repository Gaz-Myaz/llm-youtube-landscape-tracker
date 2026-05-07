from llm_landscape.fixtures import load_mock_bundles
from llm_landscape.llm.mock import MockProvider
from llm_landscape.relationships.scoring import build_relationships


def test_mock_relationships_have_edges() -> None:
    provider = MockProvider()
    bundles = load_mock_bundles()
    enrichments = {
        bundle.video.youtube_video_id: provider.extract_video_insights(bundle.video, bundle.transcript)
        for bundle in bundles
    }

    relationships = build_relationships(bundles, enrichments, provider)

    assert relationships["nodes"]
    assert relationships["edges"]
