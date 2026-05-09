# Report: LLM YouTube Landscape Tracker

Date: May 9, 2026

## 1. Project Goal

The LLM YouTube Landscape Tracker is a prototype for monitoring selected YouTube channels that cover AI, LLMs, coding assistants, model releases, and related developer workflows.

The project answers four practical questions:

- Which recent videos are relevant to the LLM landscape?
- What topics does each video cover?
- What transcript evidence supports those topic labels?
- Which channels overlap based on shared extracted topics?

The current implementation focuses on a real, subtitle-backed pipeline with provider-backed structured extraction in production. Scheduled refreshes use Gemini (`gemini-2.5-flash`) when `GEMINI_API_KEY` is configured, while a deterministic local mode remains available for tests, demos, and no-credential fallback runs.

## 2. Current Implementation Status

Implemented:

- Python worker package in `services/worker`.
- Next.js dashboard in `apps/web`.
- Shared JSON contracts in `contracts`.
- Seed channel definitions in `infra/db/seed_channels.sql`.
- Real YouTube RSS discovery.
- Real YouTube caption fetching.
- Configurable transcript provider chain: cache, `youtube-transcript-api`, then `yt-dlp` fallback.
- Local transcript caching.
- Deterministic topic extraction from subtitles for local/mock fallback runs.
- Deterministic filtering of videos outside the LLM landscape.
- Deterministic fallback ranking for published videos.
- Deterministic content type classification.
- Provider-backed structured extraction through Gemini, OpenAI-compatible chat completions, and Anthropic Messages.
- Runtime JSON Schema validation for provider responses, with strict schema transport for OpenAI and schema-first prompt/runtime validation for Gemini and Anthropic.
- Relationship graph data based on shared topic overlap.
- Full subtitle text available per published video in the dashboard evidence drawer.
- Public JSON snapshot generation.
- Snapshot schema validation.
- Docker Compose wiring for `db`, `worker`, and `web`.
- GitHub Actions workflow for scheduled Gemini snapshot updates and automatic GitHub Pages deployment.

Not implemented yet:

- Automatic fallback from a failing LLM provider call to deterministic analysis inside the same run.
- Token usage and real cost accounting in `run-metadata.json`.
- Whisper/audio transcription fallback when no subtitle provider can return captions.
- PostgreSQL as the active canonical source of truth. The schema exists, but `real-export` currently writes snapshots directly.
- Full production alerting beyond cookie-expiry issue creation in GitHub Actions.

## 3. System Architecture

The project is split into two main services.

### Python Worker

The worker owns data collection and analysis:

1. Load tracked channels from seed SQL or a CSV file.
2. Fetch each channel's YouTube RSS feed.
3. Attempt to fetch captions for candidate videos with the configured provider chain.
4. Cache successful transcripts under `TRANSCRIPT_CACHE_DIR`.
5. Run the configured enrichment provider: Gemini/OpenAI/Anthropic for LLM-backed runs, or the deterministic analyzer when `WORKER_PROVIDER=mock`.
6. Validate provider responses against the shared insight schema before snapshot export.
7. Filter out caption-backed videos that do not match LLM landscape rules.
8. Rank published videos with deterministic topic/evidence signals.
9. Build relationship edges from shared topics.
10. Export validated JSON snapshots.

Main command:

```powershell
cd services\worker
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --videos-per-channel 3 --max-videos 15
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

Production-style Gemini run:

```powershell
$env:WORKER_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "..."
$env:GEMINI_MODEL = "gemini-2.5-flash"
$env:MAX_PROVIDER_CALLS_PER_RUN = "30"
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --videos-per-channel 2 --max-videos 30
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

### Next.js Web App

The web app owns the public experience:

- Video table.
- Topic filters.
- Channel summary cards.
- Transcript-backed evidence snippets.
- Channel relationship graph.
- Run metadata display.

The app reads these files from `apps/web/public/data`:

- `videos.json`
- `channels.json`
- `relationships.json`
- `run-metadata.json`

The homepage is configured with `dynamic = "force-dynamic"`, so updated snapshot files are read at request time in the local dev server.

