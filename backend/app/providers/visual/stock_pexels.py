"""Pexels official stock media search provider."""

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


class PexelsProvider(StockSearchProviderInterface):
    """Pexels API integration for royalty-free stock imagery."""

    API_BASE = "https://api.pexels.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "PEXELS_API_KEY", None)

    @property
    def provider_id(self) -> str:
        return "PEXELS"

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
            raise ProviderConfigurationError("PEXELS_API_KEY is not configured or invalid.")

        orientation = "landscape" if aspect_ratio == "16:9" else "portrait"
        headers = {"Authorization": self._api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "page": page,
            "per_page": min(per_page, 80),
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.API_BASE}/search", headers=headers, params=params)
                if resp.status_code == 429:
                    raise RateLimitError("Pexels API hourly request rate limit exceeded.")
                resp.raise_for_status()
                data = resp.json()

            photos = data.get("photos", [])
            total = data.get("total_results", 0)

            results: List[StockAssetResult] = []
            for p in photos:
                src = p.get("src", {})
                results.append(
                    StockAssetResult(
                        external_id=f"pexels-{p.get('id')}",
                        title=p.get("alt") or f"Pexels stock visual for {query}",
                        description=f"Photographed by {p.get('photographer')} on Pexels.",
                        preview_url=src.get("medium") or src.get("large") or "",
                        download_url=src.get("large2x") or src.get("original") or src.get("large") or "",
                        source_provider="PEXELS",
                        source_url=p.get("url") or "https://www.pexels.com",
                        author_name=p.get("photographer"),
                        author_url=p.get("photographer_url"),
                        license_type="PEXELS_FREE",
                        license_status="VERIFIED_COMMERCIAL",
                        attribution_text=f"Photo by {p.get('photographer')} on Pexels",
                        width=p.get("width"),
                        height=p.get("height"),
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
            raise ProviderConfigurationError(f"Pexels API communication error: {exc}") from exc
