from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.services.candidate_windows import CandidateWindow

_SILENCE_FLOOR_DBFS = -60.0
_LOUD_CEILING_DBFS = -10.0


class ClipCandidateScore(BaseModel):
    """Structured output schema for the clip_scoring LLM prompt."""

    hook_line: bool
    self_contained: bool
    emotional_peak: bool
    quotable_line: str | None = None
    score: int = Field(ge=0, le=100)
    reason: str


@dataclass(frozen=True)
class HeuristicFeatures:
    avg_loudness_dbfs: float
    pause_ratio: float  # fraction of the window spent in pauses
    avg_speech_rate_wpm: float
    scene_change_count: int


def _points_in_window(points: list[dict], start_ms: int, end_ms: int) -> list[dict]:
    return [p for p in points if start_ms <= p["t_ms"] < end_ms]


def compute_heuristic_features(
    window: CandidateWindow,
    loudness_points: list[dict],
    pause_points: list[dict],
    speech_rate_points: list[dict],
    scene_change_points: list[dict],
) -> HeuristicFeatures:
    """Pure feature extraction from T06's stored signals, scoped to one
    candidate window's time range. No DB/LLM access — takes plain point
    lists so it's trivially testable with synthetic data."""
    loud = _points_in_window(loudness_points, window.start_ms, window.end_ms)
    avg_loudness = sum(p["value"] for p in loud) / len(loud) if loud else _SILENCE_FLOOR_DBFS

    pauses = _points_in_window(pause_points, window.start_ms, window.end_ms)
    pause_ms = sum(p["duration_ms"] for p in pauses)
    pause_ratio = min(1.0, pause_ms / window.duration_ms) if window.duration_ms > 0 else 0.0

    rates = _points_in_window(speech_rate_points, window.start_ms, window.end_ms)
    avg_rate = sum(p["value"] for p in rates) / len(rates) if rates else 0.0

    scene_changes = len(_points_in_window(scene_change_points, window.start_ms, window.end_ms))

    return HeuristicFeatures(
        avg_loudness_dbfs=round(avg_loudness, 1),
        pause_ratio=round(pause_ratio, 3),
        avg_speech_rate_wpm=round(avg_rate, 1),
        scene_change_count=scene_changes,
    )


def heuristic_score(features: HeuristicFeatures) -> float:
    """A simple, explicitly-tunable 0-100 blend of the heuristic features.

    Not validated against real clip performance — nothing has been
    published yet to validate against. AGENTS.md's learning loop
    (performance metrics joining on candidate ID) is exactly what will
    eventually justify a different formula or weights; until then this is
    a documented starting point, not a tuned model.
    """
    loudness_span = _LOUD_CEILING_DBFS - _SILENCE_FLOOR_DBFS
    loudness_norm = (features.avg_loudness_dbfs - _SILENCE_FLOOR_DBFS) / loudness_span
    loudness_norm = max(0.0, min(1.0, loudness_norm))

    flow_norm = max(0.0, 1.0 - features.pause_ratio)

    # 180 wpm is a fast-but-natural upper reference; faster doesn't score higher.
    rate_norm = max(0.0, min(1.0, features.avg_speech_rate_wpm / 180))

    score = 100 * (0.4 * loudness_norm + 0.4 * flow_norm + 0.2 * rate_norm)
    return round(score, 1)


def _overlap_fraction(a: CandidateWindow, b: CandidateWindow) -> float:
    """Intersection over union of the two windows' time ranges."""
    intersection = max(0, min(a.end_ms, b.end_ms) - max(a.start_ms, b.start_ms))
    union = (a.end_ms - a.start_ms) + (b.end_ms - b.start_ms) - intersection
    return intersection / union if union > 0 else 0.0


def deduplicate_windows(
    scored_windows: list[tuple[CandidateWindow, float]],
    iou_threshold: float = 0.5,
    max_keep: int | None = None,
) -> list[CandidateWindow]:
    """Non-maximum suppression: keep the highest-scoring window, drop any
    remaining window that overlaps a kept one by more than `iou_threshold`,
    repeat. Cheap (heuristic-score-only) pass before the expensive LLM call,
    so near-duplicate windows from T07's overlap-allowed generation don't
    all get scored individually.
    """
    ordered = sorted(scored_windows, key=lambda pair: pair[1], reverse=True)
    kept: list[CandidateWindow] = []

    for window, _score in ordered:
        if max_keep is not None and len(kept) >= max_keep:
            break
        if all(_overlap_fraction(window, k) < iou_threshold for k in kept):
            kept.append(window)

    return kept
