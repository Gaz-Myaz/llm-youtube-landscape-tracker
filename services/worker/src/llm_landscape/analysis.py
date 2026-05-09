from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from llm_landscape.domain import Transcript, TranscriptSegment, Video
from llm_landscape.llm.base import EnrichmentResult, Evidence, Topic
from llm_landscape.llm.mock import TOPIC_RULES

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+'-]*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_TOPIC_KEYWORDS = {
    "agents": (
        "ai agent",
        "ai agents",
        "coding agent",
        "agentic",
        "autonomous agent",
        "agent mode",
        "operator",
        "manus",
        "tool call",
        "planner",
    ),
    "coding-assistants": (
        "coding assistant",
        "coding agent",
        "code assistant",
        "developer workflow",
        "pull request",
        "repository",
        "copilot",
        "github copilot",
        "cursor",
        "claude code",
        "windsurf",
        "aider",
        "replit",
        "bolt",
        "vibe coding",
    ),
    "open-source-models": (
        "open weight",
        "open weights",
        "open model",
        "open models",
        "open source model",
        "open-source model",
        "open source ai",
        "llama",
        "qwen",
        "gemma",
    ),
    "local-inference": (
        "local inference",
        "local model",
        "local llm",
        "on device",
        "on-device",
        "ollama",
        "llama.cpp",
        "lm studio",
        "gguf",
        "vllm",
        "offline model",
        "privacy",
    ),
    "rag": (
        "rag",
        "retrieval augmented",
        "retrieval-augmented",
        "retrieval",
        "vector database",
        "vector search",
        "grounded answer",
        "knowledge base",
    ),
    "multimodal": (
        "multimodal",
        "vision language",
        "image generation",
        "video generation",
        "audio model",
        "image model",
        "text to image",
        "text-to-image",
        "text to video",
        "text-to-video",
    ),
    "fine-tuning": (
        "fine tuning",
        "fine-tuning",
        "lora",
        "adapter",
        "adapters",
        "sft",
    ),
    "safety-alignment": (
        "ai safety",
        "alignment",
        "aligned model",
        "safety filter",
        "policy model",
        "model risk",
        "red team",
    ),
    "enterprise-adoption": (
        "enterprise ai",
        "ai adoption",
        "production ai",
        "deploy model",
        "model deployment",
        "deployment pipeline",
        "rollout",
    ),
    "evals": (
        "evaluation",
        "eval",
        "evals",
        "arena",
        "test suite",
        "scorecard",
        "scorecards",
        "regression test",
    ),
    "benchmarks": (
        "benchmark",
        "benchmarks",
        "leaderboard",
        "swe-bench",
        "mmlu",
        "livebench",
    ),
    "model-releases": (
        "model release",
        "new model",
        "released model",
        "announced model",
        "chatgpt",
        "gpt",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "deepseek",
        "grok",
        "llama",
        "mistral",
        "qwen",
        "gemma",
        "sora",
        "codex",
        "opus",
        "sonnet",
    ),
}
_TITLE_FALLBACK_KEYWORDS = {
    "agents": ("agent", "agents", "agentic", "operator", "manus"),
    "coding-assistants": (
        "copilot",
        "github copilot",
        "cursor",
        "claude code",
        "windsurf",
        "aider",
        "replit",
        "coding agent",
        "vibe coding",
    ),
    "open-source-models": (
        "open source",
        "open-source",
        "open weight",
        "open weights",
        "llama",
        "qwen",
        "gemma",
        "mistral",
        "deepseek",
    ),
    "local-inference": (
        "local model",
        "local llm",
        "ollama",
        "llama.cpp",
        "lm studio",
        "gguf",
    ),
    "multimodal": (
        "multimodal",
        "vision",
        "image generation",
        "video generation",
        "text to image",
        "text to video",
    ),
    "model-releases": (
        "ai",
        "gpt",
        "chatgpt",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "deepseek",
        "grok",
        "mistral",
        "llama",
        "qwen",
        "gemma",
        "nvidia",
        "sakana",
        "model",
        "release",
        "launch",
        "launched",
    ),
}
_TOPIC_LABELS = {slug: label for slug, label, _score, _keywords in TOPIC_RULES}
_TOPIC_BASE_SCORES = {slug: score for slug, _label, score, _keywords in TOPIC_RULES}
_LANDSCAPE_SIGNAL_RE = re.compile(
    r"(?<![a-z0-9])(ai|llm|gpt|openai|anthropic|claude|gemini|llama|deepseek|mistral|grok|agentic|agents?|model|models)(?![a-z0-9])"
)
_CONTENT_TYPES = (
    ("tutorial", ("tutorial", "course", "workshop", "build", "from scratch", "walkthrough", "hands-on", "how to")),
    ("benchmark", ("benchmark", "leaderboard", "score", "scores", "comparison", "compare", "beats", "versus", " vs ")),
    ("interview", ("interview", "guest", "conversation", "podcast", "lex fridman podcast")),
    ("research", ("paper", "research", "study", "experiment", "dataset", "deepmind", "sakana ai")),
    ("demo", ("demo", "launch", "release", "released", "announced", "showcase", "dropped", "just got")),
    ("analysis", ("explained", "state of", "narrative", "changed", "disrupted", "broke", "shouldn't work", "what happened")),
    ("opinion", ("reacting", "reaction", "take", "opinion", "why i", "rant")),
)
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "every",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "much",
    "need",
    "only",
    "over",
    "really",
    "should",
    "that",
    "their",
    "there",
    "these",
    "thing",
    "this",
    "those",
    "through",
    "today",
    "using",
    "video",
    "want",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


