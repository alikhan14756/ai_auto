"""Script structure, clarity, and repetition QA validator."""

import re
import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class ScriptQualityValidator(BaseQAValidator):
    category = QACategory.SCRIPT_QUALITY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        script = context.script
        if not script:
            results.append(
                self.create_result(
                    check_name="script_content_verification",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="script",
                            title="Missing Script Artifact",
                            explanation="Video project does not have an approved script generated.",
                            recommended_correction="Generate and approve a script in Script Studio before QA audit.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        content = getattr(script, "content", "") or ""
        word_count = int(getattr(script, "word_count", 0) or len(content.split()))
        pacing_wpm = float(getattr(script, "pacing_wpm", 140.0) or 140.0)
        repetition_idx = float(getattr(script, "repetition_index", 0.0) or 0.0)

        # Word count / Duration check
        is_shorts = (context.project_format == "SHORTS")
        min_words = 40 if is_shorts else 150
        max_words = 220 if is_shorts else 3500

        if word_count < min_words:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="script",
                    title="Script Word Count Deficient",
                    explanation=f"Script contains only {word_count} words; minimum required for format {context.project_format} is {min_words}.",
                    evidence={"word_count": word_count, "min_words": min_words},
                    recommended_correction="Expand narration with detailed scene breakdowns and explanatory depth.",
                )
            )
        elif word_count > max_words:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.MEDIUM.value,
                    affected_artifact="script",
                    title="Script Word Count Exceeds Safe Pacing",
                    explanation=f"Script contains {word_count} words, risking viewer fatigue or truncation.",
                    evidence={"word_count": word_count, "max_words": max_words},
                    recommended_correction="Condense dialogue to maintain high viewer retention and concise delivery.",
                )
            )

        # Repetition check (trigrams)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", content.lower())
        if len(words) >= 6:
            trigrams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
            repeats = {}
            for tg in trigrams:
                repeats[tg] = repeats.get(tg, 0) + 1
            excessive_repeats = {k: v for k, v in repeats.items() if v >= 3}
            if excessive_repeats:
                repeated_phrases = [" ".join(k) for k in list(excessive_repeats.keys())[:3]]
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.MEDIUM.value,
                        affected_artifact="script",
                        title=f"Excessive Trigram Repetition Detected ({len(excessive_repeats)} instances)",
                        explanation="Repeated verbal phrases reduce script perceived quality and professionalism.",
                        evidence={"repeated_phrases": repeated_phrases},
                        recommended_correction="Use varied sentence structure and synonyms to eliminate redundant phrasing.",
                    )
                )

        # Score computation
        score = 100.0
        for f in findings:
            if f.severity == QASeverity.HIGH.value:
                score -= 25.0
            elif f.severity == QASeverity.MEDIUM.value:
                score -= 10.0
            elif f.severity == QASeverity.LOW.value:
                score -= 3.0

        status = QACheckStatus.PASSED.value
        if score < 70.0:
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="script_quality_and_structure",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "word_count": word_count,
                    "pacing_wpm": pacing_wpm,
                    "repetition_index": repetition_idx,
                },
                findings=findings,
            )
        )

        return results
