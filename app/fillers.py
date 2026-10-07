"""Filler word detection and removal."""
import re
from typing import List, Tuple

# Common filler words in English and Hinglish
FILLER_WORDS = {
    # English
    "uh",
    "um",
    "umm",
    "hmm",
    "er",
    "like",
    "youknow",
    "youknowwhat",
    "actually",
    "basically",
    "literally",
    "so",
    "okay",
    "ok",
    "right",
    "yeah",
    "ya",
    "well",
    "anyway",
    "apparently",
    "clearly",
    "presumably",
    "indeed",
    "however",
    "furthermore",
    "moreover",
    # Hinglish
    "bhai",
    "bro",
    "toh",
    "wese",
    "haan",
    "nahi",
    "dekho",
    "arre",
    "aur",
    "matlab",
    "ji",
    "type",
    "thing",
    "kind",
    "sort",
}


def _normalize_word(word: str) -> str:
    """Normalize a word for filler detection."""
    if not word:
        return ""

    word = word.lower().strip()
    # Normalize quotes
    word = word.replace("\u2019", "'")
    word = word.replace("\u2018", "'")
    # Keep alphanumerics and Devanagari
    word = re.sub(r"[^a-zA-Z0-9\u0900-\u097F']+", "", word)
    return word


def detect_filler_ranges(segments) -> List[Tuple[float, float]]:
    """Detect time ranges of filler words in transcript.

    Args:
        segments: List of transcript segments

    Returns:
        List of (start, end) tuples for filler word ranges
    """
    ranges: List[Tuple[float, float]] = []

    # Find all filler words
    for segment in segments:
        for word in getattr(segment, "words", []) or []:
            normalized = _normalize_word(word.word)
            if normalized in FILLER_WORDS:
                ranges.append((word.start, word.end))

    if not ranges:
        return []

    # Merge neighboring filler ranges (with 0.25s tolerance)
    merged = []
    for start, end in sorted(ranges):
        if not merged or start - merged[-1][1] > 0.25:
            # New filler section
            merged.append([start, end])
        else:
            # Extend previous filler section
            merged[-1][1] = max(merged[-1][1], end)

    return [(start, end) for start, end in merged]


def remove_filler_ranges(segments) -> list:
    """Remove transcript segments that are filler words.

    Args:
        segments: List of transcript segments

    Returns:
        Filtered list of segments
    """
    filler_ranges = detect_filler_ranges(segments)
    if not filler_ranges:
        return list(segments)

    cleaned = []
    for segment in segments:
        # Check if segment overlaps with any filler range
        overlapping = False
        for filler_start, filler_end in filler_ranges:
            if segment.start < filler_end and segment.end > filler_start:
                overlapping = True
                break

        if not overlapping:
            cleaned.append(segment)

    return cleaned
