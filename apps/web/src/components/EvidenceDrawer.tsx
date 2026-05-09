import { ExternalLink, FileText, Quote, X } from "lucide-react";
import { useEffect } from "react";
import type { PublicVideo } from "@/lib/schemas";

export function EvidenceDrawer({ video, onClose }: { video: PublicVideo | null; onClose: () => void }) {
  useEffect(() => {
    if (!video) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, video]);

  if (!video) {
    return null;
  }

  return (
    <div className="drawer-root">
      <button className="drawer-backdrop" aria-label="Close evidence drawer" onClick={onClose} />
      <aside className="evidence-drawer">
        <header>
          <div>
            <p>Evidence · {video.channel.title}</p>
            <h2>{video.title}</h2>
            <a href={video.url} target="_blank" rel="noreferrer">
              Watch on YouTube <ExternalLink size={11} />
            </a>
          </div>
          <button onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>
        <div className="drawer-body">
          <section>
            <p className="drawer-eyebrow">Summary</p>
            <p>{video.summary}</p>
          </section>
          <section>
            <p className="drawer-eyebrow">Snippets ({video.evidence.length})</p>
            <ul className="snippet-list">
              {video.evidence.map((evidence, index) => {
                const topicLabel =
                  video.topics.find((topic) => topic.slug === evidence.topic_slug)?.label ??
                  evidence.topic_slug ??
                  "general";
                return (
                  <li key={`${evidence.field_name}-${index}`}>
                    <div className="snippet-meta">
                      <span>
                        <Quote size={11} />
                        {evidence.field_name} · {topicLabel}
                      </span>
                      <a href={evidence.timestamp_url ?? video.url} target="_blank" rel="noreferrer">
                        {formatTimestamp(evidence.start_seconds)}-{formatTimestamp(evidence.end_seconds)}
                        <ExternalLink size={10} />
                      </a>
                    </div>
                    <p>"{evidence.quote}"</p>
                  </li>
                );
              })}
              {!video.evidence.length ? <li className="empty-snippet">No evidence snippets recorded.</li> : null}
            </ul>
          </section>
          <section>
            <div className="transcript-header">
              <p className="drawer-eyebrow">Full Subtitles</p>
              <span>
                <FileText size={11} />
                {wordCount(video.transcript_text)} words
              </span>
            </div>
            <pre className="transcript-text">{video.transcript_text}</pre>
          </section>
        </div>
      </aside>
    </div>
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

function wordCount(value: string) {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}
