"""Visual provider factory managing stock search and image generation provider instances."""

from typing import Dict, Optional, Type
from app.providers.visual.base import (
    StockSearchProviderInterface,
    ImageGenerationProviderInterface,
    ProviderConfigurationError,
)
from app.providers.visual.mock import MockStockProvider, MockImageProvider
from app.providers.visual.stock_pexels import PexelsProvider
from app.providers.visual.stock_pixabay import PixabayProvider
from app.providers.visual.gemini_image import GeminiImageProvider


class VisualProviderFactory:
    """Factory for discovering, instantiating, and caching visual providers."""

    _stock_providers: Dict[str, Type[StockSearchProviderInterface]] = {
        "MOCK": MockStockProvider,
        "PEXELS": PexelsProvider,
        "PIXABAY": PixabayProvider,
    }

    _image_providers: Dict[str, Type[ImageGenerationProviderInterface]] = {
        "MOCK": MockImageProvider,
        "GEMINI_IMAGEN": GeminiImageProvider,
    }

    _default_stock_provider: str = "MOCK"
    _default_image_provider: str = "MOCK"

    @classmethod
    def get_stock_provider(cls, name: Optional[str] = None) -> StockSearchProviderInterface:
        provider_key = (name or cls._default_stock_provider).upper().strip()
        provider_cls = cls._stock_providers.get(provider_key)
        if not provider_cls:
            # Fallback to MOCK
            return MockStockProvider()
        return provider_cls()

    @classmethod
    def get_image_provider(cls, name: Optional[str] = None) -> ImageGenerationProviderInterface:
        provider_key = (name or cls._default_image_provider).upper().strip()
        provider_cls = cls._image_providers.get(provider_key)
        if not provider_cls:
            # Fallback to MOCK
            return MockImageProvider()
        return provider_cls()

    @classmethod
    def set_default_stock_provider(cls, name: str) -> None:
        cls._default_stock_provider = name.upper()

    @classmethod
    def set_default_image_provider(cls, name: str) -> None:
        cls._default_image_provider = name.upper()

    @classmethod
    def list_available_stock_providers(cls) -> Dict[str, bool]:
        res = {}
        for k, p_cls in cls._stock_providers.items():
            try:
                instance = p_cls()
                res[k] = instance.is_available
            except Exception:
                res[k] = False
        return res

    @classmethod
    def list_available_image_providers(cls) -> Dict[str, bool]:
        res = {}
        for k, p_cls in cls._image_providers.items():
            try:
                instance = p_cls()
                res[k] = instance.is_available
            except Exception:
                res[k] = False
        return res
