"""Visual asset coverage, resolution, and diversity QA validator."""

import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class VisualAssetsValidator(BaseQAValidator):
    category = QACategory.VISUAL_ASSETS.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        scenes = context.scenes
        if not scenes:
            results.append(
                self.create_result(
                    check_name="scene_visual_coverage",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="storyboard",
                            title="No Storyboard Scenes Defined",
                            explanation="Project contains zero scenes or visual storyboard definitions.",
                            recommended_correction="Generate storyboard scenes in Visual Planning module.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        total_scenes = len(scenes)
        uncovered_scenes = 0
        low_res_assets = 0
        consecutive_duplicates = 0
        last_asset_id = None

        req_w = 1080 if context.project_format == "SHORTS" else 1920
        req_h = 1920 if context.project_format == "SHORTS" else 1080

        for idx, scene in enumerate(scenes):
            asset_id = getattr(scene, "selected_asset_id", None) or getattr(scene, "media_asset_id", None)
            if not asset_id:
                uncovered_scenes += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.HIGH.value,
                        affected_artifact=f"scene_{idx + 1}",
                        title=f"Scene {idx + 1} Missing Visual Asset",
                        explanation=f"Scene #{idx + 1} '{getattr(scene, 'title', '')}' has no assigned visual asset.",
                        evidence={"scene_index": idx + 1, "scene_id": str(getattr(scene, "id", ""))},
                        recommended_correction="Assign an AI-generated or stock media asset to this scene.",
                    )
                )
            else:
                if last_asset_id and asset_id == last_asset_id:
                    consecutive_duplicates += 1
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.MEDIUM.value,
                            affected_artifact=f"scene_{idx + 1}",
                            title=f"Consecutive Duplicate Asset on Scene {idx + 1}",
                            explanation=f"Scene {idx + 1} uses the identical media asset as Scene {idx}, causing visual stagnation.",
                            evidence={"scene_index": idx + 1, "asset_id": str(asset_id)},
                            recommended_correction="Select a distinct visual asset or change camera angle.",
                        )
                    )
                last_asset_id = asset_id

        # Media assets resolution check
        for asset in context.media_assets:
            w = int(getattr(asset, "width", 0) or 0)
            h = int(getattr(asset, "height", 0) or 0)
            if w > 0 and h > 0:
                if w < (req_w * 0.75) or h < (req_h * 0.75):
                    low_res_assets += 1
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.MEDIUM.value,
                            affected_artifact="media_asset",
                            title=f"Sub-optimal Asset Resolution ({w}x{h})",
                            explanation=f"Asset resolution is significantly below canvas target ({req_w}x{req_h}), risking pixelation.",
                            evidence={"asset_id": str(getattr(asset, "id", "")), "width": w, "height": h},
                            recommended_correction="Upscale or replace with 1080p/4K visual asset.",
                        )
                    )

        score = 100.0
        if uncovered_scenes > 0:
            score -= (uncovered_scenes / total_scenes) * 70.0
        score -= (consecutive_duplicates * 10.0)
        score -= (low_res_assets * 5.0)
        score = max(0.0, score)

        status = QACheckStatus.PASSED.value
        if uncovered_scenes > 0 or score < 60.0:
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="scene_visual_integrity",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "total_scenes": total_scenes,
                    "uncovered_scenes": uncovered_scenes,
                    "consecutive_duplicates": consecutive_duplicates,
                    "low_res_assets": low_res_assets,
                },
                findings=findings,
            )
        )

        return results
