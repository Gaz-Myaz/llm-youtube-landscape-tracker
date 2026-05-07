import { ArrowRight } from "lucide-react";
import type { PublicRelationships } from "@/lib/schemas";

export function RelationshipList({
  relationships,
  highlightId,
  onHover
}: {
  relationships: PublicRelationships;
  highlightId: string | null;
  onHover: (id: string | null) => void;
}) {
  const labels = new Map(relationships.nodes.map((node) => [node.id, node.label]));
  const sorted = [...relationships.edges].sort((a, b) => b.similarity_score - a.similarity_score);

  return (
    <aside className="ranked-panel">
      <div className="panel-heading">
        <span>Ranked relationships</span>
        <code>{relationships.edges.length} edges</code>
      </div>
      {sorted.length ? (
        <ul className="relationship-list">
          {sorted.map((edge) => {
            const active = !highlightId || highlightId === edge.source || highlightId === edge.target;
            return (
              <li
                key={`${edge.source}-${edge.target}`}
                className={active ? "" : "dimmed"}
                onMouseEnter={() => onHover(edge.source)}
                onMouseLeave={() => onHover(null)}
              >
                <div className="edge-title">
                  <span>{labels.get(edge.source) ?? edge.source}</span>
                  <ArrowRight size={13} />
                  <span>{labels.get(edge.target) ?? edge.target}</span>
                  <code>{edge.similarity_score.toFixed(2)}</code>
                </div>
                <div className="topic-row">
                  {edge.shared_topics.map((topic) => (
                    <span className="topic-chip muted-chip" key={topic.slug}>
                      {topic.label}
                    </span>
                  ))}
                </div>
                <p>{edge.explanation}</p>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty-panel-copy">No relationship edges yet. More enriched videos will make the graph denser.</p>
      )}
    </aside>
  );
}
