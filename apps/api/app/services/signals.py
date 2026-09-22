import math
import wave
from array import array
from pathlib import Path

_RMS_WINDOW_MS = 200
_SILENCE_FLOOR_DBFS = -60.0
_PAUSE_THRESHOLD_MS = 300


def compute_loudness_rms(wav_path: Path) -> list[dict]:
    """RMS energy in dBFS over fixed windows of a 16-bit mono PCM WAV."""
    with wave.open(str(wav_path), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frame_rate = wav_file.getframerate()
        if sample_width != 2:
            raise ValueError(f"expected 16-bit PCM WAV, got sample width {sample_width}")

        window_frames = max(1, round(frame_rate * _RMS_WINDOW_MS / 1000))
        full_scale = float(2 ** (8 * sample_width - 1))

        points: list[dict] = []
        frame_index = 0
        while True:
            raw = wav_file.readframes(window_frames)
            if not raw:
                break
            samples = array("h")
            samples.frombytes(raw)
            if channels > 1:
                samples = samples[::channels]

            if samples:
                mean_square = sum(s * s for s in samples) / len(samples)
                rms = math.sqrt(mean_square)
                dbfs = 20 * math.log10(rms / full_scale) if rms > 0 else _SILENCE_FLOOR_DBFS
            else:
                dbfs = _SILENCE_FLOOR_DBFS

            t_ms = round(frame_index / frame_rate * 1000)
            points.append({"t_ms": t_ms, "value": round(max(dbfs, _SILENCE_FLOOR_DBFS), 1)})
            frame_index += window_frames

        return points


def compute_scene_changes(video_path: Path) -> list[dict]:
    """Content-aware scene cut timestamps via PySceneDetect."""
    from scenedetect import ContentDetector, SceneManager, open_video

    video = open_video(str(video_path))
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()

    # Each scene's start is the previous scene's cut point; skip the first
    # (t=0, not a real cut) and dedupe consecutive identical starts.
    points = []
    for scene_start, _scene_end in scene_list[1:]:
        points.append({"t_ms": round(scene_start.get_seconds() * 1000)})
    return points


def compute_pauses(transcript_words: list[dict]) -> list[dict]:
    """Gaps between consecutive words (across the whole transcript) longer
    than the pause threshold."""
    points = []
    for previous, current in zip(transcript_words, transcript_words[1:], strict=False):
        gap_ms = current["start_ms"] - previous["end_ms"]
        if gap_ms >= _PAUSE_THRESHOLD_MS:
            points.append({"t_ms": previous["end_ms"], "duration_ms": gap_ms})
    return points


def compute_speech_rate(transcript_segments: list[dict]) -> list[dict]:
    """Words per minute, one point per transcript segment."""
    points = []
    for segment in transcript_segments:
        duration_ms = segment["end_ms"] - segment["start_ms"]
        if duration_ms <= 0:
            continue
        word_count = len(segment["words"])
        wpm = word_count / (duration_ms / 1000 / 60)
        points.append({"t_ms": segment["start_ms"], "value": round(wpm, 1)})
    return points
