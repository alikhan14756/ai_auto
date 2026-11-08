"""Security, API secrets, and sensitive token leak QA validator."""

import re
import time
from typing import List, Tuple
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator

# Regex patterns for high-risk credentials and secret tokens
SECRET_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    ("Google AI / Gemini Key", "AIza...", re.compile(r"\bAIza[0-9A-Za-z\-_]{30,45}\b")),
    ("Google Vertex / OAuth Key", r"AQ\....", re.compile(r"\bAQ\.[0-9A-Za-z\-_]{30,}\b")),
    ("OpenAI API Key", "sk-proj-... / sk-...", re.compile(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{30,}\b")),
    ("Anthropic API Key", "sk-ant-...", re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{30,}\b")),
    ("ElevenLabs Key", "xi-api-key", re.compile(r"\b(?:xi-)?[a-f0-9]{32}\b")),
    ("GitHub Personal Token", "ghp_... / gho_...", re.compile(r"\bgh[pous]_[a-zA-Z0-9]{36}\b")),
    ("AWS Access Key ID", "AKIA...", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("JWT Bearer Token", "Bearer eyJ...", re.compile(r"\beyJ[a-zA-Z0-9_\-]{15,}\.eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\b")),
]


class SecurityPrivacyValidator(BaseQAValidator):
    category = QACategory.SECURITY_PRIVACY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        texts_to_scan = []
        if context.script and getattr(context.script, "content", None):
            texts_to_scan.append(("script_content", context.script.content))
        if context.metadata_draft:
            if getattr(context.metadata_draft, "title", None):
                texts_to_scan.append(("metadata_title", context.metadata_draft.title))
            if getattr(context.metadata_draft, "description", None):
                texts_to_scan.append(("metadata_description", context.metadata_draft.description))
            if getattr(context.metadata_draft, "tags", None):
                texts_to_scan.append(("metadata_tags", " ".join(context.metadata_draft.tags)))

        detected_leaks = 0

        for field_name, text in texts_to_scan:
            for leak_type, pattern_desc, regex in SECRET_PATTERNS:
                matches = regex.findall(text)
                if matches:
                    detected_leaks += len(matches)
                    masked = [m[:4] + "..." + m[-4:] if len(m) > 8 else "***" for m in matches]
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact=field_name,
                            title=f"CRITICAL: Exposed Secret Detected ({leak_type}) in {field_name}",
                            explanation=f"Text artifact exposes live credential matching pattern '{pattern_desc}'.",
                            evidence={"artifact": field_name, "type": leak_type, "masked_matches": masked},
                            recommended_correction="Immediately revoke the exposed secret and purge token from text.",
                            requires_human_review=True,
                        )
                    )

        score = 0.0 if detected_leaks > 0 else 100.0
        status = QACheckStatus.FAILED.value if detected_leaks > 0 else QACheckStatus.PASSED.value

        results.append(
            self.create_result(
                check_name="credentials_and_secrets_leak_scan",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "artifacts_scanned": len(texts_to_scan),
                    "detected_leaks": detected_leaks,
                },
                findings=findings,
            )
        )

        return results
