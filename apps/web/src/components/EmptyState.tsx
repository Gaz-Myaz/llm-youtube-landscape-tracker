import { Inbox, type LucideIcon } from "lucide-react";

export function EmptyState({
  title,
  description,
  Icon = Inbox
}: {
  title: string;
  description?: string;
  Icon?: LucideIcon;
}) {
  return (
    <div className="empty-state">
      <div>
        <Icon size={18} />
      </div>
      <strong>{title}</strong>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
