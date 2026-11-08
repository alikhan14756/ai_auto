"""Deterministic offline visual mock providers for testing and zero-cost operation."""

import io
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

from app.providers.visual.base import (
    StockSearchProviderInterface,
    ImageGenerationProviderInterface,
    StockSearchResult,
    StockAssetResult,
    ImageGenerationResult,
)


class MockStockProvider(StockSearchProviderInterface):
    """Deterministic offline media discovery provider returning verified CC0 tech assets."""

    @property
    def provider_id(self) -> str:
        return "MOCK"

    @property
    def is_available(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        aspect_ratio: str = "16:9",
        page: int = 1,
        per_page: int = 10,
        media_type: str = "image",
    ) -> StockSearchResult:
        clean_q = (query or "tech").lower().strip()
        dims = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

        catalog = [
            ("Modern Developer Workspace with Multiple 4K Displays", "tech-workspace", "CC0", "VERIFIED_COMMERCIAL"),
            ("Terminal Code Editor showing Python AsyncIO and FastAPI Service", "code-terminal", "CC0", "VERIFIED_COMMERCIAL"),
            ("Futuristic Artificial Intelligence Neural Network Node Graph", "ai-network", "CC0", "VERIFIED_COMMERCIAL"),
            ("Cloud Infrastructure Cluster Architecture Diagram", "cloud-infra", "CC0", "VERIFIED_COMMERCIAL"),
            ("High-Performance Server Rack LED Data Center", "data-center", "CC0", "VERIFIED_COMMERCIAL"),
            ("Mobile Device Screen Demonstration with Dark Mode UI", "mobile-ui", "CC0", "VERIFIED_COMMERCIAL"),
            ("Software Architecture Flowchart and Microservice Topology", "software-diagram", "CC0", "VERIFIED_COMMERCIAL"),
            ("Digital Security Shield with Cryptographic Hexadecimal Code", "security-crypto", "CC0", "VERIFIED_COMMERCIAL"),
            ("Abstract Data Analytics Dashboard with Retention Charts", "analytics-dashboard", "CC0", "VERIFIED_COMMERCIAL"),
            ("Creative Digital Content Creator Recording Desk Setup", "creator-studio", "CC0", "VERIFIED_COMMERCIAL"),
            ("Unverified Third-Party Prototype Architecture Wireframe", "unverified-wireframe", "CUSTOM", "LICENSE_REVIEW_REQUIRED"),
        ]

        # Filter by query terms or fallback to general tech catalog
        matched = [item for item in catalog if any(w in item[0].lower() or w in item[1] for w in clean_q.split())]
        if not matched:
            matched = catalog[:per_page]

        # Pagination slice
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paged_items = matched[start_idx:end_idx]

        results: List[StockAssetResult] = []
        for idx, (title, slug, lic_type, lic_status) in enumerate(paged_items, start=start_idx + 1):
            results.append(
                StockAssetResult(
                    external_id=f"mock-stock-{slug}-{idx}",
                    title=title,
                    description=f"High-resolution CC0 verified asset representing {clean_q} for tech tutorial productions.",
                    preview_url=f"https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop&q=80",
                    download_url=f"https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1920&auto=format&fit=crop&q=80",
                    source_provider="MOCK",
                    source_url="https://unsplash.com/license",
                    author_name="Creator Studio Mock Archives",
                    author_url="https://alibuild.site",
                    license_type=lic_type,
                    license_status=lic_status,
                    attribution_text="Photo from Creator Studio AI Verified Public Archives" if lic_status == "ATTRIBUTION_REQUIRED" else None,
                    width=dims[0],
                    height=dims[1],
                    aspect_ratio=aspect_ratio,
                    media_type=media_type,
                )
            )

        return StockSearchResult(
            query=query,
            total_results=len(matched),
            page=page,
            per_page=per_page,
            assets=results,
        )


class MockImageProvider(ImageGenerationProviderInterface):
    """Deterministic offline image synthesis provider rendering high-contrast PNG assets with Pillow."""

    @property
    def provider_id(self) -> str:
        return "MOCK"

    @property
    def is_available(self) -> bool:
        return True

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "photorealistic",
        resolution: str = "1080p",
    ) -> ImageGenerationResult:
        # Dimensions based on aspect ratio
        if aspect_ratio == "9:16":
            width, height = 720, 1280
        elif aspect_ratio == "1:1":
            width, height = 1080, 1080
        else:  # default 16:9
            width, height = 1280, 720

        # Create canvas in Obsidian palette (#090A0D)
        img = Image.new("RGB", (width, height), color=(9, 10, 13))
        draw = ImageDraw.Draw(img)

        # Draw tech grid lines
        grid_step = 60
        for x in range(0, width, grid_step):
            draw.line([(x, 0), (x, height)], fill=(18, 20, 26), width=1)
        for y in range(0, height, grid_step):
            draw.line([(0, y), (width, y)], fill=(18, 20, 26), width=1)

        # Outer accent border in Vivid Ember (#FF7A00)
        border_inset = 24
        draw.rectangle(
            [(border_inset, border_inset), (width - border_inset, height - border_inset)],
            outline=(255, 122, 0),
            width=3,
        )

        # Inner corner brackets
        corner_len = 30
        corners = [
            (border_inset, border_inset),
            (width - border_inset, border_inset),
            (border_inset, height - border_inset),
            (width - border_inset, height - border_inset),
        ]
        for cx, cy in corners:
            draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=(255, 122, 0))

        # Center card
        center_w, center_h = int(width * 0.75), int(height * 0.45)
        c_x1 = (width - center_w) // 2
        c_y1 = (height - center_h) // 2
        c_x2 = c_x1 + center_w
        c_y2 = c_y1 + center_h
        draw.rectangle([(c_x1, c_y1), (c_x2, c_y2)], fill=(14, 16, 21), outline=(32, 35, 45), width=2)

        # Header tag pill
        draw.rectangle([(c_x1 + 20, c_y1 + 20), (c_x1 + 180, c_y1 + 50)], fill=(255, 122, 0, 40), outline=(255, 122, 0), width=1)
        draw.text((c_x1 + 30, c_y1 + 26), f"AI VISUAL // {aspect_ratio}", fill=(255, 122, 0))

        # Style & model metadata
        draw.text((c_x1 + 200, c_y1 + 26), f"Style: {style}  |  Res: {width}x{height}", fill=(160, 165, 180))

        # Main prompt text (wrapped lines)
        words = prompt.split()
        lines = []
        cur_line = []
        for word in words:
            cur_line.append(word)
            if len(" ".join(cur_line)) > 42:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))

        # Render first 4 lines
        y_text = c_y1 + 75
        for line in lines[:4]:
            draw.text((c_x1 + 25, y_text), line, fill=(230, 235, 245))
            y_text += 26

        # Footer badge
        draw.text((c_x1 + 25, c_y2 - 35), "Creator Studio AI - Verified Storyboard Asset", fill=(100, 105, 120))

        # Output bytes to PNG
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        image_bytes = buf.getvalue()

        return ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            file_format="png",
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            prompt=prompt,
            model_name="mock-canvas-v1",
        )
