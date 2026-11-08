"""Mock YouTube API Client for offline, zero-dollar automated CI testing.

Simulates the complete Google OAuth 2.0 flow, YouTube Data API v3 channel introspection,
and Google Resumable Media Upload protocol without network calls or external credentials.
"""

import uuid
import time
from typing import Dict, Any, Optional, Tuple
from app.core.logging import logger


class MockUploadSessionState:
    """In-memory state for a simulated resumable upload session."""

    def __init__(self, session_id: str, total_bytes: int, metadata: Dict[str, Any]):
        self.session_id = session_id
        self.total_bytes = total_bytes
        self.metadata = metadata
        self.bytes_received = 0
        self.created_at = time.time()
        self.completed = False
        self.video_id: Optional[str] = None
        self.fail_next_chunk = False
        self.simulate_network_drop = False


class MockYouTubeClient:
    """Zero-dollar offline simulator for Google YouTube API."""

    def __init__(self):
        self._sessions: Dict[str, MockUploadSessionState] = {}
        self._revoked_tokens: set = set()
        self._thumbnails: Dict[str, bytes] = {}

    def reset(self) -> None:
        """Clear all active sessions and state."""
        self._sessions.clear()
        self._revoked_tokens.clear()
        self._thumbnails.clear()

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Simulate OAuth code exchange."""
        if not code or code == "invalid_code":
            raise ValueError("Invalid authorization code")
        return {
            "access_token": f"mock_ya29_{uuid.uuid4().hex[:20]}",
            "refresh_token": f"mock_1//_{uuid.uuid4().hex[:30]}",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Simulate refreshing an access token."""
        if refresh_token in self._revoked_tokens or refresh_token == "invalid_refresh_token":
            raise ValueError("Invalid or revoked refresh token")
        return {
            "access_token": f"mock_ya29_refreshed_{uuid.uuid4().hex[:20]}",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def revoke_token(self, token: str) -> bool:
        """Simulate token revocation."""
        self._revoked_tokens.add(token)
        return True

    async def fetch_channel_profile(self, access_token: str) -> Dict[str, Any]:
        """Simulate fetching authorized channel profile."""
        if not access_token or "invalid" in access_token:
            raise ValueError("Unauthorized or invalid access token")
        return {
            "youtube_channel_id": "UC_ali_build_test_channel_01",
            "title": "Muhammad Ali AI Studio",
            "description": "Autonomous AI content engineering and tech deep dives.",
            "custom_url": "@muhammadali_ai",
            "thumbnail_url": "https://images.example.com/channel_avatar.jpg",
            "subscriber_count": 48500,
        }

    async def initiate_resumable_upload(
        self,
        metadata: Dict[str, Any],
        content_type: str,
        content_length: int,
    ) -> str:
        """Simulate initiating a resumable upload session."""
        session_id = f"mock_sess_{uuid.uuid4().hex}"
        session_uri = f"https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&session_id={session_id}"
        self._sessions[session_uri] = MockUploadSessionState(
            session_id=session_id,
            total_bytes=content_length,
            metadata=metadata,
        )
        logger.info(f"[MockYouTube] Initiated resumable upload session {session_id} for {content_length} bytes")
        return session_uri

    async def upload_chunk(
        self,
        session_uri: str,
        chunk_bytes: bytes,
        start_byte: int,
        end_byte: int,
        total_bytes: int,
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """Simulate sending a media chunk via PUT.

        Returns:
            (status_code, response_body_or_headers)
            Status 308: Resume Incomplete, headers with Range
            Status 201: Created, video payload
        """
        session = self._sessions.get(session_uri)
        if not session:
            return 404, {"error": "Upload session not found"}

        if session.fail_next_chunk:
            session.fail_next_chunk = False
            return 500, {"error": "Simulated temporary backend error"}

        if session.simulate_network_drop:
            session.simulate_network_drop = False
            raise ConnectionResetError("Simulated network socket reset during chunk transmission")

        chunk_length = len(chunk_bytes)
        expected_chunk_length = (end_byte - start_byte) + 1
        if chunk_length != expected_chunk_length:
            return 400, {"error": f"Chunk length {chunk_length} does not match range {start_byte}-{end_byte}"}

        # Update bytes received
        session.bytes_received = end_byte + 1

        if session.bytes_received >= session.total_bytes:
            session.completed = True
            session.video_id = f"yt_{uuid.uuid4().hex[:11]}"
            logger.info(f"[MockYouTube] Upload completed! Created video ID: {session.video_id}")
            return 201, {
                "id": session.video_id,
                "status": {
                    "uploadStatus": "uploaded",
                    "privacyStatus": session.metadata.get("status", {}).get("privacyStatus", "unlisted"),
                    "publishAt": session.metadata.get("status", {}).get("publishAt"),
                },
                "snippet": session.metadata.get("snippet", {}),
            }
        else:
            last_received = session.bytes_received - 1
            return 308, {"Range": f"bytes=0-{last_received}"}

    async def query_upload_status(
        self,
        session_uri: str,
        total_bytes: int,
    ) -> Tuple[int, int]:
        """Simulate status query PUT with Content-Range: bytes */total.

        Returns:
            (status_code, last_received_byte_offset)
            If status 308: next byte to send is last_offset + 1.
        """
        session = self._sessions.get(session_uri)
        if not session:
            return 404, -1

        if session.completed:
            return 200, session.total_bytes - 1

        last_received = session.bytes_received - 1
        return 308, last_received

    async def set_thumbnail(self, video_id: str, image_bytes: bytes) -> Dict[str, Any]:
        """Simulate custom thumbnail upload."""
        if not video_id:
            raise ValueError("video_id required")
        self._thumbnails[video_id] = image_bytes
        logger.info(f"[MockYouTube] Attached {len(image_bytes)} byte thumbnail to video {video_id}")
        return {
            "kind": "youtube#thumbnailSetResponse",
            "items": [
                {
                    "default": {"url": f"https://i.ytimg.com/vi/{video_id}/default.jpg", "width": 120, "height": 90},
                    "medium": {"url": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg", "width": 320, "height": 180},
                    "high": {"url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", "width": 480, "height": 360},
                    "standard": {"url": f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg", "width": 640, "height": 480},
                    "maxres": {"url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", "width": 1280, "height": 720},
                }
            ],
        }

    async def query_reports(
        self,
        access_token: str,
        start_date: str,
        end_date: str,
        metrics: str,
        dimensions: Optional[str] = None,
        filters: Optional[str] = None,
        sort: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Simulate YouTube Analytics API reports.query."""
        if not access_token or "invalid" in access_token:
            raise ValueError("Unauthorized or invalid access token")

        # Channel daily trends
        if dimensions == "day":
            headers = [
                {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "estimatedMinutesWatched", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "averageViewDuration", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                {"name": "subscribersGained", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "subscribersLost", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "likes", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "comments", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "shares", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
            rows = [
                ["2026-11-01", 1250, 4800, 230, 52.4, 45, 3, 110, 18, 12],
                ["2026-11-02", 1420, 5450, 245, 55.1, 52, 4, 135, 24, 15],
                ["2026-11-03", 1680, 6200, 240, 54.0, 60, 5, 150, 31, 22],
                ["2026-11-04", 1510, 5800, 235, 53.5, 48, 2, 140, 20, 18],
                ["2026-11-05", 1950, 7500, 260, 58.2, 75, 6, 185, 42, 30],
                ["2026-11-06", 2100, 8100, 255, 57.0, 82, 7, 210, 48, 35],
                ["2026-11-07", 2350, 9200, 265, 59.5, 95, 8, 240, 55, 42],
            ]
            return {"kind": "youtubeAnalytics#resultTable", "columnHeaders": headers, "rows": rows}

        # Video breakdown
        elif dimensions == "video":
            headers = [
                {"name": "video", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "estimatedMinutesWatched", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "averageViewDuration", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                {"name": "subscribersGained", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "likes", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "comments", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "shares", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
            rows = [
                ["mock_vid_ai_agents_101", 5400, 22500, 250, 58.0, 180, 450, 62, 54],
                ["mock_vid_fastapi_production", 3800, 16200, 255, 56.5, 120, 320, 41, 38],
                ["mock_vid_shorts_cursor_trick", 9200, 6800, 44, 82.0, 240, 780, 85, 95],
                ["mock_vid_python_312_features", 2100, 8400, 240, 51.2, 65, 180, 25, 19],
            ]
            return {"kind": "youtubeAnalytics#resultTable", "columnHeaders": headers, "rows": rows}

        # Traffic source breakdown
        elif dimensions == "insightTrafficSourceType":
            headers = [
                {"name": "insightTrafficSourceType", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "estimatedMinutesWatched", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
            rows = [
                ["YT_SEARCH", 4800, 19200],
                ["SUGGESTED_VIDEO", 3200, 12800],
                ["BROWSE_FEATURES", 2400, 9600],
                ["EXTERNAL", 850, 3100],
                ["CHANNEL_PAGE", 620, 2100],
                ["NOTIFICATION", 430, 1500],
            ]
            return {"kind": "youtubeAnalytics#resultTable", "columnHeaders": headers, "rows": rows}

        # Audience country breakdown
        elif dimensions == "country":
            headers = [
                {"name": "country", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
            rows = [
                ["US", 4200],
                ["GB", 1800],
                ["CA", 1200],
                ["DE", 950],
                ["IN", 2400],
                ["PK", 1100],
            ]
            return {"kind": "youtubeAnalytics#resultTable", "columnHeaders": headers, "rows": rows}

        # Device type breakdown
        elif dimensions == "deviceType":
            headers = [
                {"name": "deviceType", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
            rows = [
                ["DESKTOP", 6500],
                ["MOBILE", 4800],
                ["TABLET", 600],
                ["TV", 400],
            ]
            return {"kind": "youtubeAnalytics#resultTable", "columnHeaders": headers, "rows": rows}

        # Default fallback
        return {
            "kind": "youtubeAnalytics#resultTable",
            "columnHeaders": [{"name": "views", "columnType": "METRIC", "dataType": "INTEGER"}],
            "rows": [[12300]],
        }

    async def query_video_retention(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Simulate YouTube audience retention curve (100 points, 30s benchmark)."""
        if not access_token or "invalid" in access_token:
            raise ValueError("Unauthorized or invalid access token")

        # Generate smooth realistic retention curve
        points = []
        is_short = "shorts" in video_id.lower()
        decay_factor = 0.25 if is_short else 0.45

        for i in range(1, 101):
            ratio = round(i / 100.0, 2)
            # Realistic drop-off formula: steep hook drop, then steady plateau
            if ratio <= 0.05:
                watch_pct = round(1.0 - (ratio * 2.5), 3)  # Drops to ~87% at 5%
            elif ratio <= 0.15:
                watch_pct = round(0.87 - ((ratio - 0.05) * 1.5), 3)  # ~72% at 30s hook
            else:
                watch_pct = round(max(0.20, 0.72 - ((ratio - 0.15) * decay_factor)), 3)
            points.append({"ratio": ratio, "watch_percentage": watch_pct})

        retention_at_30s = 0.82 if is_short else 0.71
        drop_offs = [
            {"ratio": 0.08, "timestamp_sec": 30, "drop_pct": 14.2, "note": "End of hook intro"},
            {"ratio": 0.45, "timestamp_sec": 180, "drop_pct": 6.8, "note": "Complex code diagram slide"},
        ]

        return {
            "youtube_video_id": video_id,
            "relative_retention_points": points,
            "drop_off_points": drop_offs,
            "average_view_duration_seconds": 44 if is_short else 252,
            "retention_at_30s": retention_at_30s,
            "sample_size": 3800,
        }

    async def fetch_video_details(self, access_token: str, video_ids: list) -> list:
        """Simulate YouTube Data API v3 videos.list(part=contentDetails,statistics,snippet)."""
        items = []
        for vid in video_ids:
            is_short = "shorts" in str(vid).lower()
            items.append({
                "id": str(vid),
                "snippet": {
                    "title": f"Production Deep Dive on {vid}",
                    "publishedAt": "2026-11-01T14:00:00Z",
                    "channelId": "UC_ali_build_test_channel_01",
                },
                "contentDetails": {
                    "duration": "PT45S" if is_short else "PT7M30S",
                    "definition": "hd",
                },
                "statistics": {
                    "viewCount": "9200" if is_short else "5400",
                    "likeCount": "780" if is_short else "450",
                    "commentCount": "85" if is_short else "62",
                },
            })
        return items


# Singleton mock instance for offline mode and tests
mock_youtube_client = MockYouTubeClient()
