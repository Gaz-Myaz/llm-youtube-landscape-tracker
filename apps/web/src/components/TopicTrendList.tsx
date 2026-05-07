import type { PublicVideo } from "@/lib/schemas";

export function TopicTrendList({ videos }: { videos: PublicVideo[] }) {
  const topics = new Map<string, { label: string; count: number; score: number }>();
  for (const video of videos) {
    for (const topic of video.topics) {
      const current = topics.get(topic.slug) ?? { label: topic.label, count: 0, score: 0 };
      current.count += 1;
      current.score += topic.relevance_score;
      topics.set(topic.slug, current);
    }
  }
  const ranked = Array.from(topics.entries())
    .map(([slug, value]) => ({ slug, ...value }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);
  const max = Math.max(1, ...ranked.map((topic) => topic.score));

  return (
    <div className="topic-trend-panel">
      <div className="panel-heading">
        <span>Top topics</span>
        <code>{topics.size} unique</code>
      </div>
      <ul>
        {ranked.map((topic, index) => (
          <li key={topic.slug}>
            <code>{index + 1}</code>
            <div>
              <span>{topic.label}</span>
              <div className="topic-bar">
                <span style={{ width: `${(topic.score / max) * 100}%` }} />
              </div>
            </div>
            <strong>{topic.count}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}