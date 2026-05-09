# LLM YouTube Landscape Tracker

A prototype system for tracking LLM and AI coverage across selected YouTube channels. It has a Python worker that discovers videos from channel RSS feeds, fetches YouTube captions, derives transcript-backed topics with a deterministic analyzer or provider-backed structured extraction, and exports JSON snapshots for a Next.js dashboard.

The project is intentionally split into a data worker and a web app so the ingestion pipeline, data contracts, and presentation layer can evolve independently.

## Current Status

Implemented now:

- Real YouTube RSS discovery from seeded channel IDs in `infra/db/seed_channels.sql`, including independent AI labs, research explainers, developer tooling channels, and applied LLM education sources.
- Real YouTube caption fetching through `youtube-transcript-api`.
- `yt-dlp` subtitle fallback when the primary transcript API is blocked or unavailable.
- Local transcript caching via `TRANSCRIPT_CACHE_DIR` to reduce repeated YouTube requests.
- Deterministic, non-LLM topic extraction from subtitle text for local/mock fallback runs.
- Deterministic relevance filtering so unrelated captioned videos are skipped while single-topic LLM/model-release signals are still retained.
- Deterministic fallback ranking that orders published videos by topic strength, evidence coverage, and recency.
- Deterministic content type classification using a small keyword dictionary for tutorial, benchmark, interview, research, demo, analysis, and opinion videos.
- Production structured extraction for transcript-backed topics, summaries, content types, stance, and evidence through Google Gemini, plus manual adapters for OpenAI-compatible providers and Anthropic.
- Relationship scoring based on shared extracted topics.
- Full fetched subtitle text is included in the public video snapshot for audit/review in the dashboard.
- JSON snapshot export and schema validation.
- Next.js dashboard reading `apps/web/public/data/*.json` dynamically.
- Docker Compose and GitHub Actions paths for scheduled snapshot updates.

Still scaffolded or planned:

- PostgreSQL schema exists, but the current `real-export` path writes public snapshots directly instead of using Postgres as the canonical store.
- Vertex AI provider scaffolding exists, while the implemented production-ready LLM adapters cover Gemini, OpenAI-compatible chat completions, and Anthropic Messages.
- Whisper/audio transcription fallback is not implemented yet. Subtitle fallback through `yt-dlp` is implemented.
- The checked-in dashboard snapshots depend on the last successful export. Check `apps/web/public/data/run-metadata.json`: `provider: "gemini"`, `"openai"`, or `"anthropic"` means provider-backed structured extraction was used; `provider: "deterministic"` means the real caption-backed non-LLM path was used; `provider: "mock"` means demo/test fixtures were exported.

## Architecture

- `services/worker`: Python ingestion, transcript fetching, deterministic analysis, relationship scoring, and snapshot export.
- `apps/web`: Next.js 15 dashboard with filters, evidence snippets, channel summaries, and a relationship graph.
- `contracts`: JSON Schemas used to validate exported public snapshots.
- `infra/db`: PostgreSQL schema and seeded channel configuration for local and future canonical storage.
- `.github/workflows/update-landscape-data.yml`: scheduled/manual snapshot update workflow.
- `docker-compose.yml`: local `db`, `worker`, and `web` services.

## Worker Setup

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

Generate real subtitle-backed snapshots without an LLM:

```powershell
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --videos-per-channel 3 --max-videos 15
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

Generate real subtitle-backed snapshots with Gemini:

```powershell
$env:WORKER_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "..."
$env:GEMINI_MODEL = "gemini-2.5-flash"
$env:MAX_PROVIDER_CALLS_PER_RUN = "5"
python -m llm_landscape.main real-export --output-dir ..\..\apps\web\public\data --videos-per-channel 2 --max-videos 5
python -m llm_landscape.main validate-snapshots --data-dir ..\..\apps\web\public\data
```

The real export always uses channel RSS feeds, fetched captions, and the transcript cache. The enrichment step depends on `WORKER_PROVIDER`: `gemini`, `openai`, and `anthropic` call the selected LLM provider for each caption-backed candidate up to `MAX_PROVIDER_CALLS_PER_RUN`, while `mock` uses the deterministic local analyzer. After enrichment, videos without an LLM-landscape signal are filtered out, published videos are ranked with deterministic scoring, and these files are written:

- `videos.json`
- `channels.json`
- `relationships.json`
- `run-metadata.json`

In the current live run, `run-metadata.json` reports `provider: "gemini"`, `model: "gemini-2.5-flash"`, `videos_seen: 28`, `videos_processed: 18`, and `videos_failed: 0`. Because the provider was Gemini and the provider-call cap was 30, the worker attempted Gemini extraction for the 28 caption-backed candidates, then published 18 and filtered 10 as outside the configured LLM landscape rules.

YouTube can temporarily block anonymous transcript requests after repeated runs. The worker now uses a provider chain: cache first, then `youtube_transcript_api`, then `yt_dlp`. When transcript providers fail for a given video, the run records compact skip reasons instead of silently writing fake data. The export only fails if no usable caption-backed videos remain after fetching and relevance filtering.

## Web Setup

```powershell
cd apps\web
npm install
npm run dev
```

The app reads snapshots from `apps/web/public/data`. The page is configured as dynamic so local snapshot updates are reflected without rebuilding the app.

For a production check:

```powershell
npm run build
```

## Docker

```powershell
docker compose up --build
```

The worker service runs `real-export` and writes snapshots into `apps/web/public/data`. The web service mounts that directory read-only and serves the dashboard on port `3000`.

## Configuration

Copy `.env.example` to `.env` for local overrides. Important settings:

- `VIDEOS_PER_CHANNEL`: RSS entries to inspect per seeded channel.
- `MAX_VIDEOS_PER_RUN`: maximum candidate videos to attempt in one run.
- `TRANSCRIPT_PROVIDERS`: comma-separated subtitle provider order. Default: `youtube_transcript_api,yt_dlp`.
- `TRANSCRIPT_REQUEST_DELAY_SECONDS`: delay between uncached transcript requests to reduce YouTube rate-limit pressure.
- `WORKER_PROVIDER`: enrichment provider. Default `mock` keeps the deterministic local analyzer for real exports. Set `gemini`, `openai`, or `anthropic` for provider-backed extraction.
- `GEMINI_API_KEY`: preferred API key variable for `WORKER_PROVIDER=gemini`. `GOOGLE_API_KEY` also works.
- `GEMINI_BASE_URL`: Google Gemini OpenAI-compatible base URL. Defaults to `https://generativelanguage.googleapis.com/v1beta/openai` for `WORKER_PROVIDER=gemini`.
- `GEMINI_MODEL`: Gemini model used by the adapter. Defaults to `gemini-2.5-flash` for `WORKER_PROVIDER=gemini`.
- `OPENAI_API_KEY`: API key used when `WORKER_PROVIDER=openai`.
- `OPENAI_BASE_URL`: OpenAI-compatible API base URL. Defaults to `https://api.openai.com/v1` outside Gemini mode.
- `OPENAI_MODEL`: chat model used by the OpenAI-compatible adapter. Defaults to `gpt-4.1-mini` outside Gemini mode.
- `ANTHROPIC_API_KEY`: API key used when `WORKER_PROVIDER=anthropic`.
- `ANTHROPIC_BASE_URL`: Anthropic Messages API base URL. Defaults to `https://api.anthropic.com/v1`.
- `ANTHROPIC_MODEL`: Anthropic model used by the adapter. Defaults to `claude-3-5-haiku-latest`.
- `MAX_PROVIDER_CALLS_PER_RUN`: hard cap on enrichment calls per run. Keep this low while testing paid LLM providers.
- `YT_DLP_COOKIES_PATH`: optional path to a Netscape-format YouTube cookies file for `yt-dlp`. Useful in CI when anonymous subtitle fetches hit bot checks.
- `YT_DLP_COOKIES_FROM_BROWSER`: optional local-only `yt-dlp` browser cookie source such as `chrome:Default`.
- `TRANSCRIPT_CACHE_DIR`: local transcript cache directory, ignored by Git.
- `SNAPSHOT_OUTPUT_DIR`: snapshot output directory.
- `CONTRACTS_DIR`: JSON Schema contract directory.
- `SEED_CHANNELS_PATH`: seeded channel SQL file or use `--channels-csv` for a custom channel list.