## 4. Data Pipeline Details

### Channel Discovery

The default channel list is stored in `infra/db/seed_channels.sql`. The current seed includes channels such as Two Minute Papers, Lex Fridman, Fireship, ThePrimeTime, and freeCodeCamp.org.

During implementation, two seed IDs were corrected because they pointed to the wrong RSS feeds. This matters because incorrect channel IDs can make real videos appear under the wrong channel label.

### Caption Fetching

Captions are fetched through a provider chain. The default order is:

1. Local transcript cache.
2. `youtube-transcript-api`.
3. `yt-dlp` subtitle metadata and subtitle file fetch.

The `youtube-transcript-api` implementation supports both older and newer versions of that package:

- older style: `YouTubeTranscriptApi.get_transcript(...)`
- newer style: `YouTubeTranscriptApi().fetch(...)`

Successful captions are written to a local cache. This reduces repeated YouTube requests and makes later exports more stable. The provider order is controlled by `TRANSCRIPT_PROVIDERS`, and request pacing is controlled by `TRANSCRIPT_REQUEST_DELAY_SECONDS`.

This is a subtitle fallback, not an audio transcription fallback. If YouTube has no subtitles and `yt-dlp` cannot expose a subtitle track, the current worker still skips the video.

### LLM-Backed Extraction and Deterministic Mode

Scheduled production runs now call Gemini for structured extraction. For each caption-backed candidate up to `MAX_PROVIDER_CALLS_PER_RUN`, the worker sends video metadata, the controlled topic taxonomy, the required JSON Schema, and a transcript excerpt to the provider. The provider returns primary speaker, summary, content type, stance, topics, evidence snippets, and confidence score. The worker validates the response before it can be published.

The deterministic analyzer is still available when `WORKER_PROVIDER=mock`. It does not call an LLM. It uses exact token and phrase matching for topics such as:

- AI Agents
- Coding Assistants
- Open Source Models
- Local Inference
- RAG
- Multimodal
- Fine Tuning
- Safety and Alignment
- Enterprise Adoption
- Evaluation
- Benchmarks
- Model Releases

The deterministic analyzer also selects evidence snippets from subtitle segments and creates short summaries using transcript-derived signals.

Content type is also rule-based. The current type dictionary looks for signals such as tutorial/course/build, benchmark/leaderboard/comparison, interview/podcast, paper/research/study, demo/launch/release, analysis/explained/changed/disrupted, and opinion/reaction/take. If a video has LLM topic signals but no narrower type signal, it falls back to `analysis` instead of `unknown`.

### Relevance Filtering

Not every captioned video from a tracked channel is an LLM landscape video. The real export filters out videos with weak or missing LLM signals so the dashboard does not pretend unrelated content is relevant.

This is intentionally conservative. It is better for the prototype to skip weak matches than to publish noisy relationships.

### Fallback Ranking and Relationships

The current ordering and graph are also non-LLM. Published videos are ranked by deterministic topic strength, average top-topic score, topic diversity, evidence coverage, and recency as a tie-breaker. Channel relationships are built from shared topic labels and their extracted scores.

This gives the project an explicit fallback mode when running with `WORKER_PROVIDER=mock`. It is not an automatic per-call fallback inside a Gemini/OpenAI/Anthropic run: if the configured LLM provider errors or returns invalid schema data, the current run fails rather than silently mixing deterministic and provider-backed enrichments. If the provider-call cap is lower than the number of caption-backed candidates, extra candidates are skipped and recorded in run metadata.

## 5. Current Data Reality

The checked-in dashboard snapshots are generated artifacts from the latest successful export. The source can be verified in:

```text
apps/web/public/data/run-metadata.json
```

If it says:

```json
"provider": "mock"
```

then the dashboard is showing mock snapshots.

If it says:

```json
"provider": "deterministic"
```

then the dashboard was generated by the real subtitle-backed pipeline.

If it says:

```json
"provider": "gemini"
```

then the dashboard was generated by the real subtitle-backed pipeline with Gemini structured extraction. The current live metadata is:

```json
{
	"provider": "gemini",
	"model": "gemini-2.5-flash",
	"status": "success",
	"videos_seen": 28,
	"videos_processed": 18,
	"videos_failed": 0,
	"last_successful_run_at": "2026-05-09T14:41:28Z"
}
```

For that run, the provider-call cap was 30 and there were 28 caption-backed candidates, so the worker attempted Gemini extraction for the 28 candidates. It then published 18 videos and filtered 10 caption-backed videos as outside the configured LLM landscape rules.

`estimated_cost_usd` is currently always written as `0` by the snapshot builder. That value is a placeholder, not proof that no Gemini requests happened. Token accounting and provider-cost estimation are not implemented yet, so spend must be verified in the Google AI/Gemini billing dashboard.

During local testing, the real export successfully produced caption-backed snapshots. After repeated requests, YouTube temporarily blocked direct transcript fetches from the current IP. The worker now reports compact skip reasons, uses the transcript cache, throttles uncached requests, and can fall back to `yt-dlp` subtitle extraction.

## 6. Validation Performed

Worker tests pass:

```text
31 passed
```

The test suite covers:

- loading seed channels from SQL
- deterministic topic extraction
- avoiding substring false positives such as `rag` inside unrelated words
- landscape relevance filtering
- ISO date normalization
- transcript cache behavior
- fallback from `youtube-transcript-api` to `yt-dlp`
- relationship scoring
- deterministic fallback ranking
- snapshot generation
- Gemini/OpenAI-compatible provider creation
- Anthropic provider creation
- provider JSON parsing and schema validation
- schema-tolerant provider response normalization for optional evidence fields and overlong topic/evidence arrays

Snapshot validation passes for the current public data files:

```text
Validated snapshots in apps/web/public/data
```

VS Code workspace diagnostics were also checked. The active project files do not report errors. One reported TypeScript diagnostic came from the ignored `llm-insight-map-main` reference import, not from the active Next.js app.

## 7. Known Limitations

- Gemini-backed extraction is active for scheduled production runs, but deterministic mode is still less nuanced when used locally or as `WORKER_PROVIDER=mock`.
- Topic matching depends on curated phrase rules.
- `estimated_cost_usd` is not real cost accounting yet.
- Gemini/OpenAI/Anthropic runs do not automatically fall back to deterministic analysis if a provider call fails.
- YouTube caption access can be rate-limited or blocked, though cache, delay, and `yt-dlp` fallback reduce this risk.
- Videos without any subtitle track are skipped because audio transcription is not implemented yet.
- The current export path writes snapshots directly rather than persisting to PostgreSQL first.
- Video ranking and relationship scores are deterministic calculations based on topic/evidence signals, not embeddings or semantic similarity.

## 8. Evaluation Plan

The next evaluation pass should use 20 to 30 manually reviewed videos across the seed channels.

Each reviewed video should record:

- expected relevant or not relevant decision
- expected top topics
- evidence snippet quality
- summary faithfulness
- channel attribution correctness

Suggested metrics:

- transcript fetch success rate
- relevance filtering precision
- topic label agreement
- evidence usefulness
- relationship graph sanity
- successful scheduled run rate

## 9. Recommended Next Steps

1. Add provider usage accounting to record attempted calls, token counts when available, and estimated cost in `run-metadata.json`.
2. Decide whether failed LLM provider calls should fail the run, retry, or fall back to deterministic analysis with an explicit mixed-provider status.
3. Add fallback audio transcription for videos without usable subtitle tracks.
4. Move the real export path through PostgreSQL for durable canonical storage.
5. Add a small review dataset and compare Gemini outputs against manual labels.
6. Evaluate whether embeddings would improve relationship scoring beyond topic overlap.

## 10. Summary

The project now has a real backend path: RSS discovery, subtitle provider fallback, Gemini-backed structured extraction, filtering, deterministic ranking, relationship scoring, and validated snapshot export. It is not pretending mock data is real, and it is explicit about current limitations.

That makes the current version a solid prototype foundation: the data path exists, the dashboard consumes stable contracts, the live site publishes provider-backed data, and the remaining work is quality improvement, cost observability, and durability rather than basic scaffolding.
