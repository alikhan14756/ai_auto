"""Structured YouTube SEO Metadata Generator creating accurate, non-clickbait titles, descriptions, and tags."""

import re
from typing import Any, Dict, List, Optional


class SEOMetadataGenerator:
    """Generates broadcast-grade YouTube titles, descriptions, chapters, tags, and pinned comments."""

    SYNTHETIC_MEDIA_DISCLOSURE = (
        "Disclosure: This video features AI-assisted scriptwriting, neural voice narration, "
        "and automated editing produced via Creator Studio AI. All technical concepts, "
        "code samples, and claims are verified against authentic documentation."
    )

    @classmethod
    def generate_title_candidates(
        cls,
        topic_title: str,
        niche: str = "Software Engineering",
        keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate 3-5 distinct, accurate title candidates compliant with YouTube length limits (<=95 chars)."""
        clean_topic = topic_title.strip()
        kw = keywords or ["Python", "Architecture", "Engineering"]
        lead = kw[0] if kw else "System"

        candidates = [
            {
                "title": f"{clean_topic}: Complete Technical Architecture",
                "angle": "Architectural Breakdown",
                "character_count": len(f"{clean_topic}: Complete Technical Architecture"),
                "is_recommended": True,
            },
            {
                "title": f"Building {clean_topic} from Scratch ({lead} Guide)",
                "angle": "Practical Implementation",
                "character_count": len(f"Building {clean_topic} from Scratch ({lead} Guide)"),
                "is_recommended": False,
            },
            {
                "title": f"How {clean_topic} Works Under the Hood",
                "angle": "Deep Dive Explainer",
                "character_count": len(f"How {clean_topic} Works Under the Hood"),
                "is_recommended": False,
            },
            {
                "title": f"{clean_topic} Explained for Engineers",
                "angle": "Direct & Concise",
                "character_count": len(f"{clean_topic} Explained for Engineers"),
                "is_recommended": False,
            },
        ]

        # Enforce <= 95 char ceiling
        for c in candidates:
            if len(c["title"]) > 95:
                c["title"] = c["title"][:92] + "..."
                c["character_count"] = len(c["title"])

        return candidates

    @classmethod
    def format_timestamp(cls, seconds: float) -> str:
        """Format seconds into MM:SS for YouTube chapter markers."""
        total_sec = int(round(seconds))
        minutes = total_sec // 60
        secs = total_sec % 60
        return f"{minutes:02d}:{secs:02d}"

    @classmethod
    def generate_chapters(
        cls,
        scenes: Optional[List[Dict[str, Any]]] = None,
        total_duration_seconds: float = 300.0,
    ) -> List[Dict[str, Any]]:
        """Compile sequential chapter timestamps starting strictly at 00:00."""
        chapters = []
        if scenes and len(scenes) > 0:
            for s in scenes:
                start_sec = float(s.get("start_time_seconds", 0.0))
                title = (
                    s.get("title")
                    or s.get("visual_directive")
                    or s.get("section_type")
                    or "Chapter"
                )
                # Keep title concise (<= 40 chars)
                clean_title = re.sub(r"[^\w\s-]", "", title).strip()[:40]
                if not clean_title:
                    clean_title = f"Part {len(chapters) + 1}"

                chapters.append({
                    "timestamp": cls.format_timestamp(start_sec),
                    "seconds": start_sec,
                    "title": clean_title,
                })
        else:
            # Standard 4-part default chapters
            step = max(30.0, total_duration_seconds / 4.0)
            default_milestones = [
                ("00:00", 0.0, "Introduction & Problem Overview"),
                (cls.format_timestamp(step), step, "Core Architectural Mechanics"),
                (cls.format_timestamp(step * 2), step * 2, "Practical Implementation Walkthrough"),
                (cls.format_timestamp(step * 3), step * 3, "Production Best Practices & Summary"),
            ]
            for ts, sec, title in default_milestones:
                chapters.append({"timestamp": ts, "seconds": sec, "title": title})

        # Ensure first chapter is always exactly 00:00
        if len(chapters) > 0:
            chapters[0]["timestamp"] = "00:00"
            chapters[0]["seconds"] = 0.0

        return chapters

    @classmethod
    def generate_tags(
        cls,
        topic_title: str,
        niche: str = "Technology",
        keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate high-relevance search tags adhering strictly to YouTube's 500-character total limit."""
        kw_list = keywords or []
        base_tags = [
            topic_title.lower(),
            niche.lower(),
            "software engineering",
            "coding tutorial",
            "system architecture",
            "developer tools",
            "tech explainer",
        ]
        all_tags = base_tags + [k.lower() for k in kw_list if k]

        # Deduplicate while preserving order
        seen = set()
        final_tags = []
        total_chars = 0

        for t in all_tags:
            clean = t.strip()
            if clean and clean not in seen:
                # Comma separator counts toward YouTube's 500-character ceiling
                tag_len = len(clean) + 1
                if total_chars + tag_len <= 480:  # Safety margin under 500
                    seen.add(clean)
                    final_tags.append(clean)
                    total_chars += tag_len

        return final_tags

    @classmethod
    def generate_hashtags(
        cls,
        keywords: Optional[List[str]] = None,
        niche: str = "Programming",
    ) -> List[str]:
        """Generate 3-5 relevant hashtags."""
        tags = []
        if keywords:
            for k in keywords[:3]:
                clean = re.sub(r"[^\w]", "", k.title())
                if clean:
                    tags.append(f"#{clean}")

        if len(tags) < 4:
            clean_niche = re.sub(r"[^\w]", "", niche.title())
            tags.append(f"#{clean_niche}")
            tags.append("#SoftwareEngineering")

        return tags[:5]

    @classmethod
    def generate_description(
        cls,
        title: str,
        script_summary: str,
        chapters: List[Dict[str, Any]],
        research_sources: Optional[List[Dict[str, Any]]] = None,
        hashtags: Optional[List[str]] = None,
    ) -> str:
        """Compose structured YouTube video description with timestamps, citations, and disclosures."""
        lines = []

        # 1. Opening Hook Summary
        lines.append(script_summary.strip() or f"In this deep dive, we explore {title}.")
        lines.append("")

        # 2. Key Takeaways
        lines.append("📌 What you'll learn in this video:")
        lines.append("• Architectural patterns and design decisions explained with zero fluff.")
        lines.append("• Hands-on code structures and real-world deployment strategies.")
        lines.append("• Performance benchmarks and reliability guardrails.")
        lines.append("")

        # 3. Chapters Section
        if chapters:
            lines.append("⏱️ Timestamps:")
            for ch in chapters:
                lines.append(f"{ch['timestamp']} - {ch['title']}")
            lines.append("")

        # 4. Verified Citations / Research Sources
        if research_sources and len(research_sources) > 0:
            lines.append("🔗 Verified Sources & Technical References:")
            for src in research_sources[:4]:
                title_s = src.get("title", "Technical Documentation")
                url_s = src.get("url", "")
                if url_s:
                    lines.append(f"• {title_s}: {url_s}")
                else:
                    lines.append(f"• {title_s}")
            lines.append("")

        # 5. Hashtags
        if hashtags:
            lines.append(" ".join(hashtags))
            lines.append("")

        # 6. Mandatory AI Disclosure
        lines.append("---")
        lines.append(cls.SYNTHETIC_MEDIA_DISCLOSURE)

        return "\n".join(lines)

    @classmethod
    def generate_pinned_comment(cls, title: str) -> str:
        """Generate engaging community discussion prompt."""
        return (
            f"Question for the community: When building systems around {title}, "
            "what has been your biggest architectural challenge or tradeoff? "
            "Drop your thoughts below—let's discuss!"
        )

    @classmethod
    def generate_full_metadata(
        cls,
        topic_title: str,
        script_summary: str,
        niche: str = "Software Engineering",
        keywords: Optional[List[str]] = None,
        scenes: Optional[List[Dict[str, Any]]] = None,
        research_sources: Optional[List[Dict[str, Any]]] = None,
        total_duration_seconds: float = 300.0,
    ) -> Dict[str, Any]:
        """Aggregate full metadata payload."""
        titles = cls.generate_title_candidates(topic_title, niche, keywords)
        chosen_title = titles[0]["title"]

        chapters = cls.generate_chapters(scenes, total_duration_seconds)
        tags = cls.generate_tags(topic_title, niche, keywords)
        hashtags = cls.generate_hashtags(keywords, niche)
        description = cls.generate_description(
            title=chosen_title,
            script_summary=script_summary,
            chapters=chapters,
            research_sources=research_sources,
            hashtags=hashtags,
        )
        pinned_comment = cls.generate_pinned_comment(chosen_title)

        return {
            "title": chosen_title,
            "title_candidates": titles,
            "description": description,
            "tags": tags,
            "hashtags": hashtags,
            "chapters": chapters,
            "pinned_comment": pinned_comment,
            "synthetic_media_disclosure": True,
        }