@dataclass(frozen=True)
class TopicMatch:
    slug: str
    label: str
    relevance_score: float
    keywords: tuple[str, ...]


class DeterministicAnalyzer:
    name = "deterministic"
    model = "keyword-transcript-v1"
    prompt_version = "rules-2026-05-07"

    def extract_video_insights(self, video: Video, transcript: Transcript) -> EnrichmentResult:
        transcript_text = transcript.text.strip()
        analysis_text = _analysis_text(video, transcript_text)
        topic_matches = _match_topics(analysis_text)
        if not topic_matches:
            topic_matches = _fallback_title_topic_matches(video)
        topics = tuple(
            Topic(match.slug, match.label, match.relevance_score)
            for match in topic_matches[:4]
        )
        evidence = tuple(
            _evidence_for_topic(transcript, match)
            for match in topic_matches[:3]
        )
        return EnrichmentResult(
            schema_version="1.0",
            video_id=video.youtube_video_id,
            provider=self.name,
            model=self.model,
            prompt_version=self.prompt_version,
            primary_speaker=_speaker_for(video),
            summary=_summary_for(video, transcript_text, topic_matches),
            content_type=_content_type_for(video, analysis_text, topic_matches),
            stance="transcript-derived deterministic analysis",
            topics=topics,
            evidence=evidence,
            confidence_score=_confidence_for(analysis_text, topic_matches),
            raw_response={"mode": "deterministic_keywords", "source": transcript.source},
        )

    def summarize_relationship(
        self,
        source_channel: str,
        target_channel: str,
        shared_topic_labels: list[str],
        score: float,
    ) -> str:
        if not shared_topic_labels:
            return f"{source_channel} and {target_channel} have limited overlap in fetched captions."
        topics = ", ".join(shared_topic_labels[:3])
        return (
            f"{source_channel} and {target_channel} overlap in subtitle-derived coverage of "
            f"{topics}. Topic-overlap score: {score:.2f}."
        )


def is_landscape_relevant(video: Video, enrichment: EnrichmentResult) -> bool:
    if not enrichment.topics:
        return False
    title_text = f"{video.title} {video.description or ''}".lower()
    if _LANDSCAPE_SIGNAL_RE.search(title_text):
        return True
    strong_topics = [topic for topic in enrichment.topics if topic.relevance_score >= 0.78]
    return len(strong_topics) >= 2 or any(topic.relevance_score >= 0.84 for topic in enrichment.topics)


def _analysis_text(video: Video, transcript_text: str) -> str:
    return " ".join(
        part.strip()
        for part in (video.title, video.description or "", transcript_text)
        if part and part.strip()
    )


def _fallback_title_topic_matches(video: Video) -> tuple[TopicMatch, ...]:
    title_text = f"{video.title} {video.description or ''}".lower()
    matches: list[TopicMatch] = []
    for slug, keywords in _TITLE_FALLBACK_KEYWORDS.items():
        hit_keywords = tuple(keyword for keyword in keywords if _keyword_occurrences(title_text, keyword) > 0)
        if not hit_keywords:
            continue
        score = min(0.78, _TOPIC_BASE_SCORES[slug] - 0.16 + len(hit_keywords) * 0.04)
        matches.append(TopicMatch(slug, _TOPIC_LABELS[slug], round(score, 3), hit_keywords))
    return tuple(sorted(matches, key=lambda match: match.relevance_score, reverse=True))


