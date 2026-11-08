"""YouTube SEO metadata and compliance QA validator."""

import time
from typing import List
from app.services.qa.constants import (
    QACategory,
    QASeverity,
    QACheckStatus,
    MAX_TITLE_LENGTH_CHARS,
    MAX_TAGS_LENGTH_CHARS,
)
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class MetadataSEOValidator(BaseQAValidator):
    category = QACategory.METADATA_SEO.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        draft = context.metadata_draft
        if not draft:
            results.append(
                self.create_result(
                    check_name="metadata_presence_check",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="metadata",
                            title="Missing SEO Metadata Draft",
                            explanation="Project does not contain an approved SEO metadata draft.",
                            recommended_correction="Generate SEO metadata package in SEO Studio.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        title = getattr(draft, "title", "") or ""
        description = getattr(draft, "description", "") or ""
        tags = getattr(draft, "tags", []) or []
        chapters = getattr(draft, "chapters", []) or []

        # 1. Title length check
        title_len = len(title)
        if title_len == 0:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="title",
                    title="Empty Video Title",
                    explanation="Title is required for YouTube upload.",
                    recommended_correction="Provide a concise, descriptive video title.",
                )
            )
        elif title_len > MAX_TITLE_LENGTH_CHARS:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="title",
                    title=f"Video Title Too Long ({title_len} chars)",
                    explanation=f"Title exceeds safe YouTube display limit of {MAX_TITLE_LENGTH_CHARS} characters.",
                    evidence={"length": title_len, "max": MAX_TITLE_LENGTH_CHARS},
                    recommended_correction="Shorten title to under 80 characters for full mobile visibility.",
                )
            )

        # 2. Chapters check (for long-form)
        if context.project_format != "SHORTS":
            if not chapters:
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.MEDIUM.value,
                        affected_artifact="chapters",
                        title="No Video Chapters Configured",
                        explanation="Adding video chapters enhances viewer navigation and YouTube SEO ranking.",
                        recommended_correction="Generate timestamped chapters starting at 00:00.",
                    )
                )
            else:
                first_ch = chapters[0] if len(chapters) > 0 else {}
                first_ts = first_ch.get("timestamp", "") if isinstance(first_ch, dict) else ""
                if first_ts not in ["00:00", "0:00"]:
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.HIGH.value,
                            affected_artifact="chapters",
                            title=f"Chapters Must Start at 00:00 (Starts at '{first_ts}')",
                            explanation="YouTube requires the initial chapter timestamp to be exactly 00:00.",
                            evidence={"first_timestamp": first_ts},
                            recommended_correction="Update first chapter timestamp to 00:00.",
                        )
                    )

        # 3. Tags check (limit 500 characters)
        tags_str = ",".join(tags)
        tags_len = len(tags_str)
        if tags_len > MAX_TAGS_LENGTH_CHARS:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="tags",
                    title=f"Tags Exceed 500 Characters ({tags_len} chars)",
                    explanation="YouTube API strictly rejects tags payloads longer than 500 characters.",
                    evidence={"tags_length": tags_len, "max_allowed": MAX_TAGS_LENGTH_CHARS},
                    recommended_correction="Prune secondary tags until combined length is below 500 characters.",
                )
            )

        score = 100.0
        for f in findings:
            if f.severity == QASeverity.CRITICAL.value:
                score = 0.0
            elif f.severity == QASeverity.HIGH.value:
                score -= 25.0
            elif f.severity == QASeverity.MEDIUM.value:
                score -= 10.0

        status = QACheckStatus.PASSED.value
        if score < 60.0 or any(f.severity == QASeverity.CRITICAL.value for f in findings):
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="seo_metadata_integrity",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "title_length": title_len,
                    "description_length": len(description),
                    "tags_length": tags_len,
                    "chapters_count": len(chapters),
                },
                findings=findings,
            )
        )

        return results
