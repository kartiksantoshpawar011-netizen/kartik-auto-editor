"""Silence detection and removal."""
import re
import subprocess
from typing import List, Tuple


def detect_long_silences(
    audio_path: str,
    threshold_db: str = "-35dB",
    min_duration: float = 0.60,
    ffmpeg_bin: str = "ffmpeg",
) -> List[Tuple[float, float]]:
    """Detect silence ranges in audio using FFmpeg silencedetect.

    Args:
        audio_path: Path to audio file
        threshold_db: Silence threshold in dB (e.g., '-35dB')
        min_duration: Minimum silence duration in seconds
        ffmpeg_bin: Path to FFmpeg executable

    Returns:
        List of (start, end) tuples for silence ranges in seconds
    """
    command = [
        ffmpeg_bin,
        "-i",
        audio_path,
        "-af",
        f"silencedetect=n={threshold_db}:d={min_duration}",
        "-f",
        "null",
        "-",
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "unknown FFmpeg error"
        raise RuntimeError(f"Silence detection failed: {error}")

    ranges: List[Tuple[float, float]] = []
    silence_start = None

    # Parse FFmpeg silencedetect output
    for line in (result.stderr or "").splitlines():
        if "silence_start" in line:
            match = re.search(r"silence_start: ([0-9.]+)", line)
            if match:
                silence_start = float(match.group(1))
        elif "silence_end" in line and silence_start is not None:
            match = re.search(r"silence_end: ([0-9.]+)", line)
            if match:
                silence_end = float(match.group(1))
                ranges.append((silence_start, silence_end))
                silence_start = None

    return ranges


def remove_silence_ranges(
    segments,
    silence_ranges: List[Tuple[float, float]],
) -> list:
    """Remove transcript segments that overlap with silence ranges.

    Args:
        segments: List of transcript segments
        silence_ranges: List of (start, end) silence ranges

    Returns:
        Filtered list of segments
    """
    if not segments:
        return []

    if not silence_ranges:
        return list(segments)

    filtered = []
    for segment in segments:
        # Check if segment overlaps with any silence range
        overlapping = False
        for silence_start, silence_end in silence_ranges:
            # Check for overlap: segment starts before silence ends AND segment ends after silence starts
            if segment.start < silence_end and segment.end > silence_start:
                overlapping = True
                break

        if not overlapping:
            filtered.append(segment)

    return filtered
