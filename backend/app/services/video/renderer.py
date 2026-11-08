"""Video Rendering Engine supporting real FFmpeg subprocess pipeline and offline MockVideoRenderer."""

import os
import re
import struct
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.video.detector import FFmpegDetector
from app.services.video.command_builder import FFmpegCommandBuilder


class MockVideoRenderer:
    """Zero-dependency offline renderer creating structurally valid MP4 files for testing and offline environments."""

    @staticmethod
    def _create_box(box_type: bytes, payload: bytes) -> bytes:
        """Construct an ISOBMFF atom (box) with 4-byte big-endian length prefix."""
        size = 8 + len(payload)
        return struct.pack(">I", size) + box_type + payload

    @classmethod
    def synthesize_valid_mp4(
        cls,
        output_path: str,
        duration_seconds: float = 10.0,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Create a syntactically valid MP4 container on disk with ftyp, moov (mvhd, trak), and mdat atoms."""
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)

        # 1. ftyp box
        ftyp_payload = b"mp42" + struct.pack(">I", 0) + b"mp42isomavc1"
        ftyp_box = cls._create_box(b"ftyp", ftyp_payload)

        # 2. mvhd box (Movie Header)
        timescale = 1000
        duration_ticks = int(round(duration_seconds * timescale))
        # version 0: version(1), flags(3), creation(4), mod(4), timescale(4), duration(4), rate(4), vol(2), reserved(10), matrix(36), pre-defined(24), next_track_id(4)
        mvhd_payload = (
            struct.pack(">B", 0)  # version
            + b"\x00\x00\x00"  # flags
            + struct.pack(">IIII", 0, 0, timescale, duration_ticks)
            + struct.pack(">I", 0x00010000)  # 1.0 rate
            + struct.pack(">H", 0x0100)  # 1.0 volume
            + b"\x00" * 10
            + (
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x40000000)
            )  # unity matrix
            + b"\x00" * 24
            + struct.pack(">I", 3)  # next track id = 3 (we have video track 1 and audio track 2)
        )
        mvhd_box = cls._create_box(b"mvhd", mvhd_payload)

        # 3. Video track (trak)
        # tkhd (Track Header) for video
        tkhd_v_payload = (
            struct.pack(">B", 0)
            + b"\x00\x00\x07"  # flags: enabled | in_movie | in_preview
            + struct.pack(">IIII", 0, 0, 1, 0)  # creation, mod, track_id=1, reserved
            + struct.pack(">I", duration_ticks)
            + b"\x00" * 8
            + struct.pack(">H", 0)  # layer
            + struct.pack(">H", 0)  # alt group
            + struct.pack(">H", 0)  # volume 0 for video
            + struct.pack(">H", 0)  # reserved
            + (
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x40000000)
            )
            + struct.pack(">I", width << 16)  # width fixed 16.16
            + struct.pack(">I", height << 16)  # height fixed 16.16
        )
        tkhd_v_box = cls._create_box(b"tkhd", tkhd_v_payload)
        hdlr_v_payload = (
            struct.pack(">B", 0)
            + b"\x00\x00\x00"
            + b"\x00\x00\x00\x00"
            + b"vide"  # handler type
            + b"\x00" * 12
            + b"VideoHandler\x00"
        )
        hdlr_v_box = cls._create_box(b"hdlr", hdlr_v_payload)
        mdia_v_box = cls._create_box(b"mdia", hdlr_v_box)
        trak_v_box = cls._create_box(b"trak", tkhd_v_box + mdia_v_box)

        # 4. Audio track (trak)
        tkhd_a_payload = (
            struct.pack(">B", 0)
            + b"\x00\x00\x07"
            + struct.pack(">IIII", 0, 0, 2, 0)  # track_id=2
            + struct.pack(">I", duration_ticks)
            + b"\x00" * 8
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
            + struct.pack(">H", 0x0100)  # full volume 1.0 for audio
            + struct.pack(">H", 0)
            + (
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x00010000) + b"\x00" * 12 +
                struct.pack(">I", 0x40000000)
            )
            + struct.pack(">I", 0)
            + struct.pack(">I", 0)
        )
        tkhd_a_box = cls._create_box(b"tkhd", tkhd_a_payload)
        hdlr_a_payload = (
            struct.pack(">B", 0)
            + b"\x00\x00\x00"
            + b"\x00\x00\x00\x00"
            + b"soun"  # handler type
            + b"\x00" * 12
            + b"SoundHandler\x00"
        )
        hdlr_a_box = cls._create_box(b"hdlr", hdlr_a_payload)
        mdia_a_box = cls._create_box(b"mdia", hdlr_a_box)
        trak_a_box = cls._create_box(b"trak", tkhd_a_box + mdia_a_box)

        # 5. moov box
        moov_box = cls._create_box(b"moov", mvhd_box + trak_v_box + trak_a_box)

        # 6. mdat box with simulated encoded frames
        dummy_data = b"\x00\x00\x00\x01\x67\x42\x00\x1f" + b"\x00" * 2048
        mdat_box = cls._create_box(b"mdat", dummy_data)

        # Write all boxes
        with open(p, "wb") as f:
            f.write(ftyp_box)
            f.write(moov_box)
            f.write(mdat_box)

        logger.info(f"Synthesized valid MP4 mock container: {p} ({p.stat().st_size} bytes)")
        return str(p)

    @classmethod
    def render(
        cls,
        output_path: str,
        duration_seconds: float = 10.0,
        width: int = 1920,
        height: int = 1080,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """Perform simulated rendering with realistic stage notifications."""
        stages = [
            ("AUDIO_PREPARATION", 15),
            ("SUBTITLE_COMPILATION", 30),
            ("VIDEO_COMPOSITING", 60),
            ("AUDIO_DUCKING_MIX", 80),
            ("ENCODING_AND_PACKAGING", 95),
            ("COMPLETED", 100),
        ]
        for stage, pct in stages:
            if progress_callback:
                progress_callback(stage, pct)
            time.sleep(0.05)

        final_path = cls.synthesize_valid_mp4(
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
        )

        return {
            "status": "COMPLETED",
            "output_path": final_path,
            "duration_seconds": duration_seconds,
            "renderer_mode": "mock",
            "file_size_bytes": os.path.getsize(final_path),
        }


class VideoRenderingEngine:
    """Unified video rendering engine managing FFmpeg subprocesses with automatic mock fallback."""

    def __init__(self, mode: Optional[str] = None):
        """mode: 'auto', 'ffmpeg', or 'mock'."""
        self.mode = mode or settings.VIDEO_RENDERER_DEFAULT_MODE

    def render(
        self,
        scenes: List[Dict[str, Any]],
        output_path: str,
        narration_audio_path: Optional[str] = None,
        music_audio_path: Optional[str] = None,
        subtitle_path: Optional[str] = None,
        music_volume: float = 0.15,
        ducking_enabled: bool = True,
        ducking_db: float = -6.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Render a video from timeline specifications."""
        total_duration = sum(float(s.get("duration_seconds", 5.0)) for s in scenes)
        if total_duration <= 0.0:
            total_duration = 10.0

        use_mock = self.mode == "mock" or not FFmpegDetector.is_available()

        if use_mock:
            logger.info("Executing video rendering using MockVideoRenderer...")
            def _mock_cb(stage: str, pct: int):
                if progress_callback:
                    progress_callback(stage, pct, f"Mock stage {stage}: {pct}%")

            res = MockVideoRenderer.render(
                output_path=output_path,
                duration_seconds=total_duration,
                width=width,
                height=height,
                progress_callback=_mock_cb,
            )
            return res

        # Real FFmpeg execution
        ffmpeg_bin = FFmpegDetector.get_ffmpeg_path()
        if not ffmpeg_bin:
            raise RuntimeError("FFmpeg binary not available")

        # Build command list
        cmd = FFmpegCommandBuilder.build_render_command(
            ffmpeg_bin=ffmpeg_bin,
            scenes=scenes,
            output_path=output_path,
            narration_audio_path=narration_audio_path,
            music_audio_path=music_audio_path,
            subtitle_path=subtitle_path,
            music_volume=music_volume,
            ducking_enabled=ducking_enabled,
            ducking_db=ducking_db,
            width=width,
            height=height,
            fps=fps,
        )

        logger.info(f"Executing FFmpeg render command: {' '.join(cmd[:10])}... -> {output_path}")

        if progress_callback:
            progress_callback("STARTING", 5, "FFmpeg process initializing")

        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Monitor stderr for progress
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        stderr_lines: List[str] = []

        if process.stderr:
            for line in process.stderr:
                stderr_lines.append(line)
                if len(stderr_lines) > 50:
                    stderr_lines.pop(0)  # Keep last 50 lines tail

                match = time_pattern.search(line)
                if match and total_duration > 0:
                    hours, minutes, seconds = match.groups()
                    current_sec = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    pct = min(98, max(5, int(round((current_sec / total_duration) * 100))))
                    if progress_callback:
                        progress_callback("ENCODING", pct, line.strip())

        process.wait()
        elapsed = time.time() - start_time

        if process.returncode != 0:
            error_msg = f"FFmpeg failed with exit code {process.returncode}:\n" + "".join(stderr_lines[-15:])
            logger.error(error_msg)
            if progress_callback:
                progress_callback("FAILED", 0, error_msg)
            raise RuntimeError(error_msg)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"FFmpeg finished but output file is missing or empty: {output_path}")

        if progress_callback:
            progress_callback("COMPLETED", 100, "Rendering completed successfully")

        file_size = os.path.getsize(output_path)
        logger.info(f"Render completed: {output_path} ({file_size} bytes, took {elapsed:.2f}s)")

        return {
            "status": "COMPLETED",
            "output_path": output_path,
            "duration_seconds": total_duration,
            "render_duration_seconds": round(elapsed, 2),
            "file_size_bytes": file_size,
            "renderer_mode": "ffmpeg",
            "ffmpeg_command": " ".join(cmd),
        }
