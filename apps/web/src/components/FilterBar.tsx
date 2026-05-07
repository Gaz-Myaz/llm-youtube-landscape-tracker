import { Search, X } from "lucide-react";

export type SortKey = "date" | "channel" | "relevance";

export interface FilterState {
  query: string;
  channelId: string;
  topicSlug: string;
  contentType: string;
  sort: SortKey;
}

interface Option {
  value: string;
  label: string;
}

export function FilterBar({
  state,
  onChange,
  channels,
  topics,
  contentTypes,
  resultCount,
  totalCount
}: {
  state: FilterState;
  onChange: (next: FilterState) => void;
  channels: Option[];
  topics: Option[];
  contentTypes: Option[];
  resultCount: number;
  totalCount: number;
}) {
  const set = <K extends keyof FilterState>(key: K, value: FilterState[K]) =>
    onChange({ ...state, [key]: value });
  const hasFilters = state.query || state.channelId || state.topicSlug || state.contentType;

  return (
    <div className="filter-panel">
      <label className="search-box">
        <Search size={15} />
        <input
          value={state.query}
          onChange={(event) => set("query", event.target.value)}
          placeholder="Search title, speaker, summary, evidence"
        />
      </label>
      <div className="filter-controls">
        <Select label="Channel" value={state.channelId} onChange={(value) => set("channelId", value)} options={channels} />
        <Select label="Topic" value={state.topicSlug} onChange={(value) => set("topicSlug", value)} options={topics} />
        <Select label="Type" value={state.contentType} onChange={(value) => set("contentType", value)} options={contentTypes} />
        <Select
          label="Sort"
          value={state.sort}
          onChange={(value) => set("sort", value as SortKey)}
          options={[
            { value: "date", label: "Newest" },
            { value: "channel", label: "Channel" },
            { value: "relevance", label: "Relevance" }
          ]}
          allowEmpty={false}
        />
        {hasFilters ? (
          <button
            className="clear-button"
            onClick={() =>
              onChange({ query: "", channelId: "", topicSlug: "", contentType: "", sort: state.sort })
            }
            type="button"
          >
            <X size={13} />
            Clear
          </button>
        ) : null}
      </div>
      <span className="result-count">{resultCount} / {totalCount}</span>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  allowEmpty = true
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  allowEmpty?: boolean;
}) {
  return (
    <label className="select-shell">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {allowEmpty ? <option value="">All</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}