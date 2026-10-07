"""Audio transcription with faster-whisper."""
import os
import re
from typing import List, Optional

from faster_whisper import WhisperModel


class TranscriptWord:
    """Represents a single word with timestamps."""

    def __init__(self, word: str, start: float, end: float):
        self.word = word.strip()
        self.start = float(start)
        self.end = float(end)

    def __repr__(self):
        return f"TranscriptWord('{self.word}', {self.start:.3f}s-{self.end:.3f}s)"


class TranscriptSegment:
    """Represents a transcript segment with word-level timestamps."""

    def __init__(self, start: float, end: float, text: str, words: Optional[List[TranscriptWord]] = None):
        self.start = float(start)
        self.end = float(end)
        self.text = text.strip()
        self.words = words or []

    def __repr__(self):
        return f"TranscriptSegment({self.start:.3f}s-{self.end:.3f}s, '{self.text[:50]}...')"


def _clean_token(token: str) -> str:
    """Clean and normalize a word token."""
    if not token:
        return ""

    token = token.strip()
    # Normalize quotes
    token = token.replace("\u2019", "'")
    token = token.replace("\u2018", "'")
    token = token.replace("\u201d", '"')
    token = token.replace("\u201c", '"')
    # Keep alphanumerics, Hindi (Devanagari), and common punctuation
    token = re.sub(r"[^A-Za-z0-9\u0900-\u097F'\-]+", "", token)
    return token


def transcribe_audio(
    audio_path: str,
    model_name: str = "base",
    model_dir: str = "models",
) -> List[TranscriptSegment]:
    """Transcribe audio file using faster-whisper.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        model_name: Whisper model size: 'tiny', 'base', 'small'
        model_dir: Directory to cache downloaded models

    Returns:
        List of TranscriptSegment objects with word-level timestamps
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model_name = model_name.lower().strip()
    if model_name not in {"tiny", "base", "small"}:
        model_name = "base"

    # Load Whisper model (downloads if not cached)
    model = WhisperModel(
        model_name,
        device="cpu",  # Use CPU for Windows compatibility
        compute_type="int8",  # Quantized for speed and memory
        download_root=model_dir,
    )

    # Transcribe with word-level timestamps
    segments, _ = model.transcribe(
        audio_path,
        word_timestamps=True,
        beam_size=5,
        language="en",  # Default to English
    )

    transcript: List[TranscriptSegment] = []

    for segment in segments:
        text = (segment.text or "").strip()
        if not text:
            continue

        # Extract word-level timestamps
        words: List[TranscriptWord] = []
        for word in getattr(segment, "words", []) or []:
            word_text = getattr(word, "word", "")
            if not word_text:
                continue

            clean_word = _clean_token(word_text)
            if not clean_word:
                continue

            words.append(
                TranscriptWord(
                    word=clean_word,
                    start=float(getattr(word, "start", 0.0) or 0.0),
                    end=float(getattr(word, "end", 0.0) or 0.0),
                )
            )

        transcript.append(
            TranscriptSegment(
                start=float(getattr(segment, "start", 0.0) or 0.0),
                end=float(getattr(segment, "end", 0.0) or 0.0),
                text=text,
                words=words,
            )
        )

    return transcript
