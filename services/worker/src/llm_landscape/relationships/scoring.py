from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from llm_landscape.domain import VideoBundle
from llm_landscape.llm.base import EnrichmentResult, LlmProvider


def build_relationships(
    bundles: list[VideoBundle],
    enrichments: dict[str, EnrichmentResult],
    provider: LlmProvider,
) -> dict:
    channel_topics: dict[str, dict[str, dict]] = defaultdict(dict)
    channels: dict[str, dict] = {}
    video_counts: dict[str, int] = defaultdict(int)

    for bundle in bundles:
        channel = bundle.video.channel
        channels[channel.youtube_channel_id] = {
            "id": channel.youtube_channel_id,
            "label": channel.title,
        }
        video_counts[channel.youtube_channel_id] += 1
        enrichment = enrichments[bundle.video.youtube_video_id]
        for topic in enrichment.topics:
            current = channel_topics[channel.youtube_channel_id].get(topic.slug)
            if current is None or topic.relevance_score > current["score"]:
                channel_topics[channel.youtube_channel_id][topic.slug] = {
                    "slug": topic.slug,
                    "label": topic.label,
                    "score": topic.relevance_score,
                }

    nodes = []
    for channel_id, channel in sorted(channels.items(), key=lambda item: item[1]["label"].lower()):
        sorted_topics = sorted(
            channel_topics[channel_id].values(), key=lambda item: item["score"], reverse=True
        )
        nodes.append(
            {
                "id": channel_id,
                "label": channel["label"],
                "video_count": video_counts[channel_id],
                "top_topics": [topic["label"] for topic in sorted_topics[:4]],
            }
        )

    edges = []
    for source_id, target_id in combinations(sorted(channels), 2):
        source_topics = channel_topics[source_id]
        target_topics = channel_topics[target_id]
        shared_slugs = sorted(set(source_topics) & set(target_topics))
        union_size = len(set(source_topics) | set(target_topics)) or 1
        score = len(shared_slugs) / union_size
        if score <= 0:
            continue
        shared_topics = [
            {
                "slug": slug,
                "label": source_topics[slug]["label"],
                "score": round((source_topics[slug]["score"] + target_topics[slug]["score"]) / 2, 3),
            }
            for slug in shared_slugs
        ]
        explanation = provider.summarize_relationship(
            source_channel=channels[source_id]["label"],
            target_channel=channels[target_id]["label"],
            shared_topic_labels=[topic["label"] for topic in shared_topics],
            score=score,
        )
        edges.append(
            {
                "source": source_id,
                "target": target_id,
                "similarity_score": round(score, 3),
                "method": "topic_overlap",
                "shared_topics": shared_topics,
                "explanation": explanation,
            }
        )
    nodes = sorted(nodes, key=lambda node: (-node["video_count"], node["label"].lower()))
    edges = sorted(
        edges,
        key=lambda edge: (
            -edge["similarity_score"],
            -len(edge["shared_topics"]),
            edge["source"],
            edge["target"],
        ),
    )
    return {"nodes": nodes, "edges": edges}
