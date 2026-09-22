import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def extract_audio_16k_mono_wav(source_path: Path, dest_path: Path) -> None:
    """Extract the audio track as 16 kHz mono PCM WAV, the format faster-whisper expects."""
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(dest_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise FFmpegError(f"audio extraction failed for {source_path}: {exc}") from exc
