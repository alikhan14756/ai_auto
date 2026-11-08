"""Google Gemini / Imagen image generation provider integration."""

import io
from typing import Optional
from app.core.config import settings
from app.providers.visual.base import (
    ImageGenerationProviderInterface,
    ImageGenerationResult,
    ProviderConfigurationError,
    BudgetExceededError,
    RateLimitError,
)


class GeminiImageProvider(ImageGenerationProviderInterface):
    """Google GenAI Imagen provider for high-fidelity scene asset generation."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)

    @property
    def provider_id(self) -> str:
        return "GEMINI_IMAGEN"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and len(self._api_key.strip()) > 10)

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "photorealistic",
        resolution: str = "1080p",
    ) -> ImageGenerationResult:
        if not self.is_available:
            raise ProviderConfigurationError("GEMINI_API_KEY is not configured for image generation.")

        # Hard budget guardrail check: if default cap is 0.00, reject billable image generation
        max_spend = float(getattr(settings, "MAX_MONTHLY_SPEND_USD", 0.00))
        if max_spend <= 0.00:
            raise BudgetExceededError(
                "Paid image generation is disabled under the $0.00 default financial budget guardrail. "
                "Use the offline Mock provider or raise MAX_MONTHLY_SPEND_USD."
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)

            # Map aspect ratio to Imagen format
            ratio_map = {
                "16:9": "16:9",
                "9:16": "9:16",
                "1:1": "1:1",
            }
            img_ratio = ratio_map.get(aspect_ratio, "16:9")

            result = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=f"{prompt}. High detail, professional digital production, {style}, sharp 4k, no text watermarks.",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=img_ratio,
                    output_mime_type="image/png",
                ),
            )

            generated_image = result.generated_images[0]
            image_bytes = generated_image.image.image_bytes

            width = 1920 if img_ratio == "16:9" else (1080 if img_ratio == "9:16" else 1080)
            height = 1080 if img_ratio == "16:9" else (1920 if img_ratio == "9:16" else 1080)

            return ImageGenerationResult(
                image_bytes=image_bytes,
                mime_type="image/png",
                file_format="png",
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                prompt=prompt,
                model_name="imagen-3.0-generate-002",
            )
        except (BudgetExceededError, ProviderConfigurationError):
            raise
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower():
                raise RateLimitError(f"Gemini Imagen API quota exceeded: {exc}") from exc
            raise ProviderConfigurationError(f"Gemini image generation failure: {exc}") from exc
