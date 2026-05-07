create extension if not exists pgcrypto;

create table if not exists pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  trigger_type text not null default 'manual',
  status text not null check (status in ('running', 'success', 'failed', 'partial')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  provider_name text,
  provider_model text,
  videos_seen integer not null default 0,
  videos_processed integer not null default 0,
  videos_failed integer not null default 0,
  estimated_cost_usd numeric(10, 4) not null default 0,
  error_summary text,
  created_at timestamptz not null default now()
);

create table if not exists channels (
  id uuid primary key default gen_random_uuid(),
  youtube_channel_id text unique not null,
  title text not null,
  handle text,
  description text,
  url text not null,
  rss_url text not null,
  thumbnail_url text,
  language text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_seen_at timestamptz
);

create table if not exists videos (
  id uuid primary key default gen_random_uuid(),
  youtube_video_id text unique not null,
  channel_id uuid not null references channels(id) on delete cascade,
  title text not null,
  description text,
  url text not null,
  thumbnail_url text,
  published_at timestamptz not null,
  duration_seconds integer,
  discovered_at timestamptz not null default now(),
  transcript_status text not null default 'pending' check (transcript_status in ('pending', 'captions_found', 'fallback_required', 'unavailable', 'ready', 'failed', 'skipped')),
  enrichment_status text not null default 'pending' check (enrichment_status in ('pending', 'ready', 'failed', 'skipped')),
  availability_status text not null default 'active' check (availability_status in ('active', 'deleted', 'private', 'unknown')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists transcripts (
  id uuid primary key default gen_random_uuid(),
  video_id uuid unique not null references videos(id) on delete cascade,
  source text not null check (source in ('youtube_captions', 'whisper', 'vertex_audio', 'manual', 'fixture')),
  language text,
  text text not null,
  text_hash text not null,
  quality_score numeric(5, 4),
  acquired_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists transcript_segments (
  id uuid primary key default gen_random_uuid(),
  transcript_id uuid not null references transcripts(id) on delete cascade,
  segment_index integer not null,
  start_seconds numeric(10, 3),
  end_seconds numeric(10, 3),
  text text not null,
  token_count integer,
  unique (transcript_id, segment_index)
);

create table if not exists enrichments (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  transcript_id uuid not null references transcripts(id) on delete cascade,
  provider_name text not null,
  provider_model text not null,
  prompt_version text not null,
  input_hash text not null,
  primary_speaker text,
  summary text not null,
  content_type text not null check (content_type in ('news', 'tutorial', 'benchmark', 'opinion', 'demo', 'interview', 'research', 'unknown')),
  stance text,
  confidence_score numeric(5, 4),
  raw_response jsonb not null,
  created_at timestamptz not null default now(),
  unique (video_id, provider_name, provider_model, prompt_version, input_hash)
);

create table if not exists speakers (
  id uuid primary key default gen_random_uuid(),
  canonical_name text unique not null,
  speaker_type text check (speaker_type in ('host', 'guest', 'company', 'unknown')),
  created_at timestamptz not null default now()
);

create table if not exists video_speakers (
  video_id uuid not null references videos(id) on delete cascade,
  speaker_id uuid not null references speakers(id) on delete cascade,
  role text not null check (role in ('primary', 'guest', 'mentioned')),
  confidence_score numeric(5, 4),
  primary key (video_id, speaker_id, role)
);

create table if not exists topics (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  label text not null,
  description text,
  parent_topic_id uuid references topics(id),
  created_at timestamptz not null default now()
);

create table if not exists video_topics (
  video_id uuid not null references videos(id) on delete cascade,
  topic_id uuid not null references topics(id) on delete cascade,
  relevance_score numeric(5, 4) not null,
  evidence_count integer not null default 0,
  source_enrichment_id uuid references enrichments(id) on delete set null,
  primary key (video_id, topic_id)
);

create table if not exists evidence_snippets (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  enrichment_id uuid not null references enrichments(id) on delete cascade,
  topic_id uuid references topics(id) on delete set null,
  transcript_segment_id uuid references transcript_segments(id) on delete set null,
  field_name text not null,
  quote text not null,
  start_seconds numeric(10, 3),
  end_seconds numeric(10, 3),
  created_at timestamptz not null default now()
);

create table if not exists channel_topic_stats (
  channel_id uuid not null references channels(id) on delete cascade,
  topic_id uuid not null references topics(id) on delete cascade,
  video_count integer not null,
  average_relevance numeric(5, 4) not null,
  latest_video_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (channel_id, topic_id)
);

create table if not exists channel_relationships (
  id uuid primary key default gen_random_uuid(),
  source_channel_id uuid not null references channels(id) on delete cascade,
  target_channel_id uuid not null references channels(id) on delete cascade,
  similarity_score numeric(5, 4) not null,
  method text not null check (method in ('topic_overlap', 'embedding_similarity', 'hybrid')),
  shared_topics jsonb not null,
  explanation text not null,
  computed_at timestamptz not null default now(),
  unique (source_channel_id, target_channel_id, method),
  check (source_channel_id <> target_channel_id)
);

create table if not exists public_snapshots (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references pipeline_runs(id) on delete set null,
  name text not null,
  path text not null,
  content_hash text not null,
  generated_at timestamptz not null default now()
);

create index if not exists idx_videos_channel_published on videos(channel_id, published_at desc);
create index if not exists idx_transcripts_text_hash on transcripts(text_hash);
create index if not exists idx_enrichments_dedupe on enrichments(video_id, provider_name, provider_model, prompt_version, input_hash);
create index if not exists idx_video_topics_topic_score on video_topics(topic_id, relevance_score desc);
create index if not exists idx_channel_topic_stats_channel_score on channel_topic_stats(channel_id, average_relevance desc);
create index if not exists idx_channel_relationships_source_score on channel_relationships(source_channel_id, similarity_score desc);
create index if not exists idx_pipeline_runs_started_at on pipeline_runs(started_at desc);
