from __future__ import annotations

from llm_landscape.domain import Channel, Transcript, TranscriptSegment, Video, VideoBundle


# ---------------------------------------------------------------------------
# Mock channels
# ---------------------------------------------------------------------------

_BUILDER = Channel(
    youtube_channel_id="mock-channel-build",
    title="Builder Signals",
    handle="@buildersignals",
    description="Mock channel focused on practical LLM systems.",
    url="https://www.youtube.com/@buildersignals",
)
_RESEARCH = Channel(
    youtube_channel_id="mock-channel-research",
    title="Research Radar",
    handle="@researchradar",
    description="Mock channel focused on model releases and open model analysis.",
    url="https://www.youtube.com/@researchradar",
)
_CODING = Channel(
    youtube_channel_id="mock-channel-code",
    title="Code Companion Lab",
    handle="@codecompanionlab",
    description="Mock channel focused on AI coding assistants and developer tools.",
    url="https://www.youtube.com/@codecompanionlab",
)
_TWO_MIN = Channel(
    youtube_channel_id="UC2D2CMWXMOVWx7giW1n3LIg",
    title="Two Minute Papers",
    handle="@TwoMinutePapers",
    description="Research-focused AI and machine learning explainers.",
    url="https://www.youtube.com/@TwoMinutePapers",
)
_LEX = Channel(
    youtube_channel_id="UCSHZKyawb77ixDdsGog4iWA",
    title="Lex Fridman",
    handle="@lexfridman",
    description="Long-form technical interviews with AI researchers and builders.",
    url="https://www.youtube.com/@lexfridman",
)
_FIRESHIP = Channel(
    youtube_channel_id="UCbfYPyITQ-7l4upoX8nvctg",
    title="Fireship",
    handle="@Fireship",
    description="Fast software engineering and AI tooling explainers.",
    url="https://www.youtube.com/@Fireship",
)
_PRIME = Channel(
    youtube_channel_id="UCUyeluBRhGPCW4rPe_UvBZQ",
    title="ThePrimeTime",
    handle="@ThePrimeTimeagen",
    description="Developer commentary, tools, and AI coding workflow coverage.",
    url="https://www.youtube.com/@ThePrimeTimeagen",
)
_FCC = Channel(
    youtube_channel_id="UC8butISFwT-Wl7EV0hUK0BQ",
    title="freeCodeCamp.org",
    handle="@freecodecamp",
    description="Technical courses and tutorials, including practical AI application development.",
    url="https://www.youtube.com/@freecodecamp",
)


def _bundle(
    video_id: str,
    title: str,
    published_at: str,
    channel: Channel,
    segments: list[tuple[float, float, str]],
) -> VideoBundle:
    text = " ".join(seg[2] for seg in segments)
    return VideoBundle(
        video=Video(
            youtube_video_id=video_id,
            title=title,
            url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=published_at,
            channel=channel,
        ),
        transcript=Transcript(
            video_id=video_id,
            source="fixture",
            language="en",
            text=text,
            segments=tuple(
                TranscriptSegment(idx, start, end, body)
                for idx, (start, end, body) in enumerate(segments)
            ),
        ),
    )


def load_mock_bundles() -> list[VideoBundle]:
    """Return a denser fixture set with partial overlap between channel clusters.

    The MockProvider derives topics by keyword-matching the transcript text, so each
    bundle below is engineered to hit different keyword combinations instead of pushing
    every channel into the same few topics.
    """

    return [
        # --- Builder Signals: agents + evals ---
        _bundle(
            "mock-agents-001",
            "Why AI agents changed LLM application design",
            "2026-05-01T12:00:00Z",
            _BUILDER,
            [
                (
                    42,
                    52,
                    "An agent only becomes useful when the production team can watch tool traces and run evaluation gates before every deploy.",
                ),
                (
                    53,
                    66,
                    "The company rollout worked because we measured failure recovery instead of trusting a flashy demo.",
                ),
            ],
        ),
        _bundle(
            "mock-build-eval-101",
            "Evaluation harnesses for production agent stacks",
            "2026-05-09T10:00:00Z",
            _BUILDER,
            [
                (
                    18,
                    34,
                    "For enterprise adoption you need scorecards for agent tasks, clear ownership, and repeatable evaluation reviews.",
                ),
                (
                    35,
                    48,
                    "Our deploy checklist is boring on purpose because production systems fail in predictable ways.",
                ),
            ],
        ),
        # --- Research Radar: releases + open models ---
        _bundle(
            "mock-local-002",
            "Open models and local inference in 2026",
            "2026-05-02T15:30:00Z",
            _RESEARCH,
            [
                (
                    88,
                    101,
                    "This release matters because the new open-weight model can run with local inference on a single workstation.",
                ),
                (
                    102,
                    118,
                    "Privacy-sensitive builders finally have a real alternative to a hosted model API.",
                ),
            ],
        ),
        _bundle(
            "mock-research-bench-202",
            "Benchmark season: which open model actually wins",
            "2026-05-11T14:00:00Z",
            _RESEARCH,
            [
                (
                    12,
                    28,
                    "The latest model release pushed multimodal vision and audio understanding into the top tier of the benchmark table.",
                ),
                (
                    29,
                    44,
                    "Unlike last month, the open model now stays competitive on the public leaderboard.",
                ),
            ],
        ),
        # --- Code Companion Lab: coding workflows ---
        _bundle(
            "mock-coding-003",
            "Coding assistants are becoming software agents",
            "2026-05-03T09:10:00Z",
            _CODING,
            [
                (
                    15,
                    27,
                    "This coding assistant behaves like an agent that opens a repository, edits files, and drafts the pull request.",
                ),
                (
                    28,
                    38,
                    "The interesting shift is how much editor work it can finish without asking for help.",
                ),
            ],
        ),
        _bundle(
            "mock-coding-local-004",
            "Running a coding agent fully local",
            "2026-05-13T17:00:00Z",
            _CODING,
            [
                (
                    8,
                    22,
                    "We ran the coding assistant against a local inference server backed by an open-weight model.",
                ),
                (
                    23,
                    36,
                    "Because the repository stays on the laptop, privacy concerns drop a lot.",
                ),
            ],
        ),
        # --- Two Minute Papers: multimodal research ---
        _bundle(
            "mock-tmp-301",
            "This new open model rewrites the leaderboard",
            "2026-05-04T08:00:00Z",
            _TWO_MIN,
            [
                (
                    5,
                    18,
                    "A new multimodal model release can reason over images, audio, and video clips at once.",
                ),
                (
                    19,
                    32,
                    "It also jumps near the top of the benchmark leaderboard despite being an open model.",
                ),
            ],
        ),
        # --- Lex Fridman: agents + safety ---
        _bundle(
            "mock-lex-401",
            "Agents, evaluation, and the path to autonomous research",
            "2026-05-06T20:00:00Z",
            _LEX,
            [
                (
                    600,
                    640,
                    "In this interview we discuss how agent systems should be aligned before companies trust them with real decisions.",
                ),
                (
                    641,
                    690,
                    "Safety work matters because deployment pressure can outrun careful policy and risk review.",
                ),
            ],
        ),
        # --- Fireship: coding + agents quick takes ---
        _bundle(
            "mock-fireship-501",
            "AI coding agents in 100 seconds",
            "2026-05-07T11:00:00Z",
            _FIRESHIP,
            [
                (
                    2,
                    12,
                    "A coding agent can scan your repository, patch the bug, and post a pull request before you finish coffee.",
                ),
                (
                    13,
                    24,
                    "This is the fastest editor workflow change I have seen in years.",
                ),
            ],
        ),
        _bundle(
            "mock-fireship-502",
            "Local LLMs just got scary good",
            "2026-05-12T11:00:00Z",
            _FIRESHIP,
            [
                (
                    3,
                    14,
                    "Today a new open model release made local inference good enough for everyday laptop use.",
                ),
                (
                    15,
                    26,
                    "That matters because privacy stops being the excuse for not shipping offline AI.",
                ),
            ],
        ),
        # --- ThePrimeTime: coding + opinionated takes ---
        _bundle(
            "mock-prime-601",
            "Reacting to the new coding agent benchmark",
            "2026-05-08T22:00:00Z",
            _PRIME,
            [
                (
                    30,
                    48,
                    "My problem with the new coding tool is the repository automation looks impressive but the evaluation story is shaky.",
                ),
                (
                    49,
                    68,
                    "Until the test suite is honest, I do not trust the scorecards.",
                ),
            ],
        ),
        _bundle(
            "mock-prime-602",
            "Why I run my coding model locally",
            "2026-05-14T22:00:00Z",
            _PRIME,
            [
                (
                    10,
                    24,
                    "Running the coding workflow through local inference keeps the repository on my machine.",
                ),
                (
                    25,
                    40,
                    "That tradeoff matters more to me than cloud polish.",
                ),
            ],
        ),
        # --- freeCodeCamp: tutorials on RAG and tuning ---
        _bundle(
            "mock-fcc-701",
            "Build a coding agent from scratch",
            "2026-05-10T13:00:00Z",
            _FCC,
            [
                (
                    60,
                    90,
                    "In this workshop we combine RAG with a coding assistant so the app can cite the right files during code generation.",
                ),
                (
                    91,
                    120,
                    "Then we fine-tune the helper with LoRA adapters for our internal codebase.",
                ),
            ],
        ),
        _bundle(
            "mock-fcc-702",
            "RAG and agents tutorial: end-to-end project",
            "2026-05-15T13:00:00Z",
            _FCC,
            [
                (
                    20,
                    44,
                    "The second tutorial shows a retrieval pipeline, fine tuning, and a deployment plan for a large team.",
                ),
                (
                    45,
                    70,
                    "It is the kind of RAG system companies can adopt without rewriting everything.",
                ),
            ],
        ),
    ]
