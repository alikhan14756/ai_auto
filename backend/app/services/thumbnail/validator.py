"""Deterministic Thumbnail Quality Assurance and Specification Validator."""

import os
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image
from app.core.config import settings
from app.core.logging import logger


class ThumbnailValidator:
    """Validates thumbnail compliance against YouTube specification standards."""

    REQUIRED_WIDTH = 1280
    REQUIRED_HEIGHT = 720
    MAX_FILE_SIZE_BYTES = 2097152  # 2.0 MB
    SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG"}

    @classmethod
    def validate_thumbnail(
        cls,
        file_path: str,
        expected_width: int = 1280,
        expected_height: int = 720,
    ) -> Dict[str, Any]:
        """Run programmatic validation checks on thumbnail image asset."""
        issues: List[str] = []
        score = 100.0

        if not os.path.exists(file_path):
            return {
                "valid": False,
                "status": "FAILED",
                "score": 0.0,
                "issues": ["Thumbnail file does not exist on disk."],
                "metrics": {"file_exists": False},
            }

        file_size = os.path.getsize(file_path)
        metrics: Dict[str, Any] = {
            "file_exists": True,
            "file_size_bytes": file_size,
            "max_allowed_bytes": cls.MAX_FILE_SIZE_BYTES,
        }

        # 1. File size check (< 2MB)
        if file_size > cls.MAX_FILE_SIZE_BYTES:
            issues.append(f"File size {file_size} exceeds YouTube limit of {cls.MAX_FILE_SIZE_BYTES} bytes (2.0 MB)")
            score -= 40.0
        elif file_size < 1024:
            issues.append("File size unexpectedly small (< 1KB), possible corrupted image")
            score -= 30.0

        # 2. Image integrity and dimension check
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                img_format = (img.format or "").upper()
                metrics["width"] = w
                metrics["height"] = h
                metrics["format"] = img_format
                metrics["aspect_ratio"] = round(w / float(h), 3) if h > 0 else 0.0

                if img_format not in cls.SUPPORTED_FORMATS:
                    issues.append(f"Format {img_format} not supported. Must be PNG or JPEG.")
                    score -= 30.0

                if w != expected_width or h != expected_height:
                    issues.append(
                        f"Dimension mismatch: expected {expected_width}x{expected_height}, got {w}x{h}"
                    )
                    score -= 35.0

                # Check 16:9 aspect ratio tolerance
                aspect = w / float(h) if h > 0 else 0.0
                if abs(aspect - (16.0 / 9.0)) > 0.02:
                    issues.append(f"Aspect ratio {aspect:.3f} deviates from standard 16:9 (1.778)")
                    score -= 20.0

        except Exception as e:
            logger.warning(f"Failed to inspect image {file_path}: {e}")
            return {
                "valid": False,
                "status": "FAILED",
                "score": 0.0,
                "issues": [f"Image file is unreadable or corrupted: {str(e)}"],
                "metrics": metrics,
            }

        score = max(0.0, score)
        if score >= 90.0:
            status = "PASSED"
        elif score >= 60.0:
            status = "WARNING"
        else:
            status = "FAILED"

        return {
            "valid": (status == "PASSED"),
            "status": status,
            "score": score,
            "issues": issues,
            "metrics": metrics,
        }
