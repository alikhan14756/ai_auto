"""Tests for Visual Provider Abstraction, Mock Providers, and Factory."""

import io
import pytest
from PIL import Image
from app.providers.visual.base import (
    StockSearchProviderInterface,
    ImageGenerationProviderInterface,
    StockSearchResult,
    StockAssetResult,
    ImageGenerationResult,
    BudgetExceededError,
    ProviderConfigurationError,
)
from app.providers.visual.mock import MockStockProvider, MockImageProvider
from app.providers.visual.stock_pexels import PexelsProvider
from app.providers.visual.stock_pixabay import PixabayProvider
from app.providers.visual.gemini_image import GeminiImageProvider
from app.providers.visual.factory import VisualProviderFactory


@pytest.mark.asyncio
async def test_mock_stock_provider_search():
    """Verify MockStockProvider returns valid, structured CC0 stock assets with pagination."""
    provider = MockStockProvider()
    assert provider.provider_id == "MOCK"
    assert provider.is_available is True

    # Search for code
    res: StockSearchResult = await provider.search(query="code terminal", aspect_ratio="16:9", page=1, per_page=3)
    assert res.total_results > 0
    assert len(res.assets) <= 3
    first = res.assets[0]
    assert first.source_provider == "MOCK"
    assert first.license_status in ("VERIFIED_COMMERCIAL", "LICENSE_REVIEW_REQUIRED")
    assert first.aspect_ratio == "16:9"
    assert first.width == 1920
    assert first.height == 1080


@pytest.mark.asyncio
async def test_mock_stock_provider_portrait():
    """Verify MockStockProvider handles 9:16 portrait orientation for Shorts."""
    provider = MockStockProvider()
    res = await provider.search(query="mobile", aspect_ratio="9:16", page=1, per_page=2)
    assert len(res.assets) > 0
    assert res.assets[0].aspect_ratio == "9:16"
    assert res.assets[0].width == 1080
    assert res.assets[0].height == 1920


@pytest.mark.asyncio
async def test_mock_image_provider_synthesis():
    """Verify MockImageProvider synthesizes valid PNG image bytes with Pillow."""
    provider = MockImageProvider()
    assert provider.provider_id == "MOCK"
    assert provider.is_available is True

    # Landscape 16:9
    gen: ImageGenerationResult = await provider.generate_image(
        prompt="A futuristic AI code editor with syntax highlighting",
        aspect_ratio="16:9",
        style="photorealistic",
    )
    assert gen.file_format == "png"
    assert gen.aspect_ratio == "16:9"
    assert gen.width == 1280
    assert gen.height == 720
    assert len(gen.image_bytes) > 1000

    # Verify bytes represent a real, decodable PNG with Pillow
    img = Image.open(io.BytesIO(gen.image_bytes))
    assert img.format == "PNG"
    assert img.size == (1280, 720)


@pytest.mark.asyncio
async def test_mock_image_provider_vertical_shorts():
    """Verify MockImageProvider generates valid 9:16 portrait assets."""
    provider = MockImageProvider()
    gen = await provider.generate_image(
        prompt="Fast mobile coding demo",
        aspect_ratio="9:16",
    )
    assert gen.aspect_ratio == "9:16"
    assert gen.width == 720
    assert gen.height == 1280

    img = Image.open(io.BytesIO(gen.image_bytes))
    assert img.size == (720, 1280)


def test_external_providers_unconfigured():
    """Verify external stock providers report unavailable when API keys are absent."""
    pexels = PexelsProvider(api_key="")
    assert pexels.provider_id == "PEXELS"
    assert pexels.is_available is False

    pixabay = PixabayProvider(api_key="")
    assert pixabay.provider_id == "PIXABAY"
    assert pixabay.is_available is False


@pytest.mark.asyncio
async def test_gemini_image_budget_rejection():
    """Verify GeminiImageProvider enforces the $0.00 default financial budget guardrail."""
    gemini = GeminiImageProvider(api_key="mock-gemini-test-key-long-enough")
    assert gemini.provider_id == "GEMINI_IMAGEN"
    assert gemini.is_available is True

    # Under $0.00 max spend, generate_image should raise BudgetExceededError
    with pytest.raises(BudgetExceededError):
        await gemini.generate_image("A tech logo", aspect_ratio="16:9")


def test_visual_provider_factory():
    """Verify VisualProviderFactory dispatches default and requested provider instances."""
    stock = VisualProviderFactory.get_stock_provider()
    assert isinstance(stock, MockStockProvider)

    img = VisualProviderFactory.get_image_provider()
    assert isinstance(img, MockImageProvider)

    available_stock = VisualProviderFactory.list_available_stock_providers()
    assert "MOCK" in available_stock
    assert available_stock["MOCK"] is True

    available_img = VisualProviderFactory.list_available_image_providers()
    assert "MOCK" in available_img
    assert available_img["MOCK"] is True
