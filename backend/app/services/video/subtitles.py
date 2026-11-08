"""Subtitle and Caption Compiler supporting SRT and kinetic SubStation Alpha (.ass)."""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger


class SubtitleCompiler:
    """Compiles audio narration timestamps and scene transcripts into SRT and kinetic ASS subtitles."""

    PRESETS = {
        "vivid_ember": {
            "font_name": "Arial",
            "font_size": 48,
            "primary_color": "&H00FFFFFF",  # Pure white primary
            "highlight_color": "&H00007AFF",  # Vivid Ember (#FF7A00 in ASS &HAABBGGRR)
            "outline_color": "&H000D0A09",  # Deep obsidian border (#090A0D)
            "back_color": "&H80000000",
            "bold": 1,
            "outline": 3.0,
            "shadow": 1.0,
            "alignment": 2,  # Bottom center
            "margin_v": 60,
        },
        "minimal_white": {
            "font_name": "Arial",
            "font_size": 42,
            "primary_color": "&H00FFFFFF",
            "highlight_color": "&H00D0D0D0",
            "outline_color": "&H00000000",
            "back_color": "&H80000000",
            "bold": 0,
            "outline": 2.0,
            "shadow": 0.0,
            "alignment": 2,
            "margin_v": 50,
        },
        "bold_yellow": {
            "font_name": "Impact",
            "font_size": 52,
            "primary_color": "&H0000E6FF",  # Yellow (#FFE600)
            "highlight_color": "&H00FFFFFF",
            "outline_color": "&H00000000",
            "back_color": "&H90000000",
            "bold": 1,
            "outline": 3.5,
            "shadow": 2.0,
            "alignment": 2,
            "margin_v": 65,
        },
        "neon_cyan": {
            "font_name": "Arial",
            "font_size": 48,
            "primary_color": "&H00FFF000",  # Neon Cyan (#00F0FF)
            "highlight_color": "&H00007AFF",
            "outline_color": "&H000D0A09",
            "back_color": "&H80000000",
            "bold": 1,
            "outline": 3.0,
            "shadow": 1.5,
            "alignment": 2,
            "margin_v": 60,
        },
    }

    @staticmethod
    def hex_to_ass_color(hex_code: str, alpha: int = 0) -> str:
        """Convert standard #RRGGBB or RRGGBB to ASS &HAABBGGRR format."""
        clean = hex_code.strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join([c * 2 for c in clean])
        if len(clean) != 6:
            return "&H00FFFFFF"
        r = clean[0:2]
        g = clean[2:4]
        b = clean[4:6]
        a = f"{alpha:02X}"
        return f"&H{a}{b}{g}{r}".upper()

    @staticmethod
    def format_timestamp_srt(seconds: float) -> str:
        """Format seconds as HH:MM:SS,mmm for SRT."""
        total_ms = int(round(seconds * 1000))
        hours = total_ms // 3600000
        remainder = total_ms % 3600000
        minutes = remainder // 60000
        remainder %= 60000
        secs = remainder // 1000
        ms = remainder % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    @staticmethod
    def format_timestamp_ass(seconds: float) -> str:
        """Format seconds as H:MM:SS.cc for ASS."""
        total_cs = int(round(seconds * 100))  # centiseconds
        hours = total_cs // 360000
        remainder = total_cs % 360000
        minutes = remainder // 6000
        remainder %= 6000
        secs = remainder // 100
        cs = remainder % 100
        return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"

    @classmethod
    def compile_srt(cls, cues: List[Dict[str, Any]]) -> str:
        """Compile a list of subtitle cues into an SRT string.
        Each cue: {"start": float, "end": float, "text": str}
        """
        lines = []
        for idx, cue in enumerate(cues, start=1):
            start_str = cls.format_timestamp_srt(float(cue["start"]))
            end_str = cls.format_timestamp_srt(float(cue["end"]))
            text = str(cue.get("text", "")).strip()
            lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
        return "\n".join(lines)

    @classmethod
    def compile_ass(
        cls,
        cues: List[Dict[str, Any]],
        style_preset: str = "vivid_ember",
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Compile cues into SubStation Alpha (.ass) format with kinetic styling.
        Each cue may have 'words': [{'word': str, 'start': float, 'end': float}]
        or simple 'start', 'end', and 'text'.
        """
        preset = cls.PRESETS.get(style_preset, cls.PRESETS["vivid_ember"])

        # Header and Styles
        header = f"""[Script Info]
Title: Creator Studio AI Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{preset['font_name']},{preset['font_size']},{preset['primary_color']},{preset['highlight_color']},{preset['outline_color']},{preset['back_color']},{preset['bold']},0,0,0,100,100,0,0,1,{preset['outline']},{preset['shadow']},{preset['alignment']},20,20,{preset['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for cue in cues:
            start_sec = float(cue["start"])
            end_sec = float(cue["end"])
            start_ass = cls.format_timestamp_ass(start_sec)
            end_ass = cls.format_timestamp_ass(end_sec)

            words = cue.get("words")
            if words and len(words) > 0:
                # Word-level kinetic karaoke tags: {\k<centiseconds>}Word
                karaoke_parts = []
                for w in words:
                    w_text = w.get("word", "").strip()
                    w_start = float(w.get("start", start_sec))
                    w_end = float(w.get("end", end_sec))
                    duration_cs = max(1, int(round((w_end - w_start) * 100)))
                    karaoke_parts.append(f"{{\\k{duration_cs}}}{w_text}")
                event_text = " ".join(karaoke_parts)
            else:
                raw_text = str(cue.get("text", "")).strip()
                # Split text into words with synthesized karaoke timing if duration > 0
                word_tokens = raw_text.split()
                if len(word_tokens) > 1 and end_sec > start_sec:
                    total_dur = end_sec - start_sec
                    cs_per_word = max(1, int(round((total_dur / len(word_tokens)) * 100)))
                    karaoke_parts = [f"{{\\k{cs_per_word}}}{t}" for t in word_tokens]
                    event_text = " ".join(karaoke_parts)
                else:
                    event_text = raw_text

            events.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{event_text}")

        return header + "\n".join(events) + "\n"

    @classmethod
    def generate_cues_from_scenes(
        cls, scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract or calculate cues from storyboard/timeline scenes."""
        cues = []
        for scene in scenes:
            text = scene.get("narration_text") or scene.get("script_text") or scene.get("text") or ""
            start = float(scene.get("start_time_seconds", 0.0))
            duration = float(scene.get("duration_seconds", 5.0))
            end = float(scene.get("end_time_seconds", start + duration))

            if not text.strip():
                continue

            words = scene.get("word_timestamps") or []
            cues.append({
                "start": start,
                "end": end,
                "text": text,
                "words": words,
            })
        return cues

    @classmethod
    def save_subtitles(cls, content: str, file_path: str) -> str:
        """Save subtitle content string to disk, ensuring directory exists."""
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved subtitle file: {p} ({len(content)} chars)")
        return str(p.resolve())
