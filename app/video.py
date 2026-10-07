"""Video processing with FFmpeg."""
import subprocess
from typing import List


def _run_ffmpeg(command: List[str], description: str) -> subprocess.CompletedProcess:
    """Run FFmpeg command and handle errors."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or "unknown FFmpeg error"
        raise RuntimeError(f"{description} failed:\n{error_msg}")
    return result


def burn_subtitles(
    input_video: str,
    subtitle_path: str,
    output_video: str,
    ffmpeg_bin: str,
):
    """Burn subtitles into video using FFmpeg.

    Args:
        input_video: Path to input video
        subtitle_path: Path to ASS subtitle file
        output_video: Path to output video
        ffmpeg_bin: Path to FFmpeg executable
    """
    # Use subtitles filter to burn ASS file into video
    subtitle_filter = f"subtitles={subtitle_path.replace(chr(92), '/')}"
    subtitle_filter = subtitle_filter.replace(":", "\\:")

    command = [
        ffmpeg_bin,
        "-y",  # Overwrite output
        "-i",
        input_video,
        "-vf",
        subtitle_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_video,
    ]

    _run_ffmpeg(command, "Burning subtitles")


def crop_to_9_16(
    input_video: str,
    output_video: str,
    ffmpeg_bin: str,
):
    """Convert video to 9:16 (1080x1920) vertical format.

    Args:
        input_video: Path to input video
        output_video: Path to output video
        ffmpeg_bin: Path to FFmpeg executable
    """
    # Scale to 1080 width and pad to 1920 height (9:16 ratio)
    filter_str = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

    command = [
        ffmpeg_bin,
        "-y",  # Overwrite output
        "-i",
        input_video,
        "-vf",
        filter_str,
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_video,
    ]

    _run_ffmpeg(command, "Converting to 9:16 format")


def export_mp4(
    input_video: str,
    output_video: str,
    ffmpeg_bin: str,
):
    """Export video as H.264/AAC MP4.

    Args:
        input_video: Path to input video
        output_video: Path to output video
        ffmpeg_bin: Path to FFmpeg executable
    """
    if input_video == output_video:
        # Already in correct format
        return

    command = [
        ffmpeg_bin,
        "-y",  # Overwrite output
        "-i",
        input_video,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_video,
    ]

    _run_ffmpeg(command, "Exporting final MP4")
