"""FFmpeg command line builder with safe argument lists and advanced filtergraphs."""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path


class FFmpegCommandBuilder:
    """Builds secure, structured FFmpeg argument lists for multi-track video rendering."""

    @staticmethod
    def escape_filter_path(file_path: str) -> str:
        r"""Escape Windows / Unix path colons and backslashes for FFmpeg filter strings.
        In FFmpeg filtergraph strings, ':' must be escaped as '\:' and '\' as '/'.
        """
        # Convert all backslashes to forward slashes
        clean = Path(file_path).resolve().as_posix()
        # Escape colon (e.g. C: -> C\:)
        return clean.replace(":", r"\:")

    @classmethod
    def build_render_command(
        cls,
        ffmpeg_bin: str,
        scenes: List[Dict[str, Any]],
        output_path: str,
        narration_audio_path: Optional[str] = None,
        music_audio_path: Optional[str] = None,
        subtitle_path: Optional[str] = None,
        music_volume: float = 0.15,
        ducking_enabled: bool = True,
        ducking_db: float = -6.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        preset: str = "fast",
        crf: int = 20,
    ) -> List[str]:
        """Construct a complete argument list for FFmpeg rendering.
        Never invokes shell=True.
        """
        cmd: List[str] = [ffmpeg_bin, "-y"]

        # Track input indices
        inputs: List[str] = []
        filter_complex_parts: List[str] = []

        # 1. Add visual scene inputs
        scene_video_labels: List[str] = []
        for idx, sc in enumerate(scenes):
            asset_path = sc.get("visual_asset_path") or sc.get("asset_path")
            duration = float(sc.get("duration_seconds", 5.0))
            motion = sc.get("motion_effect", "zoom_in")

            if not asset_path or not os.path.exists(asset_path):
                # Use virtual color generator input if asset missing
                cmd.extend([
                    "-f", "lavfi",
                    "-t", f"{duration:.3f}",
                    "-i", f"color=c=0x1E222B:s={width}x{height}:r={fps}",
                ])
                scene_video_labels.append(f"[{idx}:v]")
            else:
                ext = Path(asset_path).suffix.lower()
                is_image = ext in [".jpg", ".jpeg", ".png", ".webp"]
                if is_image:
                    cmd.extend([
                        "-loop", "1",
                        "-t", f"{duration:.3f}",
                        "-i", str(Path(asset_path).resolve()),
                    ])
                    # Apply scale, pad, and optional motion effect (zoompan)
                    in_label = f"[{idx}:v]"
                    out_label = f"[v_scene_{idx}]"

                    # Calculate frames for zoompan
                    frames = max(1, int(round(duration * fps)))
                    if motion == "zoom_in":
                        zoom_expr = f"min(zoom+0.0015,1.25)"
                        pan_filter = (
                            f"scale={width*2}:{height*2},"
                            f"zoompan=z='{zoom_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
                        )
                    elif motion == "zoom_out":
                        zoom_expr = f"max(1.25-0.0015*on,1.0)"
                        pan_filter = (
                            f"scale={width*2}:{height*2},"
                            f"zoompan=z='{zoom_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
                        )
                    else:
                        pan_filter = (
                            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,"
                            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
                        )

                    filter_complex_parts.append(f"{in_label}{pan_filter}{out_label}")
                    scene_video_labels.append(out_label)
                else:
                    # Video clip asset
                    cmd.extend([
                        "-t", f"{duration:.3f}",
                        "-i", str(Path(asset_path).resolve()),
                    ])
                    in_label = f"[{idx}:v]"
                    out_label = f"[v_scene_{idx}]"
                    scale_filter = (
                        f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
                    )
                    filter_complex_parts.append(f"{in_label}{scale_filter}{out_label}")
                    scene_video_labels.append(out_label)

        # 2. Concatenate visual scenes
        num_scenes = len(scene_video_labels)
        if num_scenes == 0:
            # Fallback if no scenes passed: generate black background 5s
            cmd.extend([
                "-f", "lavfi",
                "-t", "5.0",
                "-i", f"color=c=0x1E222B:s={width}x{height}:r={fps}",
            ])
            concat_out = "[0:v]"
        elif num_scenes == 1:
            concat_out = scene_video_labels[0]
        else:
            inputs_str = "".join(scene_video_labels)
            concat_out = "[v_concat]"
            filter_complex_parts.append(f"{inputs_str}concat=n={num_scenes}:v=1:a=0{concat_out}")

        # 3. Burn Subtitles if provided
        final_video_label = concat_out
        if subtitle_path and os.path.exists(subtitle_path):
            escaped_sub = cls.escape_filter_path(subtitle_path)
            sub_out = "[v_sub]"
            if subtitle_path.lower().endswith(".ass"):
                sub_filter = f"ass='{escaped_sub}'"
            else:
                sub_filter = f"subtitles='{escaped_sub}'"
            filter_complex_parts.append(f"{concat_out}{sub_filter}{sub_out}")
            final_video_label = sub_out

        # 4. Audio Processing
        next_input_idx = max(num_scenes, 1) if num_scenes > 0 else 1
        narr_input_idx: Optional[int] = None
        music_input_idx: Optional[int] = None

        if narration_audio_path and os.path.exists(narration_audio_path):
            cmd.extend(["-i", str(Path(narration_audio_path).resolve())])
            narr_input_idx = next_input_idx
            next_input_idx += 1

        if music_audio_path and os.path.exists(music_audio_path):
            # Stream loop for background music so it covers full video length
            cmd.extend(["-stream_loop", "-1", "-i", str(Path(music_audio_path).resolve())])
            music_input_idx = next_input_idx
            next_input_idx += 1

        # Build audio filter graph
        final_audio_label = "[aout]"
        if narr_input_idx is not None and music_input_idx is not None:
            # Multi-track mixing with sidechain ducking
            if ducking_enabled:
                # Duck background music by -6dB during narration
                filter_complex_parts.append(
                    f"[{music_input_idx}:a]volume={music_volume}[music_raw];"
                    f"[{narr_input_idx}:a]volume=1.0[narr_raw];"
                    f"[music_raw][narr_raw]sidechaincompress=threshold=0.15:ratio=4:attack=50:release=300[ducked_music];"
                    f"[narr_raw][ducked_music]amix=inputs=2:duration=first:dropout_transition=2,aformat=sample_rates=48000:channel_layouts=stereo{final_audio_label}"
                )
            else:
                filter_complex_parts.append(
                    f"[{music_input_idx}:a]volume={music_volume}[music_raw];"
                    f"[{narr_input_idx}:a]volume=1.0[narr_raw];"
                    f"[narr_raw][music_raw]amix=inputs=2:duration=first,aformat=sample_rates=48000:channel_layouts=stereo{final_audio_label}"
                )
        elif narr_input_idx is not None:
            filter_complex_parts.append(
                f"[{narr_input_idx}:a]volume=1.0,aformat=sample_rates=48000:channel_layouts=stereo{final_audio_label}"
            )
        elif music_input_idx is not None:
            filter_complex_parts.append(
                f"[{music_input_idx}:a]volume={music_volume},aformat=sample_rates=48000:channel_layouts=stereo{final_audio_label}"
            )
        else:
            # Generate silent stereo audio track
            cmd.extend([
                "-f", "lavfi",
                "-i", "anullsrc=r=48000:cl=stereo",
            ])
            final_audio_label = f"[{next_input_idx}:a]"

        # Assemble filter complex flag if there are filter instructions
        if filter_complex_parts:
            full_filter = ";".join(filter_complex_parts)
            cmd.extend(["-filter_complex", full_filter])
            cmd.extend(["-map", final_video_label])
            cmd.extend(["-map", final_audio_label])
        else:
            cmd.extend(["-map", "0:v"])
            cmd.extend(["-map", "0:a?"])

        # Encoders, flags, and destination
        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", preset,
            "-crf", str(crf),
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            "-shortest",
            str(Path(output_path).resolve()),
        ])

        return cmd
