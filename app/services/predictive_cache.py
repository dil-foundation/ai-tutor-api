import asyncio
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


def _normalize_text(value: str) -> str:
    """Lowercase, trim, and strip punctuation to make comparison resilient."""
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip().lower()
    return re.sub(r"[^a-z0-9\s'.,!?-]", "", cleaned)


def _default_topic(topic: Optional[str]) -> str:
    return topic or "this topic"


@dataclass
class PredictiveResult:
    text: str
    stage: str
    source: str
    confidence: float
    pattern_key: str
    topic: Optional[str] = None


class StageAwareCache:
    """
    Stage-aware predictive response cache.

    - Stage templates: curated responses per learning stage
    - Pattern cache: stores exact responses for repeated utterances
    - Phrase cache: quick responses for globally common phrases
    """

    def __init__(self, ttl_seconds: int = 600):
        self.ttl_seconds = ttl_seconds
        self.stage_templates: Dict[str, List[str]] = {
            "greeting": [
                "Hi {user_name}, I'm your AI English tutor. What would you like to learn today?",
                "Hello {user_name}! Ready to practice English now?",
            ],
            "intent_detection": [
                "Thanks for sharing, {user_name}. Are you focusing on vocabulary, grammar, or pronunciation?",
                "Great, {user_name}! Should we dive into vocabulary, grammar, or a casual topic?",
            ],
            "vocabulary_learning": [
                "Let's explore a new vocabulary word together. I'll guide you through examples.",
                "Great choice! I'll walk you through some practical vocabulary on {topic}.",
            ],
            "sentence_practice": [
                "Let's build a sentence together using proper structure.",
                "I'll help you refine that sentence with better grammar.",
            ],
            "topic_discussion": [
                "Let's keep discussing {topic}—share what you think and I'll guide you.",
                "Interesting topic! Tell me more about {topic}, and I'll help polish your English.",
            ],
            "grammar_focus": [
                "Let's slow down and review the grammar rule step by step.",
                "Great attempt! Remember the grammar rule about {topic}.",
            ],
            "pronunciation_practice": [
                "I'll break the pronunciation down into smaller parts for you.",
                "Repeat after me and focus on the syllables I'm emphasizing.",
            ],
            "closing": [
                "Nice work today, {user_name}! Want to review anything before we wrap up?",
                "You're making solid progress, {user_name}. Ready for another round or shall we end here?",
            ],
        }
        self.pattern_cache: Dict[str, Tuple[str, float]] = {}
        self.phrase_cache: Dict[str, Tuple[str, float]] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "pattern_hits": 0,
            "template_hits": 0,
        }
        self._lock = asyncio.Lock()

    def _pattern_key(self, stage: str, user_text: str, topic: Optional[str]) -> str:
        normalized = _normalize_text(user_text)
        bucket = normalized[:120]  # bucket similar utterances
        topic_bucket = _normalize_text(topic or "general")
        return f"{stage}:{topic_bucket}:{bucket}"

    def _purge_expired(self) -> None:
        now = time.time()
        for cache in (self.pattern_cache, self.phrase_cache):
            expired_keys = [key for key, (_, expiry) in cache.items() if expiry < now]
            for key in expired_keys:
                cache.pop(key, None)

    def _select_stage_template(self, stage: str, user_name: str, topic: Optional[str]) -> Optional[str]:
        templates = self.stage_templates.get(stage) or self.stage_templates.get("intent_detection")
        if not templates:
            return None
        index = abs(hash(f"{stage}:{topic}:{user_name}")) % len(templates)
        return templates[index].format(user_name=user_name, topic=_default_topic(topic))

    def _is_similar(self, expected: str, actual: str, threshold: float = 0.82) -> bool:
        first = _normalize_text(expected)
        second = _normalize_text(actual)
        if not first or not second:
            return False
        return SequenceMatcher(None, first, second).ratio() >= threshold

    async def get_prediction(
        self,
        *,
        stage: str,
        user_input: str,
        user_name: str,
        topic: Optional[str],
    ) -> Optional[PredictiveResult]:
        """Return a likely response for the current stage and input."""
        pattern_key = self._pattern_key(stage, user_input, topic)

        async with self._lock:
            self._purge_expired()

            now = time.time()
            if pattern_key in self.pattern_cache:
                cached_text, expiry = self.pattern_cache[pattern_key]
                if expiry >= now:
                    self.stats["hits"] += 1
                    self.stats["pattern_hits"] += 1
                    return PredictiveResult(
                        text=cached_text,
                        stage=stage,
                        source="pattern_cache",
                        confidence=0.9,
                        pattern_key=pattern_key,
                        topic=topic,
                    )

            normalized_input = _normalize_text(user_input)
            if normalized_input in self.phrase_cache:
                cached_text, expiry = self.phrase_cache[normalized_input]
                if expiry >= now:
                    self.stats["hits"] += 1
                    return PredictiveResult(
                        text=cached_text,
                        stage=stage,
                        source="phrase_cache",
                        confidence=0.8,
                        pattern_key=pattern_key,
                        topic=topic,
                    )

            template_text = self._select_stage_template(stage, user_name, topic)
            if template_text:
                self.stats["misses"] += 1
                self.stats["template_hits"] += 1
                return PredictiveResult(
                    text=template_text,
                    stage=stage,
                    source="stage_template",
                    confidence=0.55,
                    pattern_key=pattern_key,
                    topic=topic,
                )

            self.stats["misses"] += 1
            return None

    async def record_result(
        self,
        prediction: Optional[PredictiveResult],
        actual_response: str,
        *,
        matched: bool,
        user_input: str,
    ) -> None:
        """Persist cache learning from the actual AI response."""
        if not prediction:
            return

        async with self._lock:
            self._purge_expired()
            expiry = time.time() + self.ttl_seconds

            # Always learn the accurate response for this pattern
            self.pattern_cache[prediction.pattern_key] = (actual_response, expiry)

            normalized_input = _normalize_text(user_input)
            self.phrase_cache[normalized_input] = (actual_response, expiry)

            if matched:
                self.stats["hits"] += 1

    def is_prediction_match(self, prediction: Optional[PredictiveResult], actual_response: str) -> bool:
        if not prediction:
            return False
        return self._is_similar(prediction.text, actual_response)

    def snapshot_stats(self) -> Dict[str, int]:
        return dict(self.stats)

