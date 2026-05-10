# LLM YouTube Landscape Tracker

A transcript-grounded dashboard for tracking how selected YouTube channels cover LLMs, AI agents, coding assistants, model releases, benchmarks, safety, and related developer workflows.

The project has two parts:

- A Python worker that discovers videos from YouTube RSS feeds, fetches captions, runs structured enrichment, and exports JSON snapshots.
- A Next.js dashboard that reads those snapshots and renders video summaries, evidence snippets, channel cards, and a relationship graph.

Live dashboard:

```text
https://gaz-myaz.github.io/llm-youtube-landscape-tracker/
```

## What The Pipeline Does

1. Loads tracked channels from `infra/db/seed_channels.sql`.
2. Reads recent videos from each channel's RSS feed.
3. Fetches captions through cache, `youtube-transcript-api`, and `yt-dlp`.
4. Sends caption-backed candidates to the configured enrichment provider.
5. Validates provider output against the shared insight schema.
6. Falls back to deterministic analysis for a single video if that video's provider call fails.
7. Filters out videos without a strong LLM-landscape signal.
8. Ranks published videos and computes channel relationships from extracted topics.
9. Writes validated public snapshots into `apps/web/public/data`.
10. Deploys the dashboard to GitHub Pages.

Scheduled production runs use Gemini by default. Manual runs can choose `mock`, `gemini`, `openai`, or `anthropic`.

## Repository Layout

- `services/worker`: Python ingestion, captions, enrichment, ranking, relationships, and snapshot export.
- `apps/web`: Next.js dashboard.
- `contracts`: JSON Schemas for exported public snapshots.
- `infra/db`: PostgreSQL schema and seeded channel configuration.
- `.github/workflows/update-landscape-data.yml`: scheduled/manual data refresh.
- `.github/workflows/deploy-pages.yml`: static GitHub Pages deployment.
- `docker-compose.yml`: local `db`, `worker`, and `web` services.

## Quick Start

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd services\worker
pip install -e .[dev]
pytest
```

Generate mock snapshots:

```powershell
python -m llm_landscape.main mock-export --output-dir ..\..\apps\web\public\data
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

Generate real caption-backed snapshots with deterministic local analysis:

```powershell
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --max-channels 10 --videos-per-channel 5 --max-videos 50
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

Generate real caption-backed snapshots with Gemini:

```powershell
$env:WORKER_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "..."
$env:GEMINI_MODEL = "gemini-2.5-flash"
$env:MAX_PROVIDER_CALLS_PER_RUN = "50"
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --max-channels 10 --videos-per-channel 5 --max-videos 50
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

Run the web app locally:

```powershell
cd apps\web
npm install
npm run dev
```

Production build check:

```powershell
cd apps\web
npm run build
```

## Snapshot Files

The worker writes these public read models:

- `videos.json`: video metadata, summaries, topics, evidence, and transcript text.
- `channels.json`: channel cards, latest activity, and top topics.
- `relationships.json`: graph nodes and topic-overlap edges.
- `run-metadata.json`: provider/model, counts, token usage, estimated cost, fallback counts, status, and content hashes.

Check `apps/web/public/data/run-metadata.json` to understand the currently published data:

- `provider: "gemini"`, `"openai"`, or `"anthropic"`: provider-backed structured extraction was used.
- `provider: "deterministic"`: real caption-backed local analysis was used.
- `provider: "mock"`: demo/test fixtures were exported.

## Configuration

Copy `.env.example` to `.env` for local overrides. The worker reads process environment variables; never commit real API keys.

Important settings:

- `WORKER_PROVIDER`: `mock`, `gemini`, `openai`, or `anthropic`. Default: `mock`.
- `GEMINI_API_KEY`: preferred key for `WORKER_PROVIDER=gemini`. `GOOGLE_API_KEY` also works.
- `GEMINI_MODEL`: Gemini model. Default: `gemini-2.5-flash`.
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`: OpenAI-compatible provider settings.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`: Anthropic provider settings.
- `MAX_PROVIDER_CALLS_PER_RUN`: hard cap on paid provider calls per run.
- `MAX_CHANNELS_PER_RUN`: maximum seeded channels to inspect in one run.
- `VIDEOS_PER_CHANNEL`: RSS entries to inspect per seeded channel.
- `MAX_VIDEOS_PER_RUN`: maximum candidate videos to attempt in one run.
- `TRANSCRIPT_PROVIDERS`: transcript provider order. Default: `youtube_transcript_api,yt_dlp,whisper` locally and `yt_dlp,youtube_transcript_api,whisper` in CI.
- `TRANSCRIPT_REQUEST_DELAY_SECONDS`: delay between uncached transcript requests.
- `YT_DLP_COOKIES_PATH`: path to a Netscape-format YouTube cookies file for `yt-dlp`.
- `YT_DLP_COOKIES_FROM_BROWSER`: optional local-only browser cookie source such as `chrome:Default`.
- `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`: local audio-transcription fallback settings. Defaults: `tiny`, `cpu`, `int8`.
- `TRANSCRIPT_CACHE_DIR`: local transcript cache directory.
- `SNAPSHOT_OUTPUT_DIR`: snapshot output directory.
- `CONTRACTS_DIR`: JSON Schema contract directory.
- `SEED_CHANNELS_PATH`: seeded channel SQL file, or use `--channels-csv` for a custom channel list.

