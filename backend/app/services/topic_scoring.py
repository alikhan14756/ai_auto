"""Deterministic topic opportunity scoring and semantic deduplication algorithms."""

import re
from typing import Dict, List, Set, Tuple


class TopicScoringService:
    """Calculates multi-dimensional opportunity scores and detects historical duplicate topics."""

    # Default weights for composite opportunity scoring
    WEIGHTS = {
        "audience_relevance": 0.25,
        "practical_value": 0.25,
        "originality": 0.20,
        "search_volume": 0.15,
        "competition_advantage": 0.15,  # (100 - competition_score)
    }

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Convert text into normalized alphanumeric token set excluding common stop words."""
        stop_words = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
            "with", "by", "of", "from", "is", "are", "how", "what", "why",
            "you", "your", "can", "do", "it", "this", "that", "in", "2026",
        }
        tokens = re.findall(r"\b[a-z0-9_]+\b", text.lower())
        return {t for t in tokens if t not in stop_words and len(t) > 2}

    @classmethod
    def calculate_similarity(cls, title_a: str, title_b: str) -> float:
        """Compute Jaccard token similarity between two titles (0.0 to 1.0)."""
        tokens_a = cls._tokenize(title_a)
        tokens_b = cls._tokenize(title_b)

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / float(len(union))

    @classmethod
    def find_max_historical_similarity(
        cls,
        candidate_title: str,
        historical_titles: List[str],
    ) -> Tuple[float, str]:
        """Find the closest existing title in historical topics and its similarity ratio."""
        max_similarity = 0.0
        most_similar_title = ""

        for existing_title in historical_titles:
            sim = cls.calculate_similarity(candidate_title, existing_title)
            if sim > max_similarity:
                max_similarity = sim
                most_similar_title = existing_title

        return round(max_similarity, 3), most_similar_title

    @classmethod
    def calculate_opportunity_score(
        cls,
        audience_relevance: float,
        practical_value: float,
        originality: float,
        search_volume_score: float,
        competition_score: float,
        custom_weights: Dict[str, float] = None,
    ) -> float:
        """Calculate deterministic opportunity score (0.0 to 100.0) from component dimensions."""
        weights = custom_weights or cls.WEIGHTS

        # Clamp all inputs to 0-100
        rel = max(0.0, min(100.0, float(audience_relevance)))
        prac = max(0.0, min(100.0, float(practical_value)))
        orig = max(0.0, min(100.0, float(originality)))
        search = max(0.0, min(100.0, float(search_volume_score)))
        comp = max(0.0, min(100.0, float(competition_score)))

        # Lower competition means higher advantage
        comp_adv = 100.0 - comp

        w_rel = weights.get("audience_relevance", 0.25)
        w_prac = weights.get("practical_value", 0.25)
        w_orig = weights.get("originality", 0.20)
        w_search = weights.get("search_volume", 0.15)
        w_comp = weights.get("competition_advantage", 0.15)

        raw_score = (
            (rel * w_rel)
            + (prac * w_prac)
            + (orig * w_orig)
            + (search * w_search)
            + (comp_adv * w_comp)
        )

        final_score = max(0.0, min(100.0, raw_score))
        return round(final_score, 2)
