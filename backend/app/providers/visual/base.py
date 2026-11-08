"""Visual providers abstract interfaces and data transfer objects."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class VisualProviderError(Exception):
    """Base exception for visual provider operations."""
    pass


class BudgetExceededError(VisualProviderError):
    """Raised when paid visual operations exceed the user's hard monthly budget limit."""
    pass


class RateLimitError(VisualProviderError):
    """Raised when an external visual API rate limit is exceeded."""
    pass


class ProviderConfigurationError(VisualProviderError):
    """Raised when provider credentials or parameters are missing or invalid."""
    pass


class StockAssetResult(BaseModel):
    """Discovered external stock asset item."""

    external_id: str
    title: str
    description: Optional[str] = None
    preview_url: str
    download_url: str
    source_provider: str  # MOCK, PEXELS, PIXABAY, UNSPLASH
    source_url: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    license_type: str = "CC0"  # CC0, PEXELS_FREE, PIXABAY_FREE, UNSPLASH_FREE, CUSTOM
    license_status: str = "VERIFIED_COMMERCIAL"  # VERIFIED_COMMERCIAL, ATTRIBUTION_REQUIRED, LICENSE_REVIEW_REQUIRED, RESTRICTED
    attribution_text: Optional[str] = None
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    aspect_ratio: str = "16:9"  # 16:9, 9:16, 1:1
    media_type: str = "image"  # image, video
    duration_seconds: Optional[float] = None


class StockSearchResult(BaseModel):
    """Search query results from stock provider."""

    query: str
    total_results: int
    page: int = 1
    per_page: int = 10
    assets: List[StockAssetResult] = Field(default_factory=list)


class ImageGenerationResult(BaseModel):
    """Generated visual asset output."""

    image_bytes: bytes
    mime_type: str = "image/png"
    file_format: str = "png"
    width: int = 1920
    height: int = 1080
    aspect_ratio: str = "16:9"
    prompt: str
    model_name: str = "mock-canvas-v1"


class StockSearchProviderInterface(ABC):
    """Abstract interface for external media stock search engines."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether provider is configured and available for search."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        aspect_ratio: str = "16:9",
        page: int = 1,
        per_page: int = 10,
        media_type: str = "image",
    ) -> StockSearchResult:
        """Search external stock engine for assets."""
        pass


class ImageGenerationProviderInterface(ABC):
    """Abstract interface for AI image synthesis engines."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether provider is configured and ready."""
        pass

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "photorealistic",
        resolution: str = "1080p",
    ) -> ImageGenerationResult:
        """Synthesize an image based on prompt and aspect ratio."""
        pass
