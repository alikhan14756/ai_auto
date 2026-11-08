"""End-to-end integration tests for Thumbnails, SEO Metadata, Publication Packages, and Worker Handlers."""

import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.render import RenderJob
from app.models.thumbnail import Thumbnail
from app.models.metadata import VideoMetadataDraft
from app.models.publication import PublicationPackage
from app.workers.handlers.thumbnail_seo import (
    ThumbnailConceptGenerationJobHandler,
    ThumbnailCompositionRenderJobHandler,
    SEOMetadataGenerationJobHandler,
    PublicationPackagePreparationJobHandler,
)


def test_thumbnail_and_seo_api_lifecycle(client, test_user, test_channel):
    """Test full API journey for Thumbnail Studio, SEO Metadata Studio, and Publication Assembly."""
    headers = auth_headers_for(test_user)

    # 1. Create a project
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "channel_id": str(test_channel.id),
            "title": "M10 Thumbnail and SEO Architecture Test",
            "format": "LONG_FORM",
        },
        headers=headers,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Test Queue Enqueue Endpoints (Validates JobQueueService fix)
    q_thumb = client.post(
        "/api/v1/thumbnails/queue/generate",
        json={"project_id": project_id},
        headers=headers,
    )
    assert q_thumb.status_code == 202
    assert q_thumb.json()["job_type"] == "THUMBNAIL_CONCEPT_GENERATION"

    q_meta = client.post(
        "/api/v1/metadata/queue/generate",
        json={"project_id": project_id},
        headers=headers,
    )
    assert q_meta.status_code == 202
    assert q_meta.json()["job_type"] == "SEO_METADATA_GENERATION"

    q_pub = client.post(
        "/api/v1/publication-packages/queue/prepare",
        json={"project_id": project_id},
        headers=headers,
    )
    assert q_pub.status_code == 202
    assert q_pub.json()["job_type"] == "PUBLICATION_PACKAGE_PREPARATION"

    # 3. POST /api/v1/thumbnails/generate
    gen_thumb_res = client.post(
        "/api/v1/thumbnails/generate",
        json={"project_id": project_id},
        headers=headers,
    )
    assert gen_thumb_res.status_code == 201
    thumbs = gen_thumb_res.json()
    assert len(thumbs) == 3
    assert set(t["variant_code"] for t in thumbs) == {"A", "B", "C"}
    for t in thumbs:
        assert t["width"] == 1280
        assert t["height"] == 720
        assert t["format"] == "PNG"
        assert t["quality_status"] == "PASSED"

    variant_a = thumbs[0]
    variant_a_id = variant_a["id"]

    # 4. GET /api/v1/thumbnails/project/{project_id}
    list_thumbs = client.get(f"/api/v1/thumbnails/project/{project_id}", headers=headers)
    assert list_thumbs.status_code == 200
    assert len(list_thumbs.json()) == 3

    # 5. GET /api/v1/thumbnails/{thumbnail_id}
    get_thumb = client.get(f"/api/v1/thumbnails/{variant_a_id}", headers=headers)
    assert get_thumb.status_code == 200
    assert get_thumb.json()["id"] == variant_a_id

    # 6. PATCH /api/v1/thumbnails/{thumbnail_id}
    patch_thumb = client.patch(
        f"/api/v1/thumbnails/{variant_a_id}",
        json={
            "headline_text": "UPDATED HEADLINE TEXT",
            "badge_text": "UPDATED BADGE",
            "style_preset": "high_contrast_educational",
            "accent_color": "#06B6D4",
        },
        headers=headers,
    )
    assert patch_thumb.status_code == 200
    p_data = patch_thumb.json()
    assert p_data["headline_text"] == "UPDATED HEADLINE TEXT"
    assert p_data["style_preset"] == "high_contrast_educational"
    assert p_data["accent_color_hex"] == "#06B6D4"

    # 7. POST /api/v1/thumbnails/{thumbnail_id}/select
    select_res = client.post(f"/api/v1/thumbnails/{variant_a_id}/select", headers=headers)
    assert select_res.status_code == 200
    assert select_res.json()["is_selected"] is True

    # 8. GET /api/v1/thumbnails/{thumbnail_id}/file
    stream_res = client.get(f"/api/v1/thumbnails/{variant_a_id}/file", headers=headers)
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"] == "image/png"
    assert len(stream_res.content) > 0

    # 9. POST /api/v1/thumbnails/validate (Valid file)
    val_res = client.post(
        "/api/v1/thumbnails/validate",
        json={"file_path": p_data["storage_path"]},
        headers=headers,
    )
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # 10. Path Traversal Boundary Test for /validate
    bad_val = client.post(
        "/api/v1/thumbnails/validate",
        json={"file_path": "../../etc/shadow"},
        headers=headers,
    )
    assert bad_val.status_code == 403

    # 11. POST /api/v1/metadata/generate
    gen_meta_res = client.post(
        "/api/v1/metadata/generate",
        json={"project_id": project_id},
        headers=headers,
    )
    assert gen_meta_res.status_code == 201
    meta = gen_meta_res.json()
    meta_id = meta["id"]
    assert len(meta["title"]) <= 95
    assert len(meta["chapters"]) >= 3
    assert meta["chapters"][0]["timestamp"] == "00:00"
    assert meta["synthetic_media_disclosure"] is True
    assert meta["seo_score"] >= 80.0

    # 12. GET /api/v1/metadata/project/{project_id}
    list_meta = client.get(f"/api/v1/metadata/project/{project_id}", headers=headers)
    assert list_meta.status_code == 200
    assert len(list_meta.json()) >= 1

    # 13. PATCH /api/v1/metadata/{metadata_id}
    patch_meta = client.patch(
        f"/api/v1/metadata/{meta_id}",
        json={"title": "Custom High-CTR YouTube Title for Production Queues"},
        headers=headers,
    )
    assert patch_meta.status_code == 200
    assert patch_meta.json()["title"] == "Custom High-CTR YouTube Title for Production Queues"

    # 14. POST /api/v1/metadata/{metadata_id}/approve
    appr_meta = client.post(f"/api/v1/metadata/{meta_id}/approve", headers=headers)
    assert appr_meta.status_code == 200
    assert appr_meta.json()["is_approved"] is True

    # 15. POST /api/v1/publication-packages (Without completed render -> status DRAFT)
    pkg_res = client.post(
        "/api/v1/publication-packages",
        json={"project_id": project_id},
        headers=headers,
    )
    assert pkg_res.status_code == 201
    pkg = pkg_res.json()
    pkg_id = pkg["id"]
    assert pkg["status"] == "DRAFT"

    # Attempting to approve incomplete DRAFT package should fail with 400
    bad_appr = client.post(f"/api/v1/publication-packages/{pkg_id}/approve", headers=headers)
    assert bad_appr.status_code == 400

    # Now add a completed RenderJob and reassemble
    import asyncio
    async def add_render_and_reassemble():
        async with TestingSessionLocal() as db:
            rj = RenderJob(
                id=uuid.uuid4(),
                project_id=uuid.UUID(project_id),
                status="COMPLETED",
                output_video_path="storage/renders/test_master.mp4",
            )
            db.add(rj)
            await db.commit()

    asyncio.run(add_render_and_reassemble())

    # Reassemble: should now be READY_FOR_QA
    pkg_res2 = client.post(
        "/api/v1/publication-packages",
        json={"project_id": project_id},
        headers=headers,
    )
    assert pkg_res2.status_code == 201
    assert pkg_res2.json()["status"] == "READY_FOR_QA"

    # Now approve succeeds
    appr_pkg = client.post(f"/api/v1/publication-packages/{pkg_id}/approve", headers=headers)
    assert appr_pkg.status_code == 200
    assert appr_pkg.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_thumbnail_and_seo_worker_handlers(db_session, test_user, test_channel):
    """Test background worker execution for all 4 M10 job types."""
    # 1. Create project
    proj = VideoProject(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        title="Async Worker M10 Execution Test",
        format="LONG_FORM",
        state="IDEA",
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    progress_log = []
    async def mock_progress(pct: int, msg: str):
        progress_log.append((pct, msg))

    async def mock_is_cancelled():
        return False

    # Handler 1: ThumbnailConceptGenerationJobHandler
    concept_handler = ThumbnailConceptGenerationJobHandler(session_factory=lambda: db_session)
    job1 = AutomationJob(
        id=uuid.uuid4(),
        job_type="THUMBNAIL_CONCEPT_GENERATION",
        payload={"project_id": str(proj.id), "user_id": str(test_user.id)},
    )
    await concept_handler.validate(job1.payload)
    res1 = await concept_handler.execute(job1, mock_progress, mock_is_cancelled)
    assert res1["variant_count"] == 3
    assert len(res1["thumbnails"]) == 3

    # Handler 2: ThumbnailCompositionRenderJobHandler
    thumb_id = res1["thumbnails"][0]["thumbnail_id"]
    render_handler = ThumbnailCompositionRenderJobHandler(session_factory=lambda: db_session)
    job2 = AutomationJob(
        id=uuid.uuid4(),
        job_type="THUMBNAIL_COMPOSITION_RENDER",
        payload={
            "thumbnail_id": thumb_id,
            "user_id": str(test_user.id),
            "headline_text": "RE-RENDERED HEADLINE",
            "style_preset": "software_tutorial",
        },
    )
    await render_handler.validate(job2.payload)
    res2 = await render_handler.execute(job2, mock_progress, mock_is_cancelled)
    assert res2["quality_status"] == "PASSED"

    # Handler 3: SEOMetadataGenerationJobHandler
    seo_handler = SEOMetadataGenerationJobHandler(session_factory=lambda: db_session)
    job3 = AutomationJob(
        id=uuid.uuid4(),
        job_type="SEO_METADATA_GENERATION",
        payload={"project_id": str(proj.id), "user_id": str(test_user.id)},
    )
    await seo_handler.validate(job3.payload)
    res3 = await seo_handler.execute(job3, mock_progress, mock_is_cancelled)
    assert "metadata_id" in res3
    assert res3["seo_score"] >= 80.0

    # Handler 4: PublicationPackagePreparationJobHandler
    pub_handler = PublicationPackagePreparationJobHandler(session_factory=lambda: db_session)
    job4 = AutomationJob(
        id=uuid.uuid4(),
        job_type="PUBLICATION_PACKAGE_PREPARATION",
        payload={"project_id": str(proj.id), "user_id": str(test_user.id)},
    )
    await pub_handler.validate(job4.payload)
    res4 = await pub_handler.execute(job4, mock_progress, mock_is_cancelled)
    assert "package_id" in res4
    assert res4["status"] in ["DRAFT", "READY_FOR_QA"]
