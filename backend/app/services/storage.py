"""Audio and Media Asset Storage Service with Local and Cloud Support."""

import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger


class StorageSecurityError(Exception):
    """Raised when an invalid or malicious file path is encountered."""
    pass


class StorageService:
    """Manages persistent media asset storage and secure retrieval."""

    def __init__(self, base_dir: Optional[str] = None):
        self._base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it does not escape base_dir (path traversal protection)."""
        clean_rel = relative_path.lstrip("/\\")
        target_path = (self._base_dir / clean_rel).resolve()
        try:
            if not target_path.is_relative_to(self._base_dir):
                raise StorageSecurityError(f"Path traversal detected: {relative_path}")
        except AttributeError:
            # Fallback for older python
            if self._base_dir not in target_path.parents and target_path != self._base_dir:
                raise StorageSecurityError(f"Path traversal detected: {relative_path}")
        return target_path

    async def save_audio_file(
        self,
        channel_id: UUID,
        project_id: UUID,
        filename: str,
        data: bytes,
    ) -> str:
        """Save audio file under storage/audio/{channel_id}/{project_id}/{filename}."""
        rel_path = f"audio/{channel_id}/{project_id}/{filename}"
        target_path = self._resolve_safe_path(rel_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write bytes
        with open(target_path, "wb") as f:
            f.write(data)

        logger.debug(f"Saved audio asset: {rel_path} ({len(data)} bytes)")
        return rel_path

    async def save_media_file(
        self,
        channel_id: UUID,
        filename: str,
        data: bytes,
    ) -> str:
        """Save media asset file under storage/media/{channel_id}/{filename}."""
        rel_path = f"media/{channel_id}/{filename}"
        target_path = self._resolve_safe_path(rel_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "wb") as f:
            f.write(data)

        logger.debug(f"Saved media asset: {rel_path} ({len(data)} bytes)")
        return rel_path

    async def read_media_file(self, relative_path: str) -> bytes:
        """Read media file bytes from storage."""
        return await self.read_audio_file(relative_path)

    async def read_audio_file(self, relative_path: str) -> bytes:
        """Read audio file bytes from storage."""
        target_path = self._resolve_safe_path(relative_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Storage asset not found: {relative_path}")

        with open(target_path, "rb") as f:
            return f.read()

    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute path after path traversal verification."""
        return self._resolve_safe_path(relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        """Delete file if it exists."""
        try:
            target_path = self._resolve_safe_path(relative_path)
            if target_path.exists():
                target_path.unlink()
                return True
            return False
        except Exception as exc:
            logger.warning(f"Could not delete storage file {relative_path}: {exc}")
            return False
