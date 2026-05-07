import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  XCircle
} from "lucide-react";
import type { RunMetadata } from "@/lib/schemas";

const statusMeta = {
  success: { label: "Healthy", Icon: CheckCircle2, tone: "healthy" },
  partial: { label: "Partial", Icon: AlertTriangle, tone: "partial" },
  stale: { label: "Stale", Icon: Clock, tone: "stale" },
  failed: { label: "Failed", Icon: XCircle, tone: "failed" }
} as const;

export function StatusBanner({ metadata }: { metadata: RunMetadata }) {
  const relative = formatRelative(metadata.last_successful_run_at);
  const effectiveStatus = metadata.status === "success" && relative.hours > 36 ? "stale" : metadata.status;
  const status = statusMeta[effectiveStatus];
  const Icon = status.Icon;
  return (
    <header className="status-header">
      <div className="status-title-block">
        <div className="dashboard-kicker">
          <Activity size={13} />
          Live dashboard
        </div>
        <h1>LLM YouTube Landscape Tracker</h1>
        <p>Transcript-grounded map of LLM creator coverage</p>
      </div>

      <div className="status-actions">
        <span className={`freshness-pill ${status.tone}`}>
          <Icon size={13} />
          {status.label}
        </span>
        <span className="metadata-pill">
          <Clock size={13} />
          Updated {relative.label}
        </span>
        <span className="metadata-pill">
          <Cpu size={13} />
          {metadata.provider} · <code>{metadata.model}</code>
        </span>
        <a className="metadata-pill source-link" href="/data/run-metadata.json" target="_blank" rel="noreferrer">
          <Database size={13} />
          View source data
          <ExternalLink size={11} />
        </a>
      </div>

      {metadata.error_summary && metadata.status !== "success" ? (
        <div className="status-warning">
          <AlertTriangle size={14} />
          <span>{metadata.error_summary}</span>
        </div>
      ) : null}
    </header>
  );
}

function formatRelative(value: string): { label: string; hours: number } {
  const difference = Date.now() - new Date(value).getTime();
  const hours = difference / 36e5;
  if (hours < 1) {
    return { label: `${Math.max(1, Math.round(difference / 60000))}m ago`, hours };
  }
  if (hours < 24) {
    return { label: `${Math.round(hours)}h ago`, hours };
  }
  return { label: `${Math.round(hours / 24)}d ago`, hours };
}

