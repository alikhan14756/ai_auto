"""Multi-layer procedural graphic thumbnail composition engine using Pillow."""

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.core.config import settings
from app.core.logging import logger


class ThumbnailComposer:
    """Procedurally composes multi-layer 1280x720 graphical YouTube thumbnails."""

    WIDTH = 1280
    HEIGHT = 720
    SAFE_MARGIN = 40

    PRESETS = {
        "modern_tech_editorial": {
            "bg_color_start": (9, 10, 13),       # Obsidian #090A0D
            "bg_color_end": (26, 30, 39),        # Slate #1A1E27
            "headline_color": (255, 255, 255),    # White
            "accent_color": (255, 122, 0),       # Vivid Ember #FF7A00
            "badge_bg": (255, 122, 0, 230),
            "badge_text": (0, 0, 0),
            "font_family": "arial",
            "show_grid": True,
            "show_glow": True,
        },
        "minimalist_professional": {
            "bg_color_start": (5, 6, 8),
            "bg_color_end": (15, 17, 22),
            "headline_color": (255, 255, 255),
            "accent_color": (220, 225, 235),
            "badge_bg": (40, 45, 55, 220),
            "badge_text": (255, 255, 255),
            "font_family": "arial",
            "show_grid": False,
            "show_glow": False,
        },
        "high_contrast_educational": {
            "bg_color_start": (8, 12, 20),
            "bg_color_end": (16, 24, 40),
            "headline_color": (255, 230, 0),     # Bright Yellow #FFE600
            "accent_color": (255, 122, 0),
            "badge_bg": (255, 122, 0, 240),
            "badge_text": (0, 0, 0),
            "font_family": "arial",
            "show_grid": True,
            "show_glow": True,
        },
        "bold_creator": {
            "bg_color_start": (12, 10, 18),
            "bg_color_end": (30, 20, 45),
            "headline_color": (255, 255, 255),
            "accent_color": (255, 122, 0),
            "badge_bg": (255, 75, 40, 240),
            "badge_text": (255, 255, 255),
            "font_family": "arial",
            "show_grid": False,
            "show_glow": True,
        },
        "software_tutorial": {
            "bg_color_start": (10, 12, 16),
            "bg_color_end": (20, 25, 35),
            "headline_color": (240, 245, 255),
            "accent_color": (0, 240, 255),       # Neon Cyan #00F0FF
            "badge_bg": (0, 240, 255, 220),
            "badge_text": (0, 0, 0),
            "font_family": "arial",
            "show_grid": True,
            "show_glow": True,
        },
        "cinematic_tech": {
            "bg_color_start": (6, 7, 9),
            "bg_color_end": (18, 14, 12),
            "headline_color": (255, 255, 255),
            "accent_color": (255, 122, 0),
            "badge_bg": (255, 122, 0, 220),
            "badge_text": (0, 0, 0),
            "font_family": "arial",
            "show_grid": False,
            "show_glow": True,
        },
    }

    @classmethod
    def _get_font(cls, size: int) -> ImageFont.ImageFont:
        """Attempt to load standard fonts or fall back cleanly to default."""
        font_candidates = [
            "arial.ttf",
            "Arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\Arial.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @classmethod
    def _draw_linear_gradient(
        cls,
        image: Image.Image,
        color_start: Tuple[int, int, int],
        color_end: Tuple[int, int, int],
    ) -> None:
        """Draw horizontal linear gradient across canvas."""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for x in range(width):
            ratio = x / float(width)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))

    @classmethod
    def _draw_accent_glow(
        cls,
        image: Image.Image,
        center: Tuple[int, int],
        radius: int,
        color: Tuple[int, int, int],
    ) -> None:
        """Draw radial ambient glow in background."""
        glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)
        for r in range(radius, 0, -4):
            alpha = int(45 * (1.0 - (r / radius) ** 1.5))
            if alpha > 0:
                draw.ellipse(
                    [
                        center[0] - r,
                        center[1] - r,
                        center[0] + r,
                        center[1] + r,
                    ],
                    fill=(color[0], color[1], color[2], alpha),
                )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(15))
        image.alpha_composite(glow_layer)

    @classmethod
    def _draw_tech_grid(cls, image: Image.Image, step: int = 60) -> None:
        """Draw subtle tech grid overlay."""
        grid_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid_layer)
        w, h = image.size
        for x in range(0, w, step):
            draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 12), width=1)
        for y in range(0, h, step):
            draw.line([(0, y), (w, y)], fill=(255, 255, 255, 12), width=1)
        image.alpha_composite(grid_layer)

    @classmethod
    def _is_safe_image_path(cls, path_str: Optional[str]) -> bool:
        """Validate that image paths reside within allowed project storage boundaries."""
        if not path_str:
            return False
        try:
            p = Path(path_str).resolve()
            allowed = [
                Path(settings.LOCAL_STORAGE_DIR).resolve(),
                Path(settings.THUMBNAIL_OUTPUT_DIR).resolve(),
            ]
            return any(p.is_relative_to(a) for a in allowed) and p.exists()
        except Exception:
            return False

    @classmethod
    def render_composition(
        cls,
        output_path: str,
        headline_text: str,
        subtitle_text: Optional[str] = None,
        style_preset: str = "modern_tech_editorial",
        background_image_path: Optional[str] = None,
        subject_image_path: Optional[str] = None,
        accent_color_hex: Optional[str] = None,
        layers: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Procedurally render a composite 1280x720 thumbnail with typography, branding, and graphics."""
        preset = cls.PRESETS.get(style_preset, cls.PRESETS["modern_tech_editorial"])

        canvas = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (9, 10, 13, 255))

        # 1. Base Background
        if background_image_path and os.path.exists(background_image_path):
            try:
                bg = Image.open(background_image_path).convert("RGBA")
                bg = bg.resize((cls.WIDTH, cls.HEIGHT), Image.Resampling.LANCZOS)
                # Darken background image slightly to ensure typography contrast
                darkener = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (0, 0, 0, 130))
                bg.alpha_composite(darkener)
                canvas.paste(bg, (0, 0))
            except Exception as e:
                logger.warning(f"Failed to load background image {background_image_path}: {e}")
                cls._draw_linear_gradient(canvas, preset["bg_color_start"], preset["bg_color_end"])
        else:
            cls._draw_linear_gradient(canvas, preset["bg_color_start"], preset["bg_color_end"])

        # 2. Ambient Accent Glow
        accent_color = preset["accent_color"]
        if accent_color_hex and accent_color_hex.startswith("#") and len(accent_color_hex) == 7:
            try:
                accent_color = (
                    int(accent_color_hex[1:3], 16),
                    int(accent_color_hex[3:5], 16),
                    int(accent_color_hex[5:7], 16),
                )
            except Exception:
                pass

        if preset.get("show_glow"):
            cls._draw_accent_glow(canvas, center=(int(cls.WIDTH * 0.75), int(cls.HEIGHT * 0.45)), radius=280, color=accent_color)

        if preset.get("show_grid"):
            cls._draw_tech_grid(canvas, step=70)

        # 3. Subject Image (Placed on Right Side)
        if subject_image_path and cls._is_safe_image_path(subject_image_path):
            try:
                subj = Image.open(subject_image_path).convert("RGBA")
                # Scale subject to fit in right portion (approx 550x550)
                subj.thumbnail((540, 540), Image.Resampling.LANCZOS)
                subj_w, subj_h = subj.size
                pos_x = cls.WIDTH - subj_w - 70
                pos_y = (cls.HEIGHT - subj_h) // 2
                canvas.alpha_composite(subj, (pos_x, pos_y))
            except Exception as e:
                logger.warning(f"Failed to load subject image {subject_image_path}: {e}")

        # 4. Custom Layers If Provided
        if layers:
            for l in layers:
                if not l.get("visible", True):
                    continue
                l_type = l.get("type")
                if l_type == "image":
                    l_path = l.get("image_path")
                    if l_path and cls._is_safe_image_path(l_path):
                        try:
                            elem = Image.open(l_path).convert("RGBA")
                            w = int(l.get("width", elem.width))
                            h = int(l.get("height", elem.height))
                            elem = elem.resize((w, h), Image.Resampling.LANCZOS)
                            x = int(l.get("x", 0))
                            y = int(l.get("y", 0))
                            canvas.alpha_composite(elem, (x, y))
                        except Exception as e:
                            logger.debug(f"Failed to render custom layer {l}: {e}")

        # 5. Badge Hook (e.g. "NEW ARCHITECTURE" or "FULL GUIDE")
        draw = ImageDraw.Draw(canvas)
        text_start_y = 110
        if subtitle_text and subtitle_text.strip():
            badge_text = subtitle_text.strip().upper()
            b_font = cls._get_font(28)
            b_bbox = draw.textbbox((0, 0), badge_text, font=b_font)
            bw = b_bbox[2] - b_bbox[0] + 32
            bh = b_bbox[3] - b_bbox[1] + 16
            bx = cls.SAFE_MARGIN + 30
            by = text_start_y

            # Draw rounded badge background
            draw.rounded_rectangle(
                [bx, by, bx + bw, by + bh],
                radius=8,
                fill=preset["badge_bg"],
            )
            draw.text(
                (bx + 16, by + 8),
                badge_text,
                fill=preset["badge_text"],
                font=b_font,
            )
            text_start_y += bh + 25

        # 6. Headline Typography with High-Contrast Dropshadow and Multi-line Wrapping
        headline = headline_text.strip()
        font_size = 72
        max_text_width = int(cls.WIDTH * 0.58)

        # Dynamic Font Scaling
        while font_size >= 36:
            font = cls._get_font(font_size)
            words = headline.split()
            lines = []
            cur_line = []
            for w in words:
                test_line = " ".join(cur_line + [w])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > max_text_width and cur_line:
                    lines.append(" ".join(cur_line))
                    cur_line = [w]
                else:
                    cur_line.append(w)
            if cur_line:
                lines.append(" ".join(cur_line))

            total_h = sum((draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] + 16) for l in lines)
            if text_start_y + total_h <= cls.HEIGHT - cls.SAFE_MARGIN - 40:
                break
            font_size -= 4

        # Render headline lines
        cur_y = text_start_y
        for l_idx, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_h = line_bbox[3] - line_bbox[1]
            tx = cls.SAFE_MARGIN + 30

            # Dual-color accent: Last line or keyword in accent color
            text_color = preset["headline_color"]
            if l_idx == len(lines) - 1 and len(lines) > 1:
                text_color = accent_color

            # High-contrast drop shadow (3px offset)
            draw.text((tx + 3, cur_y + 3), line, fill=(0, 0, 0, 240), font=font)
            draw.text((tx + 2, cur_y + 2), line, fill=(0, 0, 0, 200), font=font)
            # Main headline text
            draw.text((tx, cur_y), line, fill=text_color, font=font)

            cur_y += line_h + 16

        # 7. Subtle Edge Vignette / Border Frame
        draw.rectangle(
            [0, 0, cls.WIDTH - 1, cls.HEIGHT - 1],
            outline=(255, 122, 0, 80),
            width=2,
        )

        # 8. Save Output File
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        final_rgb = canvas.convert("RGB")
        final_rgb.save(out_p, format="PNG", optimize=True)

        file_size = os.path.getsize(out_p)
        logger.info(f"Rendered thumbnail: {out_p} ({file_size} bytes, {cls.WIDTH}x{cls.HEIGHT})")

        return {
            "output_path": str(out_p),
            "width": cls.WIDTH,
            "height": cls.HEIGHT,
            "format": "PNG",
            "file_size_bytes": file_size,
            "style_preset": style_preset,
            "headline_text": headline,
            "subtitle_text": subtitle_text,
        }
