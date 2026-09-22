import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoProbe:
    duration_ms: int | None
    width: int | None
    height: int | None
    frame_rate: str | None


class FFProbeError(RuntimeError):
    pass


def probe_video(path: Path) -> VideoProbe:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise FFProbeError(f"ffprobe failed for {path}: {exc}") from exc

    payload = json.loads(result.stdout)
    video_stream = next(
        (s for s in payload.get("streams", []) if s.get("codec_type") == "video"), None
    )

    duration_ms = None
    format_duration = payload.get("format", {}).get("duration")
    if format_duration is not None:
        duration_ms = round(float(format_duration) * 1000)

    width = video_stream.get("width") if video_stream else None
    height = video_stream.get("height") if video_stream else None
    frame_rate = video_stream.get("r_frame_rate") if video_stream else None

    return VideoProbe(
        duration_ms=duration_ms,
        width=width,
        height=height,
        frame_rate=frame_rate,
    )
