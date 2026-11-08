"""Thumbnail Concept Generator producing contrasting, non-deceptive creative directions."""

from typing import Any, Dict, List, Optional


class ThumbnailConceptGenerator:
    """Generates distinct, high-contrast creative thumbnail concepts based on project script content."""

    @classmethod
    def generate_concepts(
        cls,
        project_title: str,
        script_summary: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Synthesize 3 distinct thumbnail concepts (A, B, C) adhering to honest content representation."""
        clean_title = project_title.strip()
        kw = keywords or ["Architecture", "System", "Performance"]
        lead_kw = kw[0].upper() if kw else "ENGINEERING"

        # Concept A: Modern Tech Editorial (Clean, bold, punchy hook)
        concept_a = {
            "variant_code": "A",
            "concept_name": "The Technical Architecture",
            "style_preset": "modern_tech_editorial",
            "headline_text": f"{lead_kw} EXPLAINED",
            "subtitle_text": "DEEP DIVE 2026",
            "accent_color_hex": "#FF7A00",  # Vivid Ember
            "visual_directive": f"Isometric clean microservice topology showing {lead_kw} flow, dark obsidian canvas",
            "visual_hook": f"Isometric clean microservice topology showing {lead_kw} flow, dark obsidian canvas",
            "image_prompt": f"Minimalist tech architecture diagram for {clean_title}, glowing orange data streams on dark background",
            "rationale": "Clear technical clarity highlighting the fundamental engineering architecture.",
            "target_emotion": "Technical clarity and authority.",
            "composition_layers": [
                {"type": "background", "preset": "modern_tech_editorial", "visible": True},
                {"type": "accent_glow", "color": "#FF7A00", "radius": 280, "visible": True},
                {"type": "text", "role": "headline", "text": f"{lead_kw} EXPLAINED", "visible": True},
                {"type": "badge", "role": "subtitle", "text": "DEEP DIVE 2026", "visible": True},
            ],
        }

        # Concept B: High-Contrast Educational (Contrasting colors, practical utility)
        concept_b = {
            "variant_code": "B",
            "concept_name": "High-Contrast Practical Utility",
            "style_preset": "high_contrast_educational",
            "headline_text": f"BUILD A {lead_kw}",
            "subtitle_text": "STEP-BY-STEP",
            "accent_color_hex": "#FFE600",  # Yellow
            "visual_directive": f"Crisp high-contrast split visual demonstrating practical deployment of {clean_title}",
            "visual_hook": f"Crisp high-contrast split visual demonstrating practical deployment of {clean_title}",
            "image_prompt": f"Split screen diagram showing before and after optimization of {clean_title}, high contrast yellow and black",
            "rationale": "High contrast typography prioritizing mobile feed readability and direct practical utility.",
            "target_emotion": "Direct practical utility and curiosity.",
            "composition_layers": [
                {"type": "background", "preset": "high_contrast_educational", "visible": True},
                {"type": "accent_glow", "color": "#FFE600", "radius": 260, "visible": True},
                {"type": "text", "role": "headline", "text": f"BUILD A {lead_kw}", "visible": True},
                {"type": "badge", "role": "subtitle", "text": "STEP-BY-STEP", "visible": True},
            ],
        }

        # Concept C: Software Tutorial (IDE / Developer Focus)
        concept_c = {
            "variant_code": "C",
            "concept_name": "Developer Workflow & Code",
            "style_preset": "software_tutorial",
            "headline_text": f"ZERO TO PRO: {lead_kw}",
            "subtitle_text": "FULL TUTORIAL",
            "accent_color_hex": "#00F0FF",  # Neon Cyan
            "visual_directive": f"Modern dark mode terminal with glowing CLI output and code structure for {clean_title}",
            "visual_hook": f"Modern dark mode terminal with glowing CLI output and code structure for {clean_title}",
            "image_prompt": f"Dark code editor interface showing clean syntax highlighting and terminal commands for {clean_title}",
            "rationale": "Direct code and workflow framing resonating strongly with software engineers.",
            "target_emotion": "Mastery and precision workflow focus.",
            "composition_layers": [
                {"type": "background", "preset": "software_tutorial", "visible": True},
                {"type": "accent_glow", "color": "#00F0FF", "radius": 270, "visible": True},
                {"type": "text", "role": "headline", "text": f"ZERO TO PRO: {lead_kw}", "visible": True},
                {"type": "badge", "role": "subtitle", "text": "FULL TUTORIAL", "visible": True},
            ],
        }

        return [concept_a, concept_b, concept_c]