## API Key Setup

The worker reads provider credentials from process environment variables. `.env.example` is a template for variable names, not a safe place to store a real key in Git.

For a local PowerShell run with Gemini:

```powershell
$env:WORKER_PROVIDER = 'gemini'
$env:GEMINI_API_KEY = 'your-real-key'
$env:YT_DLP_COOKIES_PATH = (Resolve-Path .\www.youtube.com_cookies.txt).Path
.\.venv\Scripts\python.exe -m llm_landscape.main real-export
```

For GitHub Actions scheduled or manual runs:

1. Open the repository on GitHub.
2. Go to `Settings -> Secrets and variables -> Actions`.
3. Create a repository secret named `GEMINI_API_KEY`.
4. Keep `YT_DLP_COOKIES` populated as well, because transcript fetching still depends on authenticated YouTube cookies.

If you want to test another provider manually, create the matching secret instead: `OPENAI_API_KEY` for `WORKER_PROVIDER=openai` or `ANTHROPIC_API_KEY` for `WORKER_PROVIDER=anthropic`.

## Data Quality Notes

Scheduled production refreshes use Gemini for transcript-grounded structured extraction. Topic labels, summaries, content types, stance, evidence snippets, and confidence scores come from the selected provider for LLM-backed runs. Evidence snippets and full subtitle text are taken from fetched captions, and the dashboard exposes the full transcript inside the evidence drawer. Seeded channels carry a preferred caption language, so non-English channels can request their native captions before falling back to English. Video ordering is based on topic strength, topic diversity, evidence coverage, and recency. Relationship edges are based on computed topic overlap rather than free-form guesses.

The deterministic path remains available as an explicit fallback mode by running with `WORKER_PROVIDER=mock`, but LLM-backed runs do not silently fall back to deterministic analysis today. If Gemini/OpenAI/Anthropic credentials are missing, GitHub Actions fails before export. If a provider request or schema validation fails during a Gemini/OpenAI/Anthropic run, the run fails instead of publishing a mixed LLM/deterministic snapshot. If `MAX_PROVIDER_CALLS_PER_RUN` is lower than the number of caption-backed candidates, candidates beyond the cap are skipped and recorded in `error_summary`.

`estimated_cost_usd` in `run-metadata.json` is currently a placeholder set to `0`. It does not mean no provider calls were made. The worker does not yet record token usage or calculate provider spend from API responses, so real billing must be checked in the provider dashboard. A successful Gemini run with `provider: "gemini"` and nonzero `videos_seen` indicates provider-backed extraction was used for the processed candidate set up to the configured cap.

Provider-backed structured extraction is available for scheduled/manual/local runs through Gemini, OpenAI-compatible APIs, and Anthropic. Scheduled GitHub Actions runs use Gemini by default, capped by `MAX_PROVIDER_CALLS_PER_RUN`, while manual runs can still choose `mock`, `gemini`, `openai`, or `anthropic`. Provider responses are validated against a shared JSON Schema before snapshots are written; OpenAI runs also use strict `json_schema` response format, while Gemini and Anthropic receive the same schema in the prompt and pass through runtime schema validation.

## GitHub Actions Workflow

There are three workflows:

