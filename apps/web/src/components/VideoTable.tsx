import { Fragment, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  FileText,
  Quote,
  XCircle
} from "lucide-react";
import { EmptyState } from "./EmptyState";
import { EvidenceDrawer } from "./EvidenceDrawer";
import type { PublicVideo } from "@/lib/schemas";

export function VideoTable({ videos }: { videos: PublicVideo[] }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [drawerVideo, setDrawerVideo] = useState<PublicVideo | null>(null);

  if (!videos.length) {
    return (
      <div className="panel">
        <EmptyState title="No videos match these filters" description="Try clearing a filter or broadening the search query." />
      </div>
    );
  }

  return (
    <>
      <div className="video-table-panel">
        <div className="table-scroll">
          <table className="video-table">
            <thead>
              <tr>
                <th className="wide-col">Video</th>
                <th>Channel</th>
                <th>Published</th>
                <th>Speaker</th>
                <th>Type</th>
                <th>Topics</th>
                <th className="summary-col">Summary &amp; evidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => {
                const isOpen = openId === video.youtube_video_id;
                const firstEvidence = video.evidence[0];
                return (
                  <Fragment key={video.youtube_video_id}>
                    <tr>
                      <td>
                        <div className="video-title-cell">
                          <button
                            onClick={() => setOpenId(isOpen ? null : video.youtube_video_id)}
                            aria-label={isOpen ? "Collapse row" : "Expand row"}
                            type="button"
                          >
                            {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </button>
                          <a href={video.url} target="_blank" rel="noreferrer">
                            <span>{video.title}</span>
                            <ExternalLink size={12} />
                          </a>
                        </div>
                      </td>
                      <td>
                        <a className="plain-link" href={video.channel.url} target="_blank" rel="noreferrer">
                          {video.channel.title}
                        </a>
                      </td>
                      <td className="num muted-cell">{formatDate(video.published_at)}</td>
                      <td>{video.primary_speaker || <span className="muted italic">unknown</span>}</td>
                      <td>
                        <span className="type-pill">{video.content_type}</span>
                      </td>
                      <td>
                        <TopicPills topics={video.topics} />
                      </td>
                      <td>
                        <div className="summary-cell">
                          <p>{video.summary}</p>
                          {firstEvidence ? (
                            <button className="evidence-preview" onClick={() => setDrawerVideo(video)} type="button">
                              <Quote size={11} />
                              <span>"{firstEvidence.quote}"</span>
                              <a
                                href={firstEvidence.timestamp_url ?? video.url}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(event) => event.stopPropagation()}
                              >
                                {formatTimestamp(firstEvidence.start_seconds)}
                              </a>
                            </button>
                          ) : null}
                        </div>
                      </td>
                      <td>
                        <StatusPill transcript={video.transcript_status} enrichment={video.enrichment_status} />
                      </td>
                    </tr>
                    {isOpen ? (
                      <tr className="expanded-row">
                        <td colSpan={8}>
                          <ExpandedRow video={video} onOpenDrawer={() => setDrawerVideo(video)} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <EvidenceDrawer video={drawerVideo} onClose={() => setDrawerVideo(null)} />
    </>
  );
}

function ExpandedRow({ video, onOpenDrawer }: { video: PublicVideo; onOpenDrawer: () => void }) {
  return (
    <div className="expanded-grid">
      <div>
        <p className="mini-heading">Summary</p>
        <p>{video.summary}</p>
        <div className="topic-row expanded-topics">
          {video.topics.map((topic) => (
            <span key={topic.slug} className="topic-chip">
              {topic.label}
              <small>{Math.round(topic.relevance_score * 100)}</small>
            </span>
          ))}
        </div>
      </div>
      <div>
        <div className="expanded-evidence-header">
          <p className="mini-heading">Evidence ({video.evidence.length})</p>
          {video.evidence.length ? (
            <button onClick={onOpenDrawer} type="button">
              <FileText size={12} />
              Open all
            </button>
          ) : null}
        </div>
        <div className="expanded-snippets">
          {video.evidence.slice(0, 2).map((evidence, index) => (
            <div key={`${evidence.field_name}-${index}`}>
              <p>"{evidence.quote}"</p>
              <a href={evidence.timestamp_url ?? video.url} target="_blank" rel="noreferrer">
                {formatTimestamp(evidence.start_seconds)} <ExternalLink size={10} />
              </a>
            </div>
          ))}
          {!video.evidence.length ? <span className="muted italic">No evidence snippets.</span> : null}
        </div>
      </div>
    </div>
  );
}

function TopicPills({ topics }: { topics: PublicVideo["topics"] }) {
  if (!topics.length) {
    return <span className="muted">-</span>;
  }
  const visible = topics.slice(0, 3);
  const extra = topics.length - visible.length;
  return (
    <div className="topic-row">
      {visible.map((topic) => (
        <span className="topic-chip" key={topic.slug} title={`relevance ${topic.relevance_score.toFixed(2)}`}>
          {topic.label}
        </span>
      ))}
      {extra > 0 ? <span className="topic-chip muted-chip">+{extra}</span> : null}
    </div>
  );
}

function StatusPill({ transcript, enrichment }: { transcript: string; enrichment: string }) {
  let label = "Ready";
  let Icon = CheckCircle2;
  let tone = "ready";
  if (enrichment === "failed" || transcript === "failed") {
    label = "Failed";
    Icon = XCircle;
    tone = "failed";
  } else if (["missing", "unavailable", "fallback_required"].includes(transcript)) {
    label = "No transcript";
    Icon = AlertTriangle;
    tone = "warning";
  } else if (enrichment === "pending" || transcript === "pending") {
    label = "Pending";
    Icon = Clock;
    tone = "pending";
  } else if (enrichment === "skipped" || transcript === "skipped") {
    label = "Skipped";
    Icon = Clock;
    tone = "pending";
  }
  return (
    <span className={`table-status ${tone}`}>
      <Icon size={11} />
      {label}
    </span>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", year: "numeric" }).format(
    new Date(value)
  );
}

function formatTimestamp(value: number | null | undefined) {
  if (value == null) {
    return "0:00";
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}