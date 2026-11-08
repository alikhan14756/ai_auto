"""Tests for YouTube Resumable Upload protocol, chunk streaming, and interruption recovery."""

import os
import tempfile
import pytest
from app.services.youtube.resumable_uploader import YouTubeResumableUploader
from app.services.youtube.mock_client import mock_youtube_client


@pytest.fixture
def dummy_video_file():
    """Create a temporary video file of 64KB for chunked upload tests."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # 64 KB of payload
        f.write(b"CREATOR_STUDIO_AI_TEST_VIDEO_CHUNK_DATA_" * 1600)
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def dummy_thumbnail_file():
    """Create a temporary dummy JPEG file for thumbnail upload tests."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 2000)
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_resumable_upload_initiation_and_chunked_streaming(dummy_video_file):
    """Test full resumable upload session creation and chunk streaming."""
    mock_youtube_client.reset()

    snippet = {
        "title": "Autonomous AI Agent Tutorial",
        "description": "Building full lifecycle production pipelines",
        "tags": ["ai", "automation"],
        "categoryId": "28",
    }
    status = {
        "privacyStatus": "unlisted",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    }

    # 1. Initiate session
    session_uri, file_size = await YouTubeResumableUploader.initiate_upload_session(
        access_token="mock_token",
        file_path=dummy_video_file,
        snippet=snippet,
        status_dict=status,
    )
    assert "uploadType=resumable" in session_uri
    assert file_size == os.path.getsize(dummy_video_file)

    # 2. Track progress with callback
    progress_records = []

    async def callback(uploaded: int, total: int):
        progress_records.append((uploaded, total))

    # Stream in 16KB chunks
    result = await YouTubeResumableUploader.upload_file(
        session_uri=session_uri,
        file_path=dummy_video_file,
        chunk_size=16 * 1024,
        progress_callback=callback,
    )

    assert "id" in result
    assert result["id"].startswith("yt_")
    assert len(progress_records) > 0
    final_uploaded, total_expected = progress_records[-1]
    assert final_uploaded == total_expected == file_size


@pytest.mark.asyncio
async def test_resumable_upload_interruption_and_status_recovery(dummy_video_file):
    """Test network drop mid-upload, status query (HTTP 308 Range), and resuming from byte offset."""
    mock_youtube_client.reset()

    session_uri, file_size = await YouTubeResumableUploader.initiate_upload_session(
        access_token="mock_token",
        file_path=dummy_video_file,
        snippet={"title": "Interruption Test"},
        status_dict={"privacyStatus": "unlisted"},
    )

    # Simulate network drop after chunk 1
    session_state = mock_youtube_client._sessions[session_uri]
    session_state.simulate_network_drop = True

    # Upload should encounter simulated socket drop, query status 308, and recover automatically!
    result = await YouTubeResumableUploader.upload_file(
        session_uri=session_uri,
        file_path=dummy_video_file,
        chunk_size=16 * 1024,
    )

    assert "id" in result
    assert result["id"].startswith("yt_")
    assert session_state.completed is True


@pytest.mark.asyncio
async def test_thumbnail_upload_attachment(dummy_thumbnail_file):
    """Verify thumbnail upload and API response parsing."""
    mock_youtube_client.reset()

    video_id = "yt_test_video_12345"
    thumb_res = await YouTubeResumableUploader.upload_thumbnail(
        access_token="mock_token",
        video_id=video_id,
        thumbnail_path=dummy_thumbnail_file,
    )

    assert thumb_res["kind"] == "youtube#thumbnailSetResponse"
    assert "items" in thumb_res
    items = thumb_res["items"]
    assert len(items) > 0
    assert items[0]["maxres"]["width"] == 1280
