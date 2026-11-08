"""Deterministic YouTube SEO and Thumbnail/Title Pairing Scorer."""

import re
from typing import Any, Dict, List, Optional


class SEOMetadataScorer:
    """Evaluates YouTube metadata compliance, search visibility, and thumbnail alignment."""

    CLICKBAIT_PATTERNS = [
        r"\bSHOCKING\b",
        r"\bINSANE\b",
        r"\bYOU WON'?T BELIEVE\b",
        r"\bDESTROYED\b",
        r"\bWILL BLOW YOUR MIND\b",
        r"\bSECRET THEY HIDE\b",
        r"!!+",
        r"\?\?+",
    ]

    @classmethod
    def evaluate_title(cls, title: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """Evaluate title length, clarity, keyword presence, and clickbait avoidance."""
        issues = []
        strengths = []
        score = 25.0
        t_len = len(title.strip())

        if t_len > 95:
            issues.append(f"Title length ({t_len} chars) exceeds YouTube recommended ceiling of 95 characters.")
            score -= 15.0
        elif 45 <= t_len <= 80:
            strengths.append(f"Optimal title length ({t_len} chars) for desktop and mobile feeds.")
        elif t_len < 25:
            issues.append(f"Title is very short ({t_len} chars); may lack descriptive search context.")
            score -= 8.0

        # Clickbait check
        for pat in cls.CLICKBAIT_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                issues.append("Title contains sensational clickbait wording or excessive punctuation.")
                score -= 10.0
                break

        # Keyword alignment
        if keywords and any(k.lower() in title.lower() for k in keywords):
            strengths.append("Title contains primary target keywords in leading positions.")
        elif keywords:
            issues.append("Primary target keywords not found in title.")
            score -= 5.0

        return {"score": max(0.0, score), "issues": issues, "strengths": strengths}

    @classmethod
    def _ts_to_seconds(cls, ts: str) -> Optional[int]:
        """Convert MM:SS or HH:MM:SS timestamp string to total seconds."""
        parts = ts.strip().split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            return None
        return None

    @classmethod
    def evaluate_description(cls, description: str, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate description completeness, chapters, citations, and disclosure."""
        issues = []
        strengths = []
        score = 35.0
        desc = description.strip()

        if len(desc) < 200:
            issues.append("Description is very brief (< 200 chars); add video overview and resources.")
            score -= 15.0
        else:
            strengths.append(f"Comprehensive description ({len(desc)} characters).")

        # Disclosure check
        if "Disclosure:" in desc or "syntheticMedia" in desc or "AI" in desc:
            strengths.append("Mandatory synthetic media / AI disclosure included.")
        else:
            issues.append("Missing recommended synthetic media transparency statement.")
            score -= 5.0

        # Chapters check
        if chapters and len(chapters) >= 3:
            first_ts = chapters[0].get("timestamp", "")
            if first_ts in ["00:00", "0:00"]:
                strengths.append(f"Valid chapter markers included ({len(chapters)} chapters starting at 00:00).")
            else:
                issues.append("Chapters must begin at 00:00 for YouTube automatic chapter recognition.")
                score -= 8.0

            # 10-second minimum spacing and monotonic progression
            prev_sec = None
            spacing_valid = True
            for ch in chapters:
                sec = cls._ts_to_seconds(ch.get("timestamp", ""))
                if sec is None or (prev_sec is not None and sec - prev_sec < 10):
                    spacing_valid = False
                    break
                prev_sec = sec

            if not spacing_valid:
                issues.append("Each chapter must be at least 10 seconds long and timestamps in ascending order.")
                score -= 6.0
        else:
            issues.append("Fewer than 3 chapter timestamps provided.")
            score -= 10.0

        return {"score": max(0.0, score), "issues": issues, "strengths": strengths}

    @classmethod
    def evaluate_tags(cls, tags: List[str]) -> Dict[str, Any]:
        """Evaluate search tags count and total character limit."""
        issues = []
        strengths = []
        score = 20.0

        total_chars = sum(len(t) + 1 for t in tags)
        if total_chars > 500:
            issues.append(f"Total tag length ({total_chars} chars) exceeds YouTube maximum of 500 characters.")
            score -= 15.0
        elif 5 <= len(tags) <= 25 and total_chars <= 480:
            strengths.append(f"Well-balanced tag density ({len(tags)} tags, {total_chars}/500 chars).")
        elif len(tags) < 4:
            issues.append("Too few search tags provided (< 4 tags).")
            score -= 8.0

        return {"score": max(0.0, score), "issues": issues, "strengths": strengths}

    @classmethod
    def evaluate_pairing(cls, thumbnail_headline: str, video_title: str) -> Dict[str, Any]:
        """Evaluate consistency between thumbnail text and video title."""
        issues = []
        strengths = []
        score = 20.0

        th_words = set(re.findall(r"\w+", thumbnail_headline.lower()))
        ti_words = set(re.findall(r"\w+", video_title.lower()))
        overlap = th_words.intersection(ti_words)

        if thumbnail_headline.strip().lower() == video_title.strip().lower():
            issues.append("Thumbnail text is identical to title; use a shorter, complementary hook instead.")
            score -= 10.0
        elif len(overlap) > 0:
            strengths.append(f"Thumbnail hook complements title topic ({len(overlap)} shared concepts).")
        else:
            # Check length of hook
            if len(th_words) <= 5:
                strengths.append("Thumbnail hook is punchy and concise (<= 5 words).")
            else:
                issues.append("Thumbnail text contains more than 5 words; reduce for mobile readability.")
                score -= 6.0

        return {"score": max(0.0, score), "issues": issues, "strengths": strengths}

    @classmethod
    def score_metadata_package(
        cls,
        title: str,
        description: str,
        tags: List[str],
        chapters: List[Dict[str, Any]],
        thumbnail_headline: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Aggregate comprehensive SEO report and numerical quality score (0-100)."""
        t_eval = cls.evaluate_title(title, keywords)
        d_eval = cls.evaluate_description(description, chapters)
        tag_eval = cls.evaluate_tags(tags)

        total_seo = t_eval["score"] + d_eval["score"] + tag_eval["score"] + 20.0  # Base 20 for formatting
        total_seo = max(0.0, min(100.0, round(total_seo, 1)))

        all_issues = t_eval["issues"] + d_eval["issues"] + tag_eval["issues"]
        all_strengths = t_eval["strengths"] + d_eval["strengths"] + tag_eval["strengths"]

        pairing_eval = None
        pairing_score = 0.0
        if thumbnail_headline:
            p_eval = cls.evaluate_pairing(thumbnail_headline, title)
            pairing_score = round(p_eval["score"] * 5.0, 1)  # Scale to 100
            pairing_eval = {
                "score": pairing_score,
                "issues": p_eval["issues"],
                "strengths": p_eval["strengths"],
            }
            all_issues.extend(p_eval["issues"])
            all_strengths.extend(p_eval["strengths"])

        return {
            "seo_score": total_seo,
            "pairing_score": pairing_score,
            "status": "EXCELLENT" if total_seo >= 85 else "GOOD" if total_seo >= 70 else "NEEDS_IMPROVEMENT",
            "issues": all_issues,
            "strengths": all_strengths,
            "title_analysis": t_eval,
            "description_analysis": d_eval,
            "tags_analysis": tag_eval,
            "pairing_analysis": pairing_eval,
        }
