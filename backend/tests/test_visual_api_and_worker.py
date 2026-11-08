"""Comprehensive integration tests for Visual Storyboard & Media REST API and Worker Handlers."""

import io
import pytest
from uuid import uuid4
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script
from app.models.user import User
from app.models.storyboard import Storyboard
from app.models.media import MediaAsset
from app.workers.handlers.visual import (
    StoryboardGenerationJobHandler,
    VisualAssetSearchJobHandler,
    ImageGenerationJobHandler,
)


def _sample_png() -> bytes:
    img = Image.new("RGB", (80, 80), color=(255, 122, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_visual_api_storyboard_workflow(client, test_user, test_channel, db_session):
    """End-to-end integration test of storyboard generation, scene update, asset assignment, and approval."""
    headers = auth_headers_for(test_user)

    # 1. Create Project, Script, and Scene
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "channel_id": str(test_channel.id),
            "title": "Visual Studio Integration Test",
            "format": "LONG_FORM",
        },
        headers=headers,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # Add script synchronously
    s_resp = client.post(
        "/api/v1/scripts/sync",
        json={
            "project_id": project_id,
            "target_duration_seconds": 60,
        },
        headers=headers,
    )
    assert s_resp.status_code == 201

    # 2. Generate Storyboard
    sb_gen_resp = client.post(
        "/api/v1/visual/storyboards/generate",
        json={"project_id": project_id},
        headers=headers,
    )
    assert sb_gen_resp.status_code == 200
    sb_data = sb_gen_resp.json()
    storyboard_id = sb_data["id"]
    assert sb_data["status"] == "DRAFT"
    assert sb_data["aspect_ratio"] == "16:9"
    assert len(sb_data["scenes"]) > 0
    first_scene_id = sb_data["scenes"][0]["id"]

    # 3. Retrieve Storyboard
    sb_get_resp = client.get(
        f"/api/v1/visual/storyboards/project/{project_id}",
        headers=headers,
    )
    assert sb_get_resp.status_code == 200
    assert sb_get_resp.json()["id"] == storyboard_id

    # 4. Update Scene Directive and Keywords
    up_resp = client.put(
        f"/api/v1/visual/storyboards/{storyboard_id}/scenes/{first_scene_id}",
        json={
            "visual_directive": "Updated custom animated code typing directive",
            "visual_purpose": "DEMONSTRATION",
            "suggested_asset_type": "CODE_DEMONSTRATION",
            "transition": "ZOOM_IN",
        },
        headers=headers,
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["visual_purpose"] == "DEMONSTRATION"

    # 5. Search Stock Media
    search_resp = client.post(
        "/api/v1/visual/assets/search",
        json={"query": "terminal python", "aspect_ratio": "16:9"},
        headers=headers,
    )
    assert search_resp.status_code == 200
    search_results = search_resp.json()
    assert search_results["total_results"] > 0
    stock_item = search_results["assets"][0]

    # 6. Import Stock Asset and Assign to Scene
    import_resp = client.post(
        "/api/v1/visual/assets/import-external",
        json={
            "channel_id": str(test_channel.id),
            "project_id": project_id,
            "scene_id": first_scene_id,
            "stock_item": stock_item,
        },
        headers=headers,
    )
    assert import_resp.status_code == 200
    asset_data = import_resp.json()
    assert asset_data["asset_category"] == "EXTERNAL_STOCK"

    # 7. Generate AI Image for Scene
    gen_resp = client.post(
        f"/api/v1/visual/storyboards/{storyboard_id}/scenes/{first_scene_id}/generate-image",
        json={
            "channel_id": str(test_channel.id),
            "project_id": project_id,
            "prompt": "Futuristic isometric microservices flowchart",
            "aspect_ratio": "16:9",
            "provider": "MOCK",
        },
        headers=headers,
    )
    assert gen_resp.status_code == 200
    gen_asset = gen_resp.json()
    assert gen_asset["asset_category"] == "GENERATED"
    assert gen_asset["license_status"] == "VERIFIED_COMMERCIAL"

    # 8. Upload Custom Asset (Multipart)
    png_bytes = _sample_png()
    upload_resp = client.post(
        "/api/v1/visual/assets/upload",
        data={
            "channel_id": str(test_channel.id),
            "project_id": project_id,
            "title": "Uploaded Test Logo",
            "scene_id": first_scene_id,
        },
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    uploaded_asset = upload_resp.json()
    assert uploaded_asset["asset_category"] == "USER_UPLOADED"

    # 9. Stream Binary File (Authenticated)
    file_resp = client.get(f"/api/v1/visual/assets/{uploaded_asset['id']}/file", headers=headers)
    assert file_resp.status_code == 200
    assert "image/png" in file_resp.headers["content-type"]
    assert len(file_resp.content) == len(png_bytes)

    # 9b. Verify unauthenticated file streaming is rejected (Security Fix)
    unauth_file_resp = client.get(f"/api/v1/visual/assets/{uploaded_asset['id']}/file")
    assert unauth_file_resp.status_code in (401, 403)

    # 10. Update License Status
    lic_resp = client.patch(
        f"/api/v1/visual/assets/{uploaded_asset['id']}/license",
        json={
            "license_status": "ATTRIBUTION_REQUIRED",
            "attribution_text": "Icon by Muhammad Ali",
        },
        headers=headers,
    )
    assert lic_resp.status_code == 200
    assert lic_resp.json()["license_status"] == "ATTRIBUTION_REQUIRED"

    # 11. List Assets with Filter
    list_resp = client.get(f"/api/v1/visual/assets?channel_id={test_channel.id}", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2

    # 12. Approve Storyboard
    appr_resp = client.post(
        f"/api/v1/visual/storyboards/{storyboard_id}/approve",
        headers=headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_visual_worker_handlers():
    """Verify background worker handlers for Storyboard, Stock Search, and Image Gen."""
    progress_records = []

    async def mock_progress(pct: int, stage: str, message: str):
        progress_records.append((pct, stage, message))

    async def mock_cancel() -> bool:
        return False

    # 1. Test VisualAssetSearchJobHandler
    search_handler = VisualAssetSearchJobHandler(session_factory=TestingSessionLocal)
    search_job = AutomationJob(
        channel_id=uuid4(),
        job_type="VISUAL_ASSET_SEARCH",
        payload={"query": "python async", "aspect_ratio": "16:9", "provider": "MOCK"},
        idempotency_key=f"search-{uuid4()}",
    )
    search_res = await search_handler.execute(search_job, mock_progress, mock_cancel)
    assert search_res["total_results"] > 0
    assert len(search_res["assets"]) > 0

    # 2. Test ImageGenerationJobHandler
    channel_id = uuid4()
    project_id = uuid4()

    async with TestingSessionLocal() as session:
        channel = Channel(
            id=channel_id,
            user_id=uuid4(),
            youtube_channel_id=f"UC_{uuid4().hex[:12]}",
            title="Worker Channel",
            oauth_refresh_token_encrypted="mock_token",
        )
        project = VideoProject(
            id=project_id,
            channel_id=channel_id,
            title="Worker Project",
            state="SCRIPT_APPROVED",
        )
        session.add_all([channel, project])
        await session.commit()

    img_handler = ImageGenerationJobHandler(session_factory=TestingSessionLocal)
    img_job = AutomationJob(
        channel_id=channel_id,
        job_type="IMAGE_GENERATION",
        payload={
            "channel_id": str(channel_id),
            "project_id": str(project_id),
            "prompt": "Dark mode code editor with amber accents",
            "aspect_ratio": "16:9",
            "provider": "MOCK",
        },
        idempotency_key=f"img-gen-{uuid4()}",
    )
    img_res = await img_handler.execute(img_job, mock_progress, mock_cancel)
    assert img_res["asset_id"] is not None
    assert img_res["width"] == 1280
    assert img_res["height"] == 720
    assert len(img_res["sha256_hash"]) == 64
