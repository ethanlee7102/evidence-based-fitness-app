import tempfile
import os
from urllib.parse import urlparse
import httpx
import cv2

# Allowed domains for video URLs (e.g., your Supabase storage domain)
ALLOWED_DOMAINS = [
    "supabase.co",
    "supabase.com",
]

# Max file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Request timeout in seconds
REQUEST_TIMEOUT = 60


class VideoProcessor:
    """Handles video download and frame extraction."""

    def _validate_url(self, video_url: str) -> None:
        """Validate that the URL is safe to fetch."""
        try:
            parsed = urlparse(video_url)
        except Exception:
            raise ValueError("Invalid URL format")

        # Must be HTTPS
        if parsed.scheme != "https":
            raise ValueError("Only HTTPS URLs are allowed")

        # Check against allowed domains
        host = parsed.hostname or ""
        if not any(host.endswith(domain) for domain in ALLOWED_DOMAINS):
            raise ValueError(f"Domain not allowed: {host}")

        # Block private/internal IPs
        if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
            raise ValueError("Internal URLs not allowed")

    async def download_video(self, video_url: str) -> tuple[str, float]:
        """
        Download video from URL to a temporary file.
        Returns tuple of (path to temporary file, fps).
        """
        self._validate_url(video_url)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_path = tmp_file.name

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(video_url, follow_redirects=True)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith(("video/", "application/octet-stream")):
                    raise ValueError(f"Invalid content type: {content_type}")

                # Validate content length
                content_length = int(response.headers.get("content-length", 0))
                if content_length > MAX_FILE_SIZE:
                    raise ValueError(f"File too large: {content_length} bytes")

                # Check actual content size
                content = response.content
                if len(content) > MAX_FILE_SIZE:
                    raise ValueError(f"File too large: {len(content)} bytes")

                tmp_file.write(content)

        # Get video FPS
        fps = self._get_video_fps(tmp_path)

        return tmp_path, fps

    def _get_video_fps(self, video_path: str) -> float:
        """Extract FPS from video file."""
        cap = cv2.VideoCapture(video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            return fps if fps > 0 else 30.0
        finally:
            cap.release()

    def cleanup(self, video_path: str) -> None:
        """Remove temporary video file."""
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
        except OSError:
            pass  # Ignore cleanup errors
