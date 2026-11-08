"""Deterministic script evaluation, quality metrics, and repetition analysis."""

import re
from typing import Dict, List, Optional, Set, Tuple
from app.schemas.script import ScriptQualityMetrics


class ScriptEvaluationService:
    """Evaluates script spoken quality, narrative pace, repetition, and evidence coverage."""

    DEFAULT_WORDS_PER_MINUTE = 140.0

    @classmethod
    def calculate_word_count(cls, text: str) -> int:
        """Count spoken words in script text."""
        words = re.findall(r"\b[A-Za-z0-9'-]+\b", text)
        return len(words)

    @classmethod
    def estimate_duration_seconds(cls, word_count: int, wpm: float = DEFAULT_WORDS_PER_MINUTE) -> int:
        """Estimate spoken audio duration in seconds at target speech rate."""
        if word_count <= 0 or wpm <= 0:
            return 0
        return int(round((word_count / wpm) * 60.0))

    @classmethod
    def evaluate_hook_strength(cls, hook_text: str) -> float:
        """Score hook urgency, curiosity, and brevity (0.0 to 100.0)."""
        if not hook_text or not hook_text.strip():
            return 20.0

        score = 70.0
        words = hook_text.lower().split()
        word_count = len(words)

        # Ideal hook length: 10 to 45 words
        if 10 <= word_count <= 45:
            score += 15.0
        elif word_count < 8 or word_count > 60:
            score -= 15.0

        # Curiosity and engineering problem triggers
        curiosity_triggers = [
            "why", "how", "stop", "never", "most developers", "secret",
            "hidden", "instead", "failure", "replace", "replacing", "mistake", "benchmark"
        ]
        matches = sum(1 for trigger in curiosity_triggers if trigger in hook_text.lower())
        score += min(15.0, matches * 5.0)

        return max(10.0, min(100.0, score))

    @classmethod
    def evaluate_clarity(cls, text: str) -> float:
        """Evaluate sentence length and readability for spoken delivery."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 50.0

        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)

        # Optimal spoken sentence length: 12-18 words
        score = 90.0
        if avg_len > 25:
            score -= (avg_len - 25) * 2.0
        elif avg_len < 8:
            score -= (8 - avg_len) * 2.0

        # Run-on sentences (> 35 words) are difficult to speak naturally
        run_ons = sum(1 for l in lengths if l > 35)
        score -= run_ons * 4.0

        return max(20.0, min(100.0, score))

    @classmethod
    def detect_repetition(cls, text: str) -> float:
        """Compute repetition index based on repeated 3-gram phrase frequency (0.0 to 1.0)."""
        words = [w.lower() for w in re.findall(r"\b[a-z0-9]+\b", text)]
        if len(words) < 10:
            return 0.0

        trigrams = [tuple(words[i:i+3]) for i in range(len(words) - 2)]
        unique_trigrams = set(trigrams)

        if not trigrams:
            return 0.0

        # Ratio of duplicate trigrams
        repetition_ratio = 1.0 - (len(unique_trigrams) / len(trigrams))
        return round(max(0.0, min(1.0, repetition_ratio)), 3)

    @classmethod
    def evaluate_script(
        cls,
        full_text: str,
        hook_text: str,
        total_claims: int = 0,
        verified_claims: int = 0,
        unverified_claims: int = 0,
        historical_texts: Optional[List[str]] = None,
    ) -> ScriptQualityMetrics:
        """Compute composite quality assessment for a complete script draft."""
        word_count = cls.calculate_word_count(full_text)
        duration_sec = cls.estimate_duration_seconds(word_count)
        hook_score = cls.evaluate_hook_strength(hook_text)
        clarity_score = cls.evaluate_clarity(full_text)
        rep_index = cls.detect_repetition(full_text)

        # Evidence coverage
        if total_claims > 0:
            coverage = (verified_claims / float(total_claims)) * 100.0
        else:
            coverage = 80.0  # neutral if zero factual claims made

        # Historical similarity check
        hist_sim = 0.0
        if historical_texts:
            curr_tokens = set(re.findall(r"\b[a-z0-9]+\b", full_text.lower()))
            for past in historical_texts:
                past_tokens = set(re.findall(r"\b[a-z0-9]+\b", past.lower()))
                if curr_tokens and past_tokens:
                    sim = len(curr_tokens.intersection(past_tokens)) / len(curr_tokens.union(past_tokens))
                    if sim > hist_sim:
                        hist_sim = sim

        # Composite overall score
        w_hook = 0.25 * hook_score
        w_clarity = 0.25 * clarity_score
        w_coverage = 0.25 * coverage
        w_rep = 0.15 * (100.0 - (rep_index * 100.0))
        w_sim = 0.10 * (100.0 - (hist_sim * 100.0))

        overall = max(0.0, min(100.0, w_hook + w_clarity + w_coverage + w_rep + w_sim))

        return ScriptQualityMetrics(
            overall_score=round(overall, 1),
            hook_strength=round(hook_score, 1),
            clarity_score=round(clarity_score, 1),
            evidence_coverage=round(coverage, 1),
            repetition_index=rep_index,
            historical_similarity=round(hist_sim, 3),
            word_count=word_count,
            estimated_duration_seconds=duration_sec,
            unverified_claims_count=unverified_claims,
        )
