"""Main video processing pipeline."""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from imageio_ffmpeg import get_ffmpeg_exe

from app.captions import create_ass_file
from app.fillers import remove_filler_ranges
from app.silence import detect_long_silences, remove_silence_ranges
from app.transcription import transcribe_audio
from app.video import burn_subtitles, crop_to_9_16, export_mp4


class VideoEditPipeline:
    """Complete video processing pipeline."""

    def __init__(
        self,
        output_dir: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.progress_callback = progress_callback or (lambda *_: None)
        self.log_callback = log_callback or (lambda *_: None)

        # Get FFmpeg from imageio-ffmpeg package
        self.ffmpeg_path = Path(get_ffmpeg_exe())
        if not self.ffmpeg_path.exists():
            raise RuntimeError(
                f"FFmpeg binary not found at: {self.ffmpeg_path}\n"
                "Ensure imageio-ffmpeg is installed: pip install imageio-ffmpeg"
            )

        # Model cache directory
        self.model_dir = Path.cwd() / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Temporary work directory
        self.work_dir = Path.cwd() / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def emit_progress(self, value: int, text: str):
        """Emit progress update."""
        self.progress_callback(value, text)
        if text:
            self.log_callback(f"[{value}%] {text}")

    def run_ffmpeg(self, command: List[str], description: str) -> subprocess.CompletedProcess:
        """Run FFmpeg command and handle errors."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown FFmpeg error"
                raise RuntimeError(f"{description} failed:\n{error_msg}")
            return result
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"FFmpeg not found. Ensure imageio-ffmpeg is installed correctly.\nDetails: {exc}"
            ) from exc

    def extract_audio(self, source_video: str, output_audio: str):
        """Extract mono 16kHz audio from video."""
        self.emit_progress(10, "Extracting mono 16kHz audio...")

        command = [
            str(self.ffmpeg_path),
            "-y",  # Overwrite output
            "-i",
            str(source_video),
            "-vn",  # No video
            "-ac",
            "1",  # Mono
            "-ar",
            "16000",  # 16kHz sample rate
            "-c:a",
            "pcm_s16le",  # 16-bit PCM
            str(output_audio),
        ]
        self.run_ffmpeg(command, "Audio extraction")
        self.log_callback(f"✓ Audio extracted: {output_audio}")

    def process(self, video_path: str, model_name: str = "base") -> str:
        """Execute complete video processing pipeline."""
        # Validation
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not self.ffmpeg_path.exists():
            raise RuntimeError(
                f"FFmpeg binary not available at {self.ffmpeg_path}.\n"
                "Install with: pip install imageio-ffmpeg"
            )

        # Normalize model name
        model_name = model_name.lower().strip()
        if model_name not in {"tiny", "base", "small"}:
            self.log_callback(f"⚠ Unknown model '{model_name}', using 'base'")
            model_name = "base"

        # Prepare paths
        base_name = Path(video_path).stem
        audio_path = self.work_dir / f"{base_name}_audio.wav"
        ass_path = self.work_dir / f"{base_name}_captions.ass"
        edited_video = self.work_dir / f"{base_name}_edited.mp4"
        final_video = self.output_dir / f"{base_name}_final.mp4"

        # Clean up previous work if needed
        for f in [audio_path, ass_path, edited_video]:
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass

        try:
            # ===== STEP 1: Extract Audio =====
            self.emit_progress(5, "Step 1: Extracting audio...")
            self.extract_audio(video_path, str(audio_path))

            # ===== STEP 2: Transcribe =====
            self.emit_progress(20, "Step 2: Transcribing with faster-whisper...")
            self.log_callback(f"Using Whisper model: {model_name}")
            transcript = transcribe_audio(
                str(audio_path),
                model_name=model_name,
                model_dir=str(self.model_dir),
            )
            if not transcript:
                raise RuntimeError(
                    "Transcription failed: No speech detected or audio too short.\n"
                    "Try a different video or check audio quality."
                )
            self.log_callback(f"✓ Transcribed {len(transcript)} segments")

            # ===== STEP 3: Detect Long Silences =====
            self.emit_progress(35, "Step 3: Detecting long silences...")
            silence_ranges = detect_long_silences(
                str(audio_path),
                threshold_db="-35dB",
                min_duration=0.60,
                ffmpeg_bin=str(self.ffmpeg_path),
            )
            self.log_callback(f"✓ Found {len(silence_ranges)} silence sections")

            # ===== STEP 4: Remove Silence Ranges =====
            self.emit_progress(45, "Step 4: Removing silence sections...")
            cleaned_segments = remove_silence_ranges(transcript, silence_ranges)
            self.log_callback(f"✓ Removed silences: {len(transcript)} → {len(cleaned_segments)} segments")

            # ===== STEP 5: Detect Filler Words =====
            self.emit_progress(55, "Step 5: Detecting filler words...")
            initial_count = len(cleaned_segments)
            cleaned_segments = remove_filler_ranges(cleaned_segments)
            self.log_callback(f"✓ Removed fillers: {initial_count} → {len(cleaned_segments)} segments")

            if not cleaned_segments:
                raise RuntimeError(
                    "No usable content remains after silence and filler removal.\n"
                    "The video may be too short or contain mostly silence/fillers.\n"
                    "Try a different video or adjust thresholds."
                )

            # ===== STEP 6: Generate ASS Subtitles =====
            self.emit_progress(65, "Step 6: Generating ASS subtitle file...")
            create_ass_file(cleaned_segments, str(ass_path))
            self.log_callback(f"✓ ASS file created: {ass_path.name}")

            # ===== STEP 7: Burn Subtitles =====
            self.emit_progress(75, "Step 7: Burning captions into video...")
            burn_subtitles(
                str(video_path),
                str(ass_path),
                str(edited_video),
                str(self.ffmpeg_path),
            )
            self.log_callback(f"✓ Captions burned: {edited_video.name}")

            # ===== STEP 8: Crop to 9:16 =====
            self.emit_progress(85, "Step 8: Converting to 9:16 vertical format...")
            crop_to_9_16(str(edited_video), str(final_video), str(self.ffmpeg_path))
            self.log_callback(f"✓ Cropped to 1080x1920 (9:16): {final_video.name}")

            # ===== STEP 9: Export Final MP4 =====
            self.emit_progress(95, "Step 9: Exporting H.264/AAC MP4...")
            export_mp4(str(final_video), str(final_video), str(self.ffmpeg_path))
            self.log_callback(f"✓ Final MP4 ready")

            self.emit_progress(100, "✓ Processing complete!")
            self.log_callback(f"\n✓ SUCCESS: Video exported to {final_video}")

            # Cleanup temp files
            for f in [audio_path, ass_path, edited_video]:
                if f.exists():
                    try:
                        f.unlink()
                    except Exception:
                        pass

            return str(final_video)

        except Exception as exc:
            self.emit_progress(0, "✗ Error")
            error_msg = str(exc)
            self.log_callback(f"\n✗ ERROR: {error_msg}")
            raise