Cost estimate settings:

- `GEMINI_INPUT_USD_PER_1M_TOKENS`
- `GEMINI_OUTPUT_USD_PER_1M_TOKENS`
- `OPENAI_INPUT_USD_PER_1M_TOKENS`
- `OPENAI_OUTPUT_USD_PER_1M_TOKENS`
- `ANTHROPIC_INPUT_USD_PER_1M_TOKENS`
- `ANTHROPIC_OUTPUT_USD_PER_1M_TOKENS`

`estimated_cost_usd` is calculated from provider usage fields and configured rates. The provider billing dashboard remains the source of truth for invoices, free-tier behavior, rounding, and taxes.

## Provider Fallbacks And Data Quality

LLM-backed runs use Gemini/OpenAI/Anthropic for transcript-grounded fields such as speaker, summary, content type, stance, topics, evidence snippets, and confidence score.

If one provider call or schema validation step fails, the worker uses deterministic analysis for that video only. The run is marked `partial`, and `run-metadata.json` records:

- `provider_call_count`
- `provider_success_count`
- `provider_fallback_count`
- `provider_fallback_reasons`

If caption providers cannot return usable subtitles, the worker now falls back to local Whisper transcription from downloaded audio before it gives up on that video. If credentials are missing, the GitHub Actions run fails before export. If `MAX_PROVIDER_CALLS_PER_RUN` is lower than the number of caption-backed candidates, candidates beyond the cap are skipped and recorded in `error_summary`.

The deterministic analyzer remains useful for local runs and fallback cases, but it is less nuanced than provider-backed extraction.

## GitHub Actions

There are four workflows:

- `worker-check.yml`: runs worker tests and validates checked-in snapshots.
- `web-check.yml`: installs the web app, type-checks it, and runs `next build`.
- `update-landscape-data.yml`: refreshes captions and snapshots on schedule or manual dispatch.
- `deploy-pages.yml`: builds a static export and deploys the dashboard to GitHub Pages.

Scheduled data refreshes:

- run every 12 hours;
- use Gemini by default;
- inspect up to ten seeded channels per run;
- inspect five recent RSS entries per selected channel;
- cap each run at 50 candidate videos and 50 provider calls;
- prefer authenticated `yt_dlp` caption fetching in CI, with Whisper audio transcription as the last fallback;
- commit changed snapshot files after validation.

Required scheduled secrets:

- `YT_DLP_COOKIES`: Netscape-format cookies from a signed-in YouTube browser session.
- `GEMINI_API_KEY`: Gemini key for scheduled provider-backed extraction.

Manual LLM runs need the matching provider secret: `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`.

Alerting behavior:

- Cookie validation failures open `Refresh YT_DLP_COOKIES for scheduled data updates`.
- Degraded successful refreshes open or comment on `Investigate degraded landscape data refresh`.
- Non-cookie data refresh failures open or comment on `Investigate failed landscape data refresh`.
- Failed dashboard builds or deploys open or comment on `Investigate failed dashboard Pages deploy`.

## YouTube Cookie Check

For a local cookie check, do not treat a printed video ID as proof that cookies are valid. `yt-dlp` can print an ID for a public video while still warning that YouTube rejected the session.

Use this instead:

```powershell
$output = & .\.venv\Scripts\python.exe -m yt_dlp --ignore-config --cookies .\www.youtube.com_cookies.txt --skip-download --ignore-no-formats-error --list-subs "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | Out-String
$output
if ($output -match 'provided YouTube account cookies are no longer valid|Sign in to confirm you''re not a bot|Use --cookies-from-browser or --cookies for the authentication') {
    throw 'YouTube rejected the cookies. Re-export them from a freshly signed-in browser session.'
}
```

Warnings about missing video formats, a missing JavaScript runtime, or missing `ffmpeg` are not authentication failures by themselves. The blocking warnings are the YouTube auth messages above.

For YouTube cookies, a reliable export flow is:

1. Open a fresh private/incognito browser window.
2. Sign into YouTube.
3. Open `https://www.youtube.com/robots.txt` in that same session.
4. Export `youtube.com` cookies with a Netscape-cookie extension.
5. Close the private window immediately.

If the exported cookie file contains only the three-line Netscape header and no cookie rows, treat it as invalid.

## Known Gaps

- PostgreSQL schema exists, but `real-export` currently writes snapshots directly instead of using Postgres as the canonical source of truth.
- Whisper/audio transcription fallback is not implemented yet. Subtitle fallback through `yt-dlp` is implemented.
- Provider cost is estimated from usage fields and configured rates, not reconciled against billing invoices.
- Relationship scores use topic overlap, not embeddings or semantic similarity.

PostgreSQL is the next useful architecture step if the project needs durable run history, enrichment caching, evaluation records, and stronger resumability. Whisper/audio transcription fallback is worth adding only if caption miss-rate becomes a meaningful coverage problem.