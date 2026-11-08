"""Automated targeted correction recommendations generator."""

from typing import Dict, List
from app.services.qa.constants import QACategory, QASeverity


class QACorrectionEngine:
    """Generates precise, step-by-step remediation advice for QA findings."""

    @classmethod
    def generate_correction_guide(cls, finding: dict) -> dict:
        category = finding.get("category", "")
        severity = finding.get("severity", "")
        title = finding.get("title", "")
        artifact = finding.get("affected_artifact", "")
        evidence = finding.get("evidence", {})

        guide = {
            "title": title,
            "severity": severity,
            "category": category,
            "affected_artifact": artifact,
            "actionable_steps": [],
            "automated_fix_available": False,
            "navigation_target": "",
        }

        if category == QACategory.SECURITY_PRIVACY.value:
            guide["navigation_target"] = "/script-studio"
            guide["actionable_steps"] = [
                "1. Immediately rotate the exposed API key or token in the provider developer console.",
                "2. Navigate to Script Studio or SEO Studio and delete the token characters from the text.",
                "3. Ensure the token is stored securely in environment variables (.env) and never hardcoded in production assets.",
            ]
        elif category == QACategory.FACTUAL_ACCURACY.value:
            guide["navigation_target"] = "/script-studio"
            guide["actionable_steps"] = [
                "1. Open Script Studio and locate the highlighted claim citation.",
                "2. Provide an authoritative research reference URL (e.g. peer-reviewed study, official doc).",
                "3. Re-run factual verification or modify the statement to reflect verified facts.",
            ]
        elif category == QACategory.VIDEO_TECHNICAL.value:
            guide["navigation_target"] = "/video-editor"
            guide["actionable_steps"] = [
                "1. Open Video Studio Timeline.",
                "2. Inspect the scene transition where black frames were detected.",
                "3. Extend the preceding scene or trim the voice gap to ensure continuous visual asset coverage.",
                "4. Trigger a fresh 1080p MP4 render.",
            ]
        elif category == QACategory.THUMBNAIL_QUALITY.value:
            guide["navigation_target"] = "/thumbnail-studio"
            guide["actionable_steps"] = [
                "1. Open Thumbnail Studio.",
                "2. Ensure canvas dimensions are set to 1280x720 (16:9).",
                "3. Select high-contrast preset and confirm file export is under 2.0 MB.",
                "4. Click 'Set as Active Thumbnail'.",
            ]
        elif category == QACategory.METADATA_SEO.value:
            guide["navigation_target"] = "/seo-studio"
            guide["actionable_steps"] = [
                "1. Open SEO Studio.",
                "2. Ensure title is between 50 and 80 characters.",
                "3. Ensure first chapter begins at 00:00.",
                "4. Check that combined search tags are under 500 characters.",
                "5. Save and approve the draft.",
            ]
        elif category == QACategory.NARRATION_AUDIO.value:
            guide["navigation_target"] = "/video-editor"
            guide["actionable_steps"] = [
                "1. Check audio track levels in Voice & Audio Studio.",
                "2. Apply loudness normalization filter targeting -14.0 LUFS.",
                "3. Ensure master audio limiter ceiling is at -1.0 dBTP to avoid clipping.",
            ]
        else:
            guide["actionable_steps"] = [
                "1. Review the finding explanation and evidence.",
                "2. Make necessary adjustments in the corresponding production studio.",
                "3. Re-execute the QA audit gate.",
            ]

        return guide
