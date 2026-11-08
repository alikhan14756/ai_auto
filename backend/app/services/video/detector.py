"""FFmpeg and FFprobe binary detection and capability inspection."""

import glob
import os
import shutil
import subprocess
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger


class FFmpegDetector:
    """Discovers host FFmpeg/FFprobe binaries and validates available codecs/filters."""

    _ffmpeg_path: Optional[str] = None
    _ffprobe_path: Optional[str] = None
    _detected: bool = False
    _codecs: Optional[List[str]] = None
    _filters: Optional[List[str]] = None

    @classmethod
    def reset(cls) -> None:
        """Reset cached detection state (useful in testing)."""
        cls._ffmpeg_path = None
        cls._ffprobe_path = None
        cls._detected = False
        cls._codecs = None
        cls._filters = None

    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        """Locate ffmpeg binary on the host system."""
        if not cls._detected:
            cls.detect()
        return cls._ffmpeg_path

    @classmethod
    def get_ffprobe_path(cls) -> Optional[str]:
        """Locate ffprobe binary on the host system."""
        if not cls._detected:
            cls.detect()
        return cls._ffprobe_path

    @classmethod
    def is_available(cls) -> bool:
        """Check if both ffmpeg and ffprobe are available."""
        if not cls._detected:
            cls.detect()
        return bool(cls._ffmpeg_path and cls._ffprobe_path)

    @classmethod
    def detect(cls) -> Dict[str, Optional[str]]:
        """Inspect environment, PATH, and standard Windows/Unix locations."""
        cls._detected = True

        # 1. Check settings or environment override
        candidate_ffmpeg = settings.FFMPEG_PATH or os.environ.get("FFMPEG_PATH")
        candidate_ffprobe = settings.FFPROBE_PATH or os.environ.get("FFPROBE_PATH")

        # 2. Check PATH
        if not candidate_ffmpeg:
            candidate_ffmpeg = shutil.which("ffmpeg")
        if not candidate_ffprobe:
            candidate_ffprobe = shutil.which("ffprobe")

        # 3. Check Windows specific install locations if on Windows
        if os.name == "nt":
            common_patterns = [
                os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*"),
                os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links"),
                r"C:\Program Files\ffmpeg\bin",
                r"C:\ffmpeg\bin",
                r"C:\ProgramData\chocolatey\bin",
            ]
            for pattern in common_patterns:
                matched_dirs = glob.glob(pattern)
                for directory in matched_dirs:
                    if not candidate_ffmpeg:
                        # Direct or recursive check for ffmpeg.exe
                        f_path = os.path.join(directory, "ffmpeg.exe")
                        if os.path.isfile(f_path):
                            candidate_ffmpeg = f_path
                        else:
                            for root, _, files in os.walk(directory):
                                if "ffmpeg.exe" in files:
                                    candidate_ffmpeg = os.path.join(root, "ffmpeg.exe")
                                    break
                    if not candidate_ffprobe:
                        p_path = os.path.join(directory, "ffprobe.exe")
                        if os.path.isfile(p_path):
                            candidate_ffprobe = p_path
                        else:
                            for root, _, files in os.walk(directory):
                                if "ffprobe.exe" in files:
                                    candidate_ffprobe = os.path.join(root, "ffprobe.exe")
                                    break

        # Validate by executing -version
        if candidate_ffmpeg and cls._verify_binary(candidate_ffmpeg, ["-version"]):
            cls._ffmpeg_path = candidate_ffmpeg
        else:
            cls._ffmpeg_path = None

        if candidate_ffprobe and cls._verify_binary(candidate_ffprobe, ["-version"]):
            cls._ffprobe_path = candidate_ffprobe
        else:
            cls._ffprobe_path = None

        logger.info(
            f"FFmpeg detection result: ffmpeg={cls._ffmpeg_path}, ffprobe={cls._ffprobe_path}, available={cls.is_available()}"
        )
        return {
            "ffmpeg": cls._ffmpeg_path,
            "ffprobe": cls._ffprobe_path,
            "available": str(cls.is_available()),
        }

    @classmethod
    def _verify_binary(cls, binary_path: str, args: List[str]) -> bool:
        """Run a quick verification command to ensure binary is runnable."""
        try:
            res = subprocess.run(
                [binary_path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
            return res.returncode == 0
        except Exception as e:
            logger.debug(f"Failed to execute {binary_path}: {e}")
            return False
