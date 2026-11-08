"""Pixabay official stock media search provider."""

import httpx
from typing import List, Optional
from app.core.config import settings
from app.providers.visual.base import (
    StockSearchProviderInterface,
    StockSearchResult,
    StockAssetResult,
    ProviderConfigurationError,
    RateLimitError,
)


class PixabayProvider(StockSearchProviderInterface):
    """Pixabay API integration for commercial royalty-free media."""

    API_BASE = "https://pixabay.com/api"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "PIXABAY_API_KEY", None)

    @property
    def provider_id(self) -> str:
        return "PIXABAY"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and len(self._api_key.strip()) > 5)

    async def search(
        self,
        query: str,
        aspect_ratio: str = "16:9",
        page: int = 1,
        per_page: int = 10,
        media_type: str = "image",
    ) -> StockSearchResult:
        if not self.is_available:
            raise ProviderConfigurationError("PIXABAY_API_KEY is not configured or invalid.")

        orientation = "horizontal" if aspect_ratio == "16:9" else "vertical"
        params = {
            "key": self._api_key,
            "q": query,
            "image_type": "photo",
            "orientation": orientation,
            "page": page,
            "per_page": min(per_page, 50),
            "safesearch": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self.API_BASE, params=params)
                if resp.status_code == 429:
                    raise RateLimitError("Pixabay API request limit exceeded.")
                resp.raise_for_status()
                data = resp.json()

            hits = data.get("hits", [])
            total = data.get("totalHits", 0)

            results: List[StockAssetResult] = []
            for h in hits:
                results.append(
                    StockAssetResult(
                        external_id=f"pixabay-{h.get('id')}",
                        title=h.get("tags") or f"Pixabay visual for {query}",
                        description=f"Contributor {h.get('user')} on Pixabay.",
                        preview_url=h.get("webformatURL") or h.get("previewURL") or "",
                        download_url=h.get("largeImageURL") or h.get("webformatURL") or "",
                        source_provider="PIXABAY",
                        source_url=h.get("pageURL") or "https://pixabay.com",
                        author_name=h.get("user"),
                        author_url=f"https://pixabay.com/users/{h.get('user')}-{h.get('user_id')}/" if h.get("user_id") else None,
                        license_type="PIXABAY_FREE",
                        license_status="VERIFIED_COMMERCIAL",
                        attribution_text=None,  # Pixabay does not require attribution
                        width=h.get("imageWidth"),
                        height=h.get("imageHeight"),
                        aspect_ratio=aspect_ratio,
                        media_type="image",
                    )
                )

            return StockSearchResult(
                query=query,
                total_results=total,
                page=page,
                per_page=per_page,
                assets=results,
            )
        except (RateLimitError, ProviderConfigurationError):
            raise
        except Exception as exc:
            raise ProviderConfigurationError(f"Pixabay API communication error: {exc}") from exc
