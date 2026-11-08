"""Unit tests for all 12 QA domain validators."""

import os
import uuid
import pytest
from app.services.qa.constants import (
    QACategory,
    QASeverity,
    QACheckStatus,
    MAX_BLACK_FRAME_DURATION_SEC,
    MAX_FREEZE_FRAME_DURATION_SEC,
    MAX_AUDIO_SILENCE_DURATION_SEC,
    MAX_AUDIO_TRUE_PEAK_DBTP,
)
from app.services.qa.models import QAExecutionContext
from app.services.qa.validators import (
    FactualAccuracyValidator,
    ScriptQualityValidator,
    AudioQualityValidator,
    VisualAssetsValidator,
    VideoTechnicalValidator,
    CaptionIntegrityValidator,
    ThumbnailQualityValidator,
    MetadataSEOValidator,
    CopyrightLicensingValidator,
    SecurityPrivacyValidator,
    YouTubePolicyValidator,
    PackageCompletenessValidator,
)


class MockRecord:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def base_context():
    proj_id = uuid.uuid4()
    chan_id = uuid.uuid4()
    return QAExecutionContext(
        project_id=proj_id,
        project_title="Building Autonomous AI Agents with Python",
        project_format="LONG_FORM",
        channel_id=chan_id,
    )


@pytest.mark.asyncio
async def test_factual_accuracy_validator_contradicted(base_context):
    validator = FactualAccuracyValidator()
    base_context.script_claims = [
        MockRecord(
            id=uuid.uuid4(),
            claim_text="Python was invented in 2024 by Google.",
            verification_status="CONTRADICTED",
            confidence_score=0.95,
        )
    ]
    results = await validator.validate(base_context)
    assert len(results) == 1
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert res.score == 0.0
    assert any(f.severity == QASeverity.CRITICAL.value for f in res.findings)


@pytest.mark.asyncio
async def test_factual_accuracy_validator_clean(base_context):
    validator = FactualAccuracyValidator()
    base_context.script_claims = [
        MockRecord(
            id=uuid.uuid4(),
            claim_text="Python was created by Guido van Rossum and released in 1991.",
            verification_status="VERIFIED",
            confidence_score=0.98,
        )
    ]
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.PASSED.value
    assert res.score == 100.0
    assert len(res.findings) == 0


@pytest.mark.asyncio
async def test_script_quality_validator_missing(base_context):
    validator = ScriptQualityValidator()
    base_context.script = None
    results = await validator.validate(base_context)
    assert results[0].status == QACheckStatus.FAILED.value
    assert results[0].score == 0.0
    assert results[0].findings[0].severity == QASeverity.CRITICAL.value


@pytest.mark.asyncio
async def test_script_quality_validator_clean(base_context):
    validator = ScriptQualityValidator()
    # 15 distinct natural sentences without any repetition
    sentences = [
        "Welcome to Creator Studio AI where we explore automated systems.",
        "In this episode we will break down software design principles in depth.",
        "First we examine database indexing strategies and query performance optimizations.",
        "Next we look at asynchronous worker queue architectures with durable leases.",
        "Notice how message brokers ensure at least once delivery across all nodes.",
        "Furthermore our pipeline integrates deterministic quality assurance checks.",
        "This guarantees high fidelity audio sharp visuals and synchronized captions.",
        "Then we inspect automated media ingestion pipelines and cloud storage adapters.",
        "Next the narrative synthesizer converts raw data into engaging storylines.",
        "The voice generation engine synthesizes natural expressive voiceovers.",
        "Subtitles are generated in SubStation Alpha format with active word highlight.",
        "Color grading ensures obsidian tones with warm amber embers throughout.",
        "Each frame is verified using video analysis filters before final export.",
        "Finally we prepare the complete publication package for release review.",
        "Thank you for watching and make sure to subscribe for more engineering deep dives.",
    ]
    content = " ".join(sentences)
    base_context.script = MockRecord(
        content=content,
        word_count=len(content.split()),
        pacing_wpm=145.0,
        repetition_index=0.01,
    )
    results = await validator.validate(base_context)
    assert results[0].status == QACheckStatus.PASSED.value
    assert results[0].score >= 90.0


@pytest.mark.asyncio
async def test_audio_quality_validator_clipping_and_silence(base_context):
    validator = AudioQualityValidator()
    base_context.narration_track = MockRecord(
        id=uuid.uuid4(),
        audio_file_path="storage/audio.wav",
        integrated_lufs=-22.0,  # Severe deviation from -14
        true_peak_dbtp=-0.2,    # Above -1.0 dBTP ceiling
        qa_metrics={
            "integrated_lufs": -22.0,
            "true_peak_dbtp": -0.2,
            "max_silence_duration_s": 2.5,  # Exceeds 1.5s
        }
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status in [QACheckStatus.WARNING.value, QACheckStatus.FAILED.value]
    severities = [f.severity for f in res.findings]
    assert QASeverity.HIGH.value in severities


@pytest.mark.asyncio
async def test_visual_assets_validator_uncovered_scenes(base_context):
    validator = VisualAssetsValidator()
    base_context.scenes = [
        MockRecord(id=uuid.uuid4(), sequence_number=1, title="Intro", media_asset_id=None),
        MockRecord(id=uuid.uuid4(), sequence_number=2, title="Body", media_asset_id=uuid.uuid4()),
    ]
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert any("Missing Visual Asset" in f.title for f in res.findings)


@pytest.mark.asyncio
async def test_video_technical_validator_black_frames_critical(base_context):
    validator = VideoTechnicalValidator()
    base_context.render_job = MockRecord(
        id=uuid.uuid4(),
        status="COMPLETED",
        output_video_path="storage/test.mp4",
        black_frame_duration_max=0.85,  # > 0.25s threshold
        freeze_duration_max=0.5,
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert res.score == 0.0
    critical_findings = [f for f in res.findings if f.severity == QASeverity.CRITICAL.value]
    assert any("Black Frame" in f.title for f in critical_findings)


@pytest.mark.asyncio
async def test_video_technical_validator_quality_report_metrics(base_context):
    """Verify that VideoTechnicalValidator inspects QualityReport associated with the render."""
    validator = VideoTechnicalValidator()
    render_job = MockRecord(
        id=uuid.uuid4(),
        status="COMPLETED",
        output_video_path="storage/test.mp4",
        quality_reports=[
            MockRecord(
                black_frame_duration_max=0.92,
                freeze_duration_max=3.5,
                all_checks_passed=False,
            )
        ]
    )
    base_context.render_job = render_job
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert any("Black Frame" in f.title for f in res.findings)
    assert any("Frozen Video Frame" in f.title for f in res.findings)


@pytest.mark.asyncio
async def test_thumbnail_quality_validator_dimensions(base_context):
    validator = ThumbnailQualityValidator()
    base_context.thumbnail = MockRecord(
        id=uuid.uuid4(),
        storage_path="storage/thumb.png",
        width=1920,   # Not 1280
        height=1080,  # Not 720
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert any(f.severity == QASeverity.HIGH.value and "Dimensions" in f.title for f in res.findings)


@pytest.mark.asyncio
async def test_metadata_seo_validator_chapters_and_tags(base_context):
    validator = MetadataSEOValidator()
    base_context.metadata_draft = MockRecord(
        title="Valid Title Under 95 Chars",
        description="Great video overview.",
        chapters=[{"timestamp": "01:00", "title": "Late Start"}],  # Did not start at 00:00
        tags=["python"] * 100,  # Long tags > 500 chars
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert any("00:00" in f.title for f in res.findings)
    assert any("Tags Exceed" in f.title for f in res.findings)


@pytest.mark.asyncio
async def test_security_privacy_validator_secrets_detected(base_context):
    validator = SecurityPrivacyValidator()
    base_context.script = MockRecord(
        content="Here is my Google API key: AIzaSyA1234567890123456789012345678901 for debugging."
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert res.score == 0.0
    assert any(f.severity == QASeverity.CRITICAL.value and "Secret Detected" in f.title for f in res.findings)


@pytest.mark.asyncio
async def test_youtube_policy_validator_deceptive_hazard(base_context):
    validator = YouTubePolicyValidator()
    base_context.metadata_draft = MockRecord(
        title="Get rich overnight 100% guaranteed free bitcoin giveaway",
        description="Click here.",
        synthetic_media_declared=False,
    )
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert any(f.severity == QASeverity.CRITICAL.value for f in res.findings)


@pytest.mark.asyncio
async def test_package_completeness_validator(base_context):
    validator = PackageCompletenessValidator()
    base_context.render_job = None
    base_context.thumbnail = None
    base_context.metadata_draft = None
    results = await validator.validate(base_context)
    res = results[0]
    assert res.status == QACheckStatus.FAILED.value
    assert res.score == 0.0
    assert len(res.findings) == 3
    assert all(f.severity == QASeverity.CRITICAL.value for f in res.findings)
