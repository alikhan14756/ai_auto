"""Unit and component tests for FFmpeg detection, Command Builder, Mock Renderer, and Validation."""

import os
from pathlib import Path
import pytest
from app.services.video.detector import FFmpegDetector
from app.services.video.command_builder import FFmpegCommandBuilder
from app.services.video.renderer import MockVideoRenderer, VideoRenderingEngine
from app.services.video.validator import VideoValidationService


def test_ffmpeg_detector():
    """Verify binary detection returns consistent system status."""
    info = FFmpegDetector.detect()
    assert "ffmpeg" in info
    assert "ffprobe" in info
    assert "available" in info
    assert FFmpegDetector.is_available() is True or FFmpegDetector.is_available() is False


def test_ffmpeg_command_builder_basic(tmp_path):
    """Verify safe FFmpeg argument assembly without shell strings."""
    out_file = str(tmp_path / "test_out.mp4")
    cmd = FFmpegCommandBuilder.build_render_command(
        ffmpeg_bin="ffmpeg",
        scenes=[
            {"duration_seconds": 4.5, "motion_effect": "zoom_in"},
            {"duration_seconds": 3.0, "motion_effect": "static"},
        ],
        output_path=out_file,
        width=1920,
        height=1080,
        fps=30,
    )
    assert cmd[0] == "ffmpeg"
    assert "-y" in cmd
    assert "-filter_complex" in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert out_file in cmd


def test_ffmpeg_command_builder_audio_ducking(tmp_path):
    """Verify audio ducking sidechain compression graph construction."""
    narr_file = tmp_path / "narr.wav"
    narr_file.write_bytes(b"RIFF" + b"\x00" * 40)
    music_file = tmp_path / "music.mp3"
    music_file.write_bytes(b"ID3" + b"\x00" * 40)
    out_file = str(tmp_path / "ducked.mp4")

    cmd = FFmpegCommandBuilder.build_render_command(
        ffmpeg_bin="ffmpeg",
        scenes=[{"duration_seconds": 5.0}],
        output_path=out_file,
        narration_audio_path=str(narr_file),
        music_audio_path=str(music_file),
        ducking_enabled=True,
    )
    # Check that sidechaincompress and amix are included in the filtergraph
    filter_graph = " ".join(cmd)
    assert "sidechaincompress" in filter_graph
    assert "amix" in filter_graph


def test_mock_video_renderer(tmp_path):
    """Verify MockVideoRenderer synthesizes a structurally valid MP4 container."""
    out_file = str(tmp_path / "mock.mp4")
    res = MockVideoRenderer.render(
        output_path=out_file,
        duration_seconds=6.0,
        width=1920,
        height=1080,
    )
    assert res["status"] == "COMPLETED"
    assert res["renderer_mode"] == "mock"
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000

    # Low level header check
    with open(out_file, "rb") as f:
        head = f.read(32)
    assert head[4:8] == b"ftyp"
    assert b"mp42" in head


def test_video_validation_service_mock_file(tmp_path):
    """Verify VideoValidationService on mock MP4 container."""
    out_file = str(tmp_path / "test_valid.mp4")
    MockVideoRenderer.synthesize_valid_mp4(out_file, duration_seconds=8.0, width=1920, height=1080)

    report = VideoValidationService.validate_video(
        file_path=out_file,
        expected_width=1920,
        expected_height=1080,
        expected_duration_seconds=8.0,
        require_audio=False,
    )
    assert report["status"] == "PASSED"
    assert report["score"] >= 90.0
    assert report["metrics"]["file_size_bytes"] > 0


def test_video_validation_service_corrupted_file(tmp_path):
    """Verify VideoValidationService detects invalid containers."""
    corrupted_file = str(tmp_path / "corrupted.mp4")
    with open(corrupted_file, "wb") as f:
        f.write(b"NOT_AN_MP4_FILE_JUST_RANDOM_TEXT")

    report = VideoValidationService.validate_video(corrupted_file)
    assert report["status"] == "FAILED"
    assert report["score"] == 0.0
    assert len(report["issues"]) > 0


def test_real_or_mock_rendering_engine(tmp_path):
    """Verify VideoRenderingEngine renders cleanly in either real FFmpeg or fallback mock mode."""
    out_file = str(tmp_path / "engine_rendered.mp4")
    engine = VideoRenderingEngine(mode="auto")

    progress_events = []
    def on_progress(stage, pct, msg):
        progress_events.append((stage, pct))

    res = engine.render(
        scenes=[{"duration_seconds": 2.0, "motion_effect": "zoom_in"}],
        output_path=out_file,
        width=1920,
        height=1080,
        fps=30,
        progress_callback=on_progress,
    )
    assert res["status"] == "COMPLETED"
    assert os.path.exists(out_file)
    assert len(progress_events) > 0
    assert res["file_size_bytes"] > 0
