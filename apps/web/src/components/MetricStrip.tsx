import { AlertTriangle, DollarSign, Film, Network, Tags, Users, type LucideIcon } from "lucide-react";
import type { PublicChannel, PublicRelationships, PublicVideo, RunMetadata } from "@/lib/schemas";

export function MetricStrip({
  videos,
  channels,
  relationships,
  metadata
}: {
  videos: PublicVideo[];
  channels: PublicChannel[];
  relationships: PublicRelationships;
  metadata: RunMetadata;
}) {
  const topicCount = new Set(videos.flatMap((video) => video.topics.map((topic) => topic.slug))).size;
  const fallbackCount = metadata.provider_fallback_count ?? 0;
  const failedCount = metadata.videos_failed;
  const skippedCount = metadata.videos_skipped;
  const tokenCount = metadata.token_usage?.total_tokens ?? 0;
  const issueCount = failedCount + skippedCount + fallbackCount;
  return (
    <div className="metric-strip">
      <Metric Icon={Film} label="Videos tracked" value={String(videos.length)} sub={`${metadata.videos_seen} seen total`} />
      <Metric Icon={Users} label="Channels" value={String(channels.length)} />
      <Metric Icon={Tags} label="Topics detected" value={String(topicCount)} />
      <Metric Icon={Network} label="Relationships" value={String(relationships.edges.length)} sub={`${relationships.nodes.length} nodes`} />
      <Metric
        Icon={AlertTriangle}
        label="Run issues"
        value={String(issueCount)}
        sub={formatIssueSummary(failedCount, skippedCount, fallbackCount)}
        tone={failedCount > 0 || fallbackCount > 0 ? "warning" : "default"}
      />
      <Metric
        Icon={DollarSign}
        label="Estimated cost"
        value={formatCost(metadata.estimated_cost_usd)}
        sub={tokenCount > 0 ? `${tokenCount.toLocaleString()} tokens` : "this run"}
      />
    </div>
  );
}

function formatCost(value: number): string {
  if (value > 0 && value < 0.01) {
    return "<$0.01";
  }
  return `$${value.toFixed(2)}`;
}

function formatIssueSummary(failedCount: number, skippedCount: number, fallbackCount: number): string {
  const parts = [];
  if (failedCount > 0) {
    parts.push(`${failedCount} failed`);
  }
  if (skippedCount > 0) {
    parts.push(`${skippedCount} skipped`);
  }
  if (fallbackCount > 0) {
    parts.push(`${fallbackCount} provider fallback`);
  }
  return parts.length > 0 ? parts.join(" · ") : "no issues";
}

function Metric({
  Icon,
  label,
  value,
  sub,
  tone = "default"
}: {
  Icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "warning";
}) {
  return (
    <div className="metric-panel">
      <div className="metric-heading">
        <Icon size={13} />
        {label}
      </div>
      <strong className={tone === "warning" ? "warning-text" : ""}>{value}</strong>
      {sub ? <span>{sub}</span> : null}
    </div>
  );
}
