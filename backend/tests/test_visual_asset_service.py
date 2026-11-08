"""Tests for VisualAssetService (magic bytes, SHA-256 hashing, uploads, and licensing)."""

import io
import pytest
import uuid
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.media import MediaAsset
from app.services.storage import StorageService, StorageSecurityError
from app.services.visual_asset import VisualAssetService, AssetSecurityError
from app.providers.visual.base import StockAssetResult


def _create_sample_png_bytes() -> bytes:
    """Create a minimal valid PNG image byte stream."""
    img = Image.new("RGB", (100, 100), color=(255, 122, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_sample_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG image byte stream."""
    img = Image.new("RGB", (100, 100), color=(9, 10, 13))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_magic_byte_detection():
    """Verify magic bytes sniffing correctly classifies formats and rejects invalid payloads."""
    png_bytes = _create_sample_png_bytes()
    assert VisualAssetService.detect_mime_type_from_magic_bytes(png_bytes) == "image/png"

    jpeg_bytes = _create_sample_jpeg_bytes()
    assert VisualAssetService.detect_mime_type_from_magic_bytes(jpeg_bytes) == "image/jpeg"

    # Invalid payload
    with pytest.raises(AssetSecurityError):
        VisualAssetService.detect_mime_type_from_magic_bytes(b"<html><script>alert(1)</script></html>")

    # Short payload
    with pytest.raises(AssetSecurityError):
        VisualAssetService.detect_mime_type_from_magic_bytes(b"short")


def test_sha256_calculation():
    """Verify SHA-256 calculation produces deterministic 64-char hex strings."""
    data = b"Creator Studio AI asset payload"
    h1 = VisualAssetService.calculate_sha256(data)
    h2 = VisualAssetService.calculate_sha256(data)
    assert h1 == h2
    assert len(h1) == 64


def test_storage_security_path_traversal(tmp_path):
    """Verify StorageService rejects malicious path traversal attempts."""
    storage = StorageService(base_dir=str(tmp_path))
    with pytest.raises(StorageSecurityError):
        storage.get_absolute_path("../../etc/passwd")

    with pytest.raises(StorageSecurityError):
        storage.get_absolute_path("/../windows/system32")


@pytest.mark.asyncio
async def test_upload_and_assign_asset(db_session: AsyncSession, tmp_path):
    """Verify secure asset uploading, SHA-256 persistence, and scene assignment."""
    storage = StorageService(base_dir=str(tmp_path))
    service = VisualAssetService(storage_service=storage)

    channel_id = uuid.uuid4()
    project_id = uuid.uuid4()
    scene_id = uuid.uuid4()

    channel = Channel(
        id=channel_id,
        user_id=uuid.uuid4(),
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:12]}",
        title="Asset Channel",
        oauth_refresh_token_encrypted="mock_token",
    )
    project = VideoProject(
        id=project_id,
        channel_id=channel_id,
        title="Asset Project",
        state="SCRIPT_APPROVED",
    )
    scene = Scene(
        id=scene_id,
        project_id=project_id,
        scene_order=1,
        narration_text="Scene to receive asset",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Test visual directive",
        duration_seconds=3.0,
    )
    db_session.add_all([channel, project, scene])
    await db_session.commit()

    png_bytes = _create_sample_png_bytes()

    # Upload custom asset
    asset = await service.upload_asset(
        db=db_session,
        channel_id=channel_id,
        project_id=project_id,
        filename="custom_diagram.png",
        data=png_bytes,
        title="Custom Architecture Diagram",
        scene_id=scene_id,
    )

    assert asset is not None
    assert asset.channel_id == channel_id
    assert asset.asset_category == "USER_UPLOADED"
    assert asset.sha256_hash == VisualAssetService.calculate_sha256(png_bytes)
    assert asset.file_size_bytes == len(png_bytes)
    assert asset.is_verified is True

    # Check that scene received assignment
    await db_session.refresh(scene)
    assert scene.selected_asset_id == asset.id
    assert scene.review_status == "SUGGESTED"

    # Test file retrieval from storage
    retrieved_bytes = await service.get_asset_file_bytes(asset)
    assert retrieved_bytes == png_bytes


@pytest.mark.asyncio
async def test_update_asset_licensing(db_session: AsyncSession, tmp_path):
    """Verify updating licensing provenance and attribution notes."""
    storage = StorageService(base_dir=str(tmp_path))
    service = VisualAssetService(storage_service=storage)

    channel_id = uuid.uuid4()
    project_id = uuid.uuid4()
    channel = Channel(
        id=channel_id,
        user_id=uuid.uuid4(),
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:12]}",
        title="License Channel",
        oauth_refresh_token_encrypted="mock_token",
    )
    project = VideoProject(
        id=project_id,
        channel_id=channel_id,
        title="License Project",
        state="SCRIPT_APPROVED",
    )
    db_session.add_all([channel, project])
    await db_session.commit()

    stock_item = StockAssetResult(
        external_id="ext-stock-123",
        title="Unverified Cloud Diagram",
        preview_url="https://example.com/preview.jpg",
        download_url="https://example.com/download.jpg",
        source_provider="MOCK",
        source_url="https://example.com/source",
        author_name="External Contributor",
        license_type="CUSTOM",
        license_status="LICENSE_REVIEW_REQUIRED",
    )

    imported_asset = await service.import_stock_asset(
        db=db_session,
        channel_id=channel_id,
        project_id=project_id,
        stock_item=stock_item,
    )
    assert imported_asset.license_status == "LICENSE_REVIEW_REQUIRED"

    # Update license after manual review
    updated = await service.update_asset_license(
        db=db_session,
        asset_id=imported_asset.id,
        license_status="VERIFIED_COMMERCIAL",
        attribution_text="Cleared for commercial use by Creator Studio QA",
        license_type="CC_BY_4_0",
    )
    assert updated.license_status == "VERIFIED_COMMERCIAL"
    assert updated.attribution_text == "Cleared for commercial use by Creator Studio QA"
    assert updated.license_type == "CC_BY_4_0"
