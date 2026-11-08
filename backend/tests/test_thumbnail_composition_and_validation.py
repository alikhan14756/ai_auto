"""Unit and component tests for Thumbnail Composition, Concept Generation, and Quality Validation."""

import os
from pathlib import Path
from PIL import Image
import pytest

from app.services.thumbnail.composition import ThumbnailComposer
from app.services.thumbnail.concepts import ThumbnailConceptGenerator
from app.services.thumbnail.validator import ThumbnailValidator


def test_thumbnail_composer_render_basic(tmp_path):
    """Test procedural composition renders 1280x720 PNG with required metadata."""
    out_path = str(tmp_path / "test_thumb.png")
    result = ThumbnailComposer.render_composition(
        output_path=out_path,
        headline_text="STOP USING REDIS",
        subtitle_text="ZERO BUDGET",
        style_preset="modern_tech_editorial",
        accent_color_hex="#FF7A00",
    )

    assert os.path.exists(out_path)
    assert result["width"] == 1280
    assert result["height"] == 720
    assert result["format"] == "PNG"
    assert result["file_size_bytes"] > 0
    assert result["file_size_bytes"] < 2 * 1024 * 1024  # Under 2MB

    # Verify Pillow can open the generated image
    with Image.open(out_path) as img:
        assert img.size == (1280, 720)
        assert img.format == "PNG"


def test_thumbnail_composer_all_presets(tmp_path):
    """Verify all 6 supported style presets render without exceptions."""
    presets = [
        "modern_tech_editorial",
        "minimalist_professional",
        "high_contrast_educational",
        "bold_creator",
        "software_tutorial",
        "cinematic_tech",
    ]
    for idx, preset in enumerate(presets):
        out_path = str(tmp_path / f"thumb_preset_{idx}.png")
        result = ThumbnailComposer.render_composition(
            output_path=out_path,
            headline_text=f"PRESET {idx}",
            subtitle_text="TEST PRESET",
            style_preset=preset,
            accent_color_hex="#06B6D4",
        )
        assert os.path.exists(out_path)
        assert result["width"] == 1280
        assert result["height"] == 720


def test_thumbnail_composer_long_headline_multiline(tmp_path):
    """Verify long headlines automatically wrap across multiple lines without crashing."""
    out_path = str(tmp_path / "multiline_thumb.png")
    result = ThumbnailComposer.render_composition(
        output_path=out_path,
        headline_text="HOW WE SCALED OUR BACKGROUND QUEUE WORKER SYSTEM TO MILLIONS",
        subtitle_text="CASE STUDY",
        style_preset="bold_creator",
        accent_color_hex="#10B981",
    )
    assert os.path.exists(out_path)
    assert result["file_size_bytes"] > 0


def test_thumbnail_validator_valid_image(tmp_path):
    """Test validator on a compliant 1280x720 PNG."""
    out_path = str(tmp_path / "valid.png")
    ThumbnailComposer.render_composition(
        output_path=out_path,
        headline_text="PERFECT THUMBNAIL",
        subtitle_text="VERIFIED",
    )

    report = ThumbnailValidator.validate_thumbnail(out_path)
    assert report["valid"] is True
    assert report["status"] == "PASSED"
    assert report["metrics"]["width"] == 1280
    assert report["metrics"]["height"] == 720
    assert report["metrics"]["file_size_bytes"] < 2 * 1024 * 1024
    assert len(report["issues"]) == 0


def test_thumbnail_validator_nonexistent_file():
    """Test validator on missing path."""
    report = ThumbnailValidator.validate_thumbnail("nonexistent_image_path.png")
    assert report["valid"] is False
    assert report["status"] == "FAILED"
    assert "does not exist" in report["issues"][0].lower()


def test_thumbnail_validator_bad_dimensions(tmp_path):
    """Test validator rejects non-1280x720 images."""
    bad_img = Image.new("RGB", (800, 600), color=(50, 50, 50))
    bad_path = str(tmp_path / "bad_dims.png")
    bad_img.save(bad_path, format="PNG")

    report = ThumbnailValidator.validate_thumbnail(bad_path)
    assert report["valid"] is False
    assert report["status"] == "FAILED"
    assert any("1280x720" in err for err in report["issues"])


def test_thumbnail_concept_generator():
    """Verify concept generator returns 3 distinct variants with required fields."""
    concepts = ThumbnailConceptGenerator.generate_concepts(
        project_title="Building High Throughput Queues in Python",
        script_summary="Learn how to use PostgreSQL SKIP LOCKED for async worker tasks.",
    )

    assert len(concepts) == 3
    variants = [c["variant_code"] for c in concepts]
    assert variants == ["A", "B", "C"]

    for c in concepts:
        assert "headline_text" in c
        assert "style_preset" in c
        assert "accent_color_hex" in c
        assert "visual_hook" in c
        assert "target_emotion" in c
        assert "composition_layers" in c
        assert len(c["headline_text"].split()) <= 6  # Glancability check