def _match_topics(text: str) -> tuple[TopicMatch, ...]:
    lowered = text.lower()
    word_count = max(1, len(_WORD_RE.findall(lowered)))
    matches: list[TopicMatch] = []
    for slug, keywords in _TOPIC_KEYWORDS.items():
        hit_keywords = tuple(keyword for keyword in keywords if _keyword_occurrences(lowered, keyword) > 0)
        if not hit_keywords:
            continue
        occurrence_count = sum(_keyword_occurrences(lowered, keyword) for keyword in hit_keywords)
        density = min(0.18, occurrence_count / word_count * 10)
        keyword_bonus = min(0.12, len(hit_keywords) * 0.035)
        score = min(0.99, _TOPIC_BASE_SCORES[slug] - 0.22 + density + keyword_bonus)
        matches.append(TopicMatch(slug, _TOPIC_LABELS[slug], round(score, 3), hit_keywords))
    return tuple(sorted(matches, key=lambda match: match.relevance_score, reverse=True))


def _keyword_occurrences(text: str, keyword: str) -> int:
    return len(_keyword_pattern(keyword).findall(text))


@lru_cache(maxsize=512)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword.lower()).replace(r"\ ", r"[\s\u00a0-]+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def _evidence_for_topic(transcript: Transcript, match: TopicMatch) -> Evidence:
    segment = _best_segment(transcript.segments, match.keywords)
    quote = segment.text if segment else _best_sentence(transcript.text, match.keywords)
    return Evidence(
        field_name="topic",
        topic_slug=match.slug,
        quote=quote[:480],
        start_seconds=segment.start_seconds if segment else None,
        end_seconds=segment.end_seconds if segment else None,
        confidence_score=min(0.95, match.relevance_score + 0.05),
    )


def _best_segment(
    segments: tuple[TranscriptSegment, ...], keywords: tuple[str, ...]
) -> TranscriptSegment | None:
    if not segments:
        return None
    if not keywords:
        return segments[0]
    return max(
        segments,
        key=lambda segment: sum(_keyword_occurrences(segment.text.lower(), keyword) for keyword in keywords),
    )


def _best_sentence(text: str, keywords: tuple[str, ...]) -> str:
    sentences = [sentence.strip() for sentence in _SENTENCE_RE.split(text) if sentence.strip()]
    if not sentences:
        return text[:480]
    if not keywords:
        return sentences[0]
    return max(sentences, key=lambda sentence: sum(_keyword_occurrences(sentence.lower(), keyword) for keyword in keywords))


def _summary_for(video: Video, text: str, topics: tuple[TopicMatch, ...]) -> str:
    topic_text = ", ".join(topic.label for topic in topics[:3]) or "LLM coverage"
    sentence = _best_sentence(text, topics[0].keywords if topics else ()) if text else ""
    if sentence:
        return f"{video.title} focuses on {topic_text}. Key transcript signal: {sentence[:220]}"
    return f"{video.title} focuses on {topic_text}."


def _content_type_for(video: Video, text: str, topics: tuple[TopicMatch, ...]) -> str:
    haystack = f"{video.title} {text[:2500]}".lower()
    for content_type, keywords in _CONTENT_TYPES:
        if any(keyword in haystack for keyword in keywords):
            return content_type
    if topics and _LANDSCAPE_SIGNAL_RE.search(haystack):
        return "analysis"
    return "unknown"


def _speaker_for(video: Video) -> str | None:
    if video.channel.title:
        return f"{video.channel.title} host"
    return None


def _confidence_for(text: str, topics: tuple[TopicMatch, ...]) -> float:
    words = _WORD_RE.findall(text.lower())
    if not words or not topics:
        return 0.35
    signal_words = [word for word in words if word not in _STOPWORDS and len(word) > 3]
    diversity = len(set(signal_words)) / max(1, len(signal_words))
    topic_signal = min(0.35, len(topics) * 0.07)
    return round(min(0.92, 0.46 + topic_signal + diversity * 0.12), 3)
