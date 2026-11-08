"""Unit tests for Subtitle and Caption Compiler (SRT and kinetic ASS)."""

import os
from pathlib import Path
import pytest
from app.services.video.subtitles import SubtitleCompiler


def test_hex_to_ass_color():
    """Verify conversion from CSS hex to ASS &HAABBGGRR format."""
    # Vivid Ember #FF7A00 -> R=FF, G=7A, B=00 -> ASS: &H00007AFF
    ass_ember = SubtitleCompiler.hex_to_ass_color("#FF7A00")
    assert ass_ember == "&H00007AFF"

    # White #FFFFFF -> &H00FFFFFF
    ass_white = SubtitleCompiler.hex_to_ass_color("#FFFFFF")
    assert ass_white == "&H00FFFFFF"

    # Short hex #F00 -> #FF0000 -> &H000000FF
    ass_red = SubtitleCompiler.hex_to_ass_color("#F00")
    assert ass_red == "&H000000FF"


def test_srt_compilation():
    """Verify SRT formatted output and timestamp precision."""
    cues = [
        {"start": 0.0, "end": 2.45, "text": "Welcome to Creator Studio AI."},
        {"start": 2.45, "end": 5.12, "text": "The autonomous video generation pipeline."},
    ]
    srt = SubtitleCompiler.compile_srt(cues)
    assert "1\n00:00:00,000 --> 00:00:02,450\nWelcome to Creator Studio AI." in srt
    assert "2\n00:00:02,450 --> 00:00:05,120\nThe autonomous video generation pipeline." in srt


def test_ass_compilation_vivid_ember():
    """Verify ASS compilation with kinetic karaoke tags and Vivid Ember styles."""
    cues = [
        {
            "start": 0.0,
            "end": 3.0,
            "text": "Build fast and ship.",
            "words": [
                {"word": "Build", "start": 0.0, "end": 0.8},
                {"word": "fast", "start": 0.8, "end": 1.6},
                {"word": "and", "start": 1.6, "end": 2.0},
                {"word": "ship.", "start": 2.0, "end": 3.0},
            ],
        }
    ]
    ass = SubtitleCompiler.compile_ass(cues, style_preset="vivid_ember", width=1920, height=1080)

    # Check script info and resolution
    assert "[Script Info]" in ass
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass

    # Check style definition contains Vivid Ember highlight &H00007AFF
    assert "&H00007AFF" in ass

    # Check kinetic karaoke tags
    assert r"{\k80}Build" in ass
    assert r"{\k80}fast" in ass
    assert r"{\k40}and" in ass
    assert r"{\k100}ship." in ass


def test_ass_synthesized_word_timings_when_missing():
    """Verify proportional word division when explicit word timestamps are absent."""
    cues = [
        {
            "start": 1.0,
            "end": 4.0,  # 3 seconds total for 3 words -> 100cs per word
            "text": "Automate video now",
        }
    ]
    ass = SubtitleCompiler.compile_ass(cues, style_preset="minimal_white")
    assert r"{\k100}Automate {\k100}video {\k100}now" in ass


def test_subtitle_file_persistence(tmp_path):
    """Verify saving subtitle files ensures directory creation."""
    target_path = tmp_path / "subs" / "test.ass"
    saved = SubtitleCompiler.save_subtitles("[Script Info]\nTitle: Test\n", str(target_path))
    assert os.path.exists(saved)
    with open(saved, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Title: Test" in content
