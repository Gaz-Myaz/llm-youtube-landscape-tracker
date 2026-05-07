import { Calendar, ExternalLink, Film, Link2 } from "lucide-react";
import type { PublicChannel, PublicRelationships } from "@/lib/schemas";

export function ChannelCards({
  channels,
  relationships
}: {
  channels: PublicChannel[];
  relationships: PublicRelationships;
}) {
  const labels = new Map(relationships.nodes.map((node) => [node.id, node.label]));
  const strongestFor = (id: string) => {
    let best: PublicRelationships["edges"][number] | null = null;
    for (const edge of relationships.edges) {
      if (edge.source !== id && edge.target !== id) {
        continue;
      }
      if (!best || edge.similarity_score > best.similarity_score) {
        best = edge;
      }
    }
    if (!best) {
      return null;
    }
    const otherId = best.source === id ? best.target : best.source;
    return { label: labels.get(otherId) ?? otherId, score: best.similarity_score };
  };

  return (
    <div className="channel-grid">
      {channels.map((channel) => (
        <article className="channel-card" key={channel.youtube_channel_id}>
          <div className="channel-card-head">
            <div>
              <h3>{channel.title}</h3>
              <code>{channel.handle ?? "@unknown"}</code>
            </div>
            <a href={channel.url} target="_blank" rel="noreferrer" aria-label="Open channel">
              <ExternalLink size={13} />
            </a>
          </div>
          <div className="channel-meta-row">
            <span>
              <Film size={12} />
              {channel.video_count}
            </span>
            {channel.latest_video_at ? (
              <span>
                <Calendar size={12} />
                {formatDate(channel.latest_video_at)}
              </span>
            ) : null}
          </div>
          <div className="topic-row">
            {channel.top_topics.slice(0, 3).map((topic) => (
              <span className="topic-chip" key={topic.slug}>
                {topic.label}
              </span>
            ))}
          </div>
          <StrongestRelationship relationship={strongestFor(channel.youtube_channel_id)} />
        </article>
      ))}
    </div>
  );
}

function StrongestRelationship({ relationship }: { relationship: { label: string; score: number } | null }) {
  if (!relationship) {
    return null;
  }
  return (
    <div className="strongest-relationship">
      <Link2 size={11} />
      <span>
        Closest to <strong>{relationship.label}</strong>
      </span>
      <code>{relationship.score.toFixed(2)}</code>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(value)
  );
}