- `worker-check.yml`: runs worker tests and validates checked-in snapshots on pushes and pull requests.
- `web-check.yml`: installs the web app with `npm ci`, type-checks it, and runs `next build`.
- `update-landscape-data.yml`: scheduled/manual production-style update. It restores the transcript cache, requires a `YT_DLP_COOKIES` secret for the authenticated subtitle path, runs worker tests, exports real subtitle-backed snapshots, validates the JSON contracts, builds the web app with the refreshed data, and commits changed snapshot files.
- `deploy-pages.yml`: builds a static export from the checked-in snapshots and deploys the dashboard to GitHub Pages.

Add a repository secret named `YT_DLP_COOKIES` containing an exported Netscape cookie file from a signed-in YouTube browser session. The workflow writes that secret to a temporary file, validates that it looks like a YouTube cookie jar, and passes it to `yt-dlp` before snapshot export.

Manual `Update landscape data` runs can choose `mock`, `gemini`, `openai`, or `anthropic` through the `worker_provider` input. Scheduled runs use `gemini`, so add a repository secret named `GEMINI_API_KEY` before relying on the schedule. For manual LLM runs, add the matching secret you need: `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`. Keep `max_provider_calls_per_run` low while smoke-testing paid providers.

The scheduled refresh inspects two recent RSS entries per seeded channel and caps each run at 30 candidate videos. That keeps the run broad across channels without hammering YouTube too aggressively. If cookie validation fails, the workflow opens a GitHub issue titled `Refresh YT_DLP_COOKIES for scheduled data updates` unless one is already open.

For a local cookie check, do not treat a printed video ID as sufficient proof that the cookies are valid. `yt-dlp` can still print the ID for a public video while warning that the YouTube account cookies were rotated or rejected. A usable local check is:

```powershell
$output = & .\.venv\Scripts\python.exe -m yt_dlp --ignore-config --cookies .\www.youtube.com_cookies.txt --skip-download --ignore-no-formats-error --list-subs "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | Out-String
$output
if ($output -match 'provided YouTube account cookies are no longer valid|Sign in to confirm you''re not a bot|Use --cookies-from-browser or --cookies for the authentication') {
	throw 'YouTube rejected the cookies. Re-export them from a freshly signed-in browser session.'
}
```

Warnings about missing video formats, a missing JavaScript runtime, or missing `ffmpeg` are not authentication failures by themselves. For this project, the blocking warnings are the YouTube auth messages above.

For YouTube specifically, export cookies from a new private/incognito browser window to reduce the chance that YouTube rotates the session before `yt-dlp` uses it. The upstream `yt-dlp` guidance is: log into YouTube in a fresh private window, open `https://www.youtube.com/robots.txt` in that same tab, export the `youtube.com` cookies with a Netscape-cookie extension, and then close the private window immediately.

On Windows, `yt-dlp --cookies-from-browser` can also fail for Chromium-based browsers if the browser keeps its cookie database locked. If that command errors with `Could not copy Chrome cookie database`, fully close the browser first, or use a browser extension to export a Netscape cookie file instead of relying on live browser extraction.

If the exported cookie file contains only the three-line Netscape header and no cookie rows, treat it as an invalid export. That usually means the extension did not get access to the signed-in session cookies, commonly because it was not allowed in the private/incognito window or the export was made from the wrong browser session.

The scheduled CI refresh now prefers `yt_dlp` ahead of `youtube_transcript_api` so the authenticated provider is used first on GitHub-hosted runners.

Scheduled updates call Gemini by default. Manual `workflow_dispatch` runs can still opt into `mock`, `gemini`, `openai`, or `anthropic` for controlled comparisons.

For GitHub Pages deploys, the web build switches to a static export when `DEPLOY_TARGET=github-pages` is set. That path publishes the current checked-in snapshots. The Pages workflow runs on direct pushes to `main` and after a successful `Update landscape data` workflow, so scheduled snapshot refreshes are published to the public site automatically.
