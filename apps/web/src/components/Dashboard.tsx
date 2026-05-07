"use client";

import { useMemo, useState } from "react";
import { ChannelCards } from "./ChannelCards";
import { FilterBar, type FilterState } from "./FilterBar";
import { MetricStrip } from "./MetricStrip";
import { RelationshipGraph } from "./RelationshipGraph";
import { RelationshipList } from "./RelationshipList";
import { StatusBanner } from "./StatusBanner";
import { TopicTrendList } from "./TopicTrendList";
import { VideoTable } from "./VideoTable";
import type { PublicChannel, PublicRelationships, PublicVideo, RunMetadata } from "@/lib/schemas";

export interface DashboardSnapshots {
  videos: { generated_at: string; videos: PublicVideo[] };
  channels: { generated_at: string; channels: PublicChannel[] };
  relationships: PublicRelationships;
  runMetadata: RunMetadata;
}

export function Dashboard({ snapshots }: { snapshots: DashboardSnapshots }) {
  const [filters, setFilters] = useState<FilterState>({
    query: "",
    channelId: "",
    topicSlug: "",
    contentType: "",
    sort: "date"
  });
  const [highlightId, setHighlightId] = useState<string | null>(null);

  const filteredVideos = useMemo(() => {
    const query = filters.query.trim().toLowerCase();
    let rows = snapshots.videos.videos.filter((video) => {
      if (filters.channelId && video.channel.youtube_channel_id !== filters.channelId) {
        return false;
      }
      if (filters.topicSlug && !video.topics.some((topic) => topic.slug === filters.topicSlug)) {
        return false;
      }
      if (filters.contentType && video.content_type !== filters.contentType) {
        return false;
      }
      if (!query) {
        return true;
      }
      return [
        video.title,
        video.summary,
        video.primary_speaker ?? "",
        video.channel.title,
        video.content_type,
        ...video.topics.map((topic) => topic.label),
        ...video.evidence.map((evidence) => evidence.quote)
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });

    if (filters.sort === "channel") {
      rows = rows.sort((a, b) => a.channel.title.localeCompare(b.channel.title));
    } else if (filters.sort === "relevance") {
      rows = rows.sort((a, b) => maxRelevance(b) - maxRelevance(a));
    } else {
      rows = rows.sort(
        (a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
      );
    }
    return rows;
  }, [filters, snapshots.videos.videos]);

  const channelOptions = useMemo(
    () =>
      snapshots.channels.channels.map((channel) => ({
        value: channel.youtube_channel_id,
        label: channel.title
      })),
    [snapshots.channels.channels]
  );
  const topicOptions = useMemo(() => {
    const topics = new Map<string, string>();
    for (const video of snapshots.videos.videos) {
      for (const topic of video.topics) {
        topics.set(topic.slug, topic.label);
      }
    }
    return Array.from(topics.entries())
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([value, label]) => ({ value, label }));
  }, [snapshots.videos.videos]);
  const contentTypeOptions = useMemo(
    () =>
      Array.from(new Set(snapshots.videos.videos.map((video) => video.content_type)))
        .sort()
        .map((value) => ({ value, label: value })),
    [snapshots.videos.videos]
  );

  return (
    <main className="dashboard-shell">
      <StatusBanner metadata={snapshots.runMetadata} />

      <section aria-label="Pipeline metrics">
        <MetricStrip
          videos={snapshots.videos.videos}
          channels={snapshots.channels.channels}
          relationships={snapshots.relationships}
          metadata={snapshots.runMetadata}
        />
      </section>

      <section aria-label="Video intelligence" className="section-stack">
        <SectionHeading
          eyebrow="Video intelligence"
          title="Transcript-grounded video table"
          hint="Search, filter, and inspect evidence snippets."
        />
        <FilterBar
          state={filters}
          onChange={setFilters}
          channels={channelOptions}
          topics={topicOptions}
          contentTypes={contentTypeOptions}
          resultCount={filteredVideos.length}
          totalCount={snapshots.videos.videos.length}
        />
        <VideoTable videos={filteredVideos} />
      </section>

      <section aria-label="Channel relationships" className="section-stack">
        <SectionHeading
          eyebrow="Relationships"
          title="How channels relate"
          hint="Edges weighted by topic-cosine similarity."
        />
        <div className="relationship-grid">
          <div className="relationship-graph-column">
            <RelationshipGraph
              relationships={snapshots.relationships}
              highlightId={highlightId}
              onHover={setHighlightId}
            />
          </div>
          <div className="relationship-list-column">
            <RelationshipList
              relationships={snapshots.relationships}
              highlightId={highlightId}
              onHover={setHighlightId}
            />
          </div>
        </div>
      </section>

      <section aria-label="Channels and topics" className="section-stack">
        <div className="channel-topic-grid">
          <div className="channel-topic-column channel-topic-column-wide">
            <SectionHeading eyebrow="Channels" title="Tracked channel overview" />
            <ChannelCards channels={snapshots.channels.channels} relationships={snapshots.relationships} />
          </div>
          <div className="channel-topic-column">
            <SectionHeading eyebrow="Topics" title="Topic trends" />
            <TopicTrendList videos={snapshots.videos.videos} />
          </div>
        </div>
      </section>
    </main>
  );
}

function SectionHeading({ eyebrow, title, hint }: { eyebrow: string; title: string; hint?: string }) {
  return (
    <div className="section-heading">
      <div>
        <p>{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {hint ? <span>{hint}</span> : null}
    </div>
  );
}

function maxRelevance(video: PublicVideo) {
  return Math.max(0, ...video.topics.map((topic) => topic.relevance_score));
}
