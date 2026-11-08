"""YouTube Resumable Uploader Protocol Implementation with Interruption Recovery.

Implements the official Google Resumable Media Upload protocol:
- Initial metadata handshake to acquire a unique resumable session URI
- Chunked multi-part streaming (multiples of 256 KiB)
- Byte-range status polling (`bytes */total_size`) on network drops
- Resumption from the exact byte offset confirmed by Google servers
- Exponential backoff with jitter and Retry-After support
"""

import os
import re
import asyncio
import random
from typing import Dict, Any, Optional, Tuple, Callable, Awaitable
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.youtube.constants import (
    YOUTUBE_VIDEOS_UPLOAD_URL,
    YOUTUBE_THUMBNAILS_SET_URL,
)
from app.services.youtube.mock_client import mock_youtube_client


class YouTubeResumableUploader:
    """Manages chunked byte streaming and interruption recovery for YouTube uploads."""

    DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB (must be multiple of 256 KiB)
    MAX_RETRIES = 5
    BASE_BACKOFF_SECONDS = 2.0

    @classmethod
    async def initiate_upload_session(
        cls,
        access_token: str,
        file_path: str,
        snippet: Dict[str, Any],
        status_dict: Dict[str, Any],
    ) -> Tuple[str, int]:
        """Initiate a resumable upload session with YouTube Data API v3.

        Returns:
            Tuple of (session_uri, file_size_bytes)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError(f"Video file is 0 bytes: {file_path}")

        payload = {
            "snippet": snippet,
            "status": status_dict,
        }

        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
            session_uri = await mock_youtube_client.initiate_resumable_upload(
                payload, "video/mp4", file_size
            )
            return session_uri, file_size

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(YOUTUBE_VIDEOS_UPLOAD_URL, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                logger.error(f"[YouTubeUploader] Initiation failed: HTTP {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Failed to initiate resumable upload: {resp.text}")

            session_uri = resp.headers.get("Location")
            if not session_uri:
                raise RuntimeError("YouTube upload initiation did not return a Location header")

            logger.info(f"[YouTubeUploader] Initiated resumable session for {file_size} bytes")
            return session_uri, file_size

    @classmethod
    async def query_upload_status(
        cls,
        session_uri: str,
        total_bytes: int,
        access_token: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Query Google upload status to find how many bytes have been saved.

        Returns:
            Tuple of (status_code, last_confirmed_byte_offset)
            If status_code is 308: next byte to transmit is offset + 1.
            If offset is -1: no bytes saved yet.
        """
        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
            return await mock_youtube_client.query_upload_status(session_uri, total_bytes)

        headers = {
            "Content-Range": f"bytes */{total_bytes}",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(session_uri, headers=headers)
            if resp.status_code in (200, 201):
                # Upload already finished
                return resp.status_code, total_bytes - 1

            if resp.status_code == 308:
                range_header = resp.headers.get("Range")
                if range_header:
                    match = re.search(r"bytes=0-(\d+)", range_header)
                    if match:
                        last_byte = int(match.group(1))
                        return 308, last_byte
                return 308, -1  # 0 bytes received

            logger.warning(f"[YouTubeUploader] Status query returned HTTP {resp.status_code}: {resp.text}")
            return resp.status_code, -1

    @classmethod
    async def upload_file(
        cls,
        session_uri: str,
        file_path: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        initial_offset: int = 0,
        access_token: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Stream chunks to YouTube with automatic status query on failure and resumption.

        Returns:
            Created video dictionary response containing 'id' and 'snippet'.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        total_bytes = os.path.getsize(file_path)
        current_offset = initial_offset

        # If resuming, verify with server first
        if current_offset > 0:
            status_code, confirmed_last_byte = await cls.query_upload_status(
                session_uri, total_bytes, access_token
            )
            if status_code in (200, 201):
                logger.info(f"[YouTubeUploader] File already completely uploaded according to server status query.")
                return {"id": "already_uploaded", "status": {"uploadStatus": "uploaded"}}
            current_offset = confirmed_last_byte + 1
            logger.info(f"[YouTubeUploader] Resuming upload from verified byte offset {current_offset}/{total_bytes}")

        retries = 0

        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(file_path, "rb") as f:
                while current_offset < total_bytes:
                    bytes_to_read = min(chunk_size, total_bytes - current_offset)
                    f.seek(current_offset)
                    chunk_data = f.read(bytes_to_read)

                    start_byte = current_offset
                    end_byte = current_offset + len(chunk_data) - 1
                    content_range = f"bytes {start_byte}-{end_byte}/{total_bytes}"

                    try:
                        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
                            status_code, res_data = await mock_youtube_client.upload_chunk(
                                session_uri, chunk_data, start_byte, end_byte, total_bytes
                            )
                        else:
                            headers = {
                                "Content-Length": str(len(chunk_data)),
                                "Content-Range": content_range,
                                "Content-Type": "video/mp4",
                            }
                            if access_token:
                                headers["Authorization"] = f"Bearer {access_token}"

                            resp = await client.put(session_uri, headers=headers, content=chunk_data)
                            status_code = resp.status_code
                            res_data = resp.json() if resp.text else {}

                            # Check Range header on 308
                            if status_code == 308:
                                range_hdr = resp.headers.get("Range")
                                if range_hdr:
                                    match = re.search(r"bytes=0-(\d+)", range_hdr)
                                    if match:
                                        res_data = {"Range": range_hdr}

                        if status_code in (200, 201):
                            # Final chunk completed
                            current_offset = total_bytes
                            if progress_callback:
                                await progress_callback(current_offset, total_bytes)
                            logger.info(f"[YouTubeUploader] Final chunk accepted (HTTP {status_code}).")
                            return res_data or {"id": "uploaded_video"}

                        elif status_code == 308:
                            # Chunk accepted, parse offset if provided
                            range_str = (res_data or {}).get("Range", "")
                            if range_str:
                                m = re.search(r"bytes=0-(\d+)", range_str)
                                if m:
                                    current_offset = int(m.group(1)) + 1
                                else:
                                    current_offset = end_byte + 1
                            else:
                                current_offset = end_byte + 1

                            retries = 0  # reset retries on forward progress
                            if progress_callback:
                                await progress_callback(current_offset, total_bytes)

                        elif status_code in (500, 502, 503, 504, 429):
                            # Retryable server error
                            raise RuntimeError(f"Server returned retryable HTTP {status_code}")

                        else:
                            raise RuntimeError(f"Upload rejected with non-retryable HTTP {status_code}: {res_data}")

                    except Exception as exc:
                        retries += 1
                        logger.warning(
                            f"[YouTubeUploader] Chunk upload failed at offset {current_offset} "
                            f"(attempt {retries}/{cls.MAX_RETRIES}): {exc}"
                        )
                        if retries > cls.MAX_RETRIES:
                            raise RuntimeError(f"Resumable upload failed after {cls.MAX_RETRIES} attempts: {exc}") from exc

                        # Exponential backoff with jitter
                        backoff = (cls.BASE_BACKOFF_SECONDS ** retries) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(backoff)

                        # Query server to verify actual byte offset before re-sending
                        try:
                            query_code, server_last_byte = await cls.query_upload_status(
                                session_uri, total_bytes, access_token
                            )
                            if query_code in (200, 201):
                                return {"id": "already_uploaded", "status": {"uploadStatus": "uploaded"}}
                            if server_last_byte >= 0:
                                current_offset = server_last_byte + 1
                                logger.info(f"[YouTubeUploader] Recovered offset from status query: {current_offset}")
                        except Exception as status_err:
                            logger.warning(f"[YouTubeUploader] Status query during recovery attempt failed: {status_err}")

        raise RuntimeError("Resumable upload loop terminated without completion status.")

    @classmethod
    async def upload_thumbnail(
        cls,
        access_token: str,
        video_id: str,
        thumbnail_path: str,
    ) -> Dict[str, Any]:
        """Upload custom thumbnail for published video."""
        if not os.path.exists(thumbnail_path):
            raise FileNotFoundError(f"Thumbnail file not found at: {thumbnail_path}")

        with open(thumbnail_path, "rb") as f:
            image_data = f.read()

        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
            return await mock_youtube_client.set_thumbnail(video_id, image_data)

        url = f"{YOUTUBE_THUMBNAILS_SET_URL}?videoId={video_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "image/jpeg",
            "Content-Length": str(len(image_data)),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, content=image_data)
            if resp.status_code not in (200, 201):
                logger.error(f"[YouTubeUploader] Thumbnail upload failed: HTTP {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Thumbnail upload failed: {resp.text}")
            return resp.json()
