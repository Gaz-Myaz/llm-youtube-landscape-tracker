import { z } from "zod";

const topicSchema = z.object({
  slug: z.string(),
  label: z.string(),
  relevance_score: z.number()
});

const evidenceSchema = z.object({
  field_name: z.string(),
  topic_slug: z.string().nullable().optional(),
  quote: z.string(),
  start_seconds: z.number().nullable().optional(),
  end_seconds: z.number().nullable().optional(),
  timestamp_url: z.string().nullable().optional()
});

export const publicVideosSchema = z.object({
  schema_version: z.literal("1.0"),
  generated_at: z.string(),
  videos: z.array(
    z.object({
      youtube_video_id: z.string(),
      title: z.string(),
      url: z.string(),
      thumbnail_url: z.string().nullable().optional(),
      published_at: z.string(),
      channel: z.object({
        youtube_channel_id: z.string(),
        title: z.string(),
        url: z.string()
      }),
      primary_speaker: z.string().nullable(),
      summary: z.string(),
      content_type: z.string(),
      topics: z.array(topicSchema),
      evidence: z.array(evidenceSchema),
      transcript_status: z.string(),
      enrichment_status: z.string()
    })
  )
});

export const publicChannelsSchema = z.object({
  schema_version: z.literal("1.0"),
  generated_at: z.string(),
  channels: z.array(
    z.object({
      youtube_channel_id: z.string(),
      title: z.string(),
      handle: z.string().nullable().optional(),
      description: z.string().nullable().optional(),
      url: z.string(),
      thumbnail_url: z.string().nullable().optional(),
      video_count: z.number(),
      latest_video_at: z.string().nullable(),
      top_topics: z.array(
        z.object({
          slug: z.string(),
          label: z.string(),
          score: z.number()
        })
      )
    })
  )
});

export const publicRelationshipsSchema = z.object({
  schema_version: z.literal("1.0"),
  generated_at: z.string(),
  nodes: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      video_count: z.number(),
      top_topics: z.array(z.string())
    })
  ),
  edges: z.array(
    z.object({
      source: z.string(),
      target: z.string(),
      similarity_score: z.number(),
      method: z.string(),
      shared_topics: z.array(
        z.object({
          slug: z.string(),
          label: z.string(),
          score: z.number()
        })
      ),
      explanation: z.string()
    })
  )
});

export const runMetadataSchema = z.object({
  schema_version: z.literal("1.0"),
  last_successful_run_at: z.string(),
  status: z.enum(["success", "failed", "partial", "stale"]),
  provider: z.string(),
  model: z.string(),
  videos_seen: z.number(),
  videos_processed: z.number(),
  videos_failed: z.number(),
  estimated_cost_usd: z.number(),
  error_summary: z.string().nullable().optional(),
  content_hashes: z.record(z.string())
});

export type PublicVideos = z.infer<typeof publicVideosSchema>;
export type PublicVideo = PublicVideos["videos"][number];
export type PublicChannels = z.infer<typeof publicChannelsSchema>;
export type PublicChannel = PublicChannels["channels"][number];
export type PublicRelationships = z.infer<typeof publicRelationshipsSchema>;
export type RunMetadata = z.infer<typeof runMetadataSchema>;
