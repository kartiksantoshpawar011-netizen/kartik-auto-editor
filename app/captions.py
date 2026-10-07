"""ASS subtitle file generation."""
from pathlib import Path
from typing import List


def _escape_ass_text(text: str) -> str:
    """Escape special characters for ASS subtitle format."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
    )


def _format_ass_time(milliseconds: int) -> str:
    """Format time for ASS subtitle format (HH:MM:SS.CC)."""
    total_seconds, ms = divmod(milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # ASS uses centiseconds, not milliseconds
    centiseconds = ms // 10
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(centiseconds):02d}"


def create_ass_file(segments, output_path: str):
    """Generate ASS subtitle file from transcript segments.

    Args:
        segments: List of transcript segments
        output_path: Path to save ASS file
    """
    # ASS format header
    script = [
        "[Script Info]",
        "Title: Kartik Auto Editor Captions",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.601",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Default style with Unicode font for Hindi support
        "Style: Default,Noto Sans Devanagari,54,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,20,20,120,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # Add dialogue lines
    for segment in segments:
        text = getattr(segment, "text", "").strip()
        if not text:
            continue

        # Convert seconds to milliseconds
        start_ms = int(segment.start * 1000)
        end_ms = int(segment.end * 1000)

        # Format times
        start_time = _format_ass_time(start_ms)
        end_time = _format_ass_time(end_ms)

        # Escape special characters
        safe_text = _escape_ass_text(text)

        # Add dialogue line
        # Format: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        # Using \pos() to position at bottom center and \an2 for bottom alignment
        dialogue = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\pos(540,1700)}}{{\\an2}}{safe_text}"
        script.append(dialogue)

    # Write ASS file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(script) + "\n", encoding="utf-8")
