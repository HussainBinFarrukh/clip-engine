from app.services.candidate_scoring import (
    HeuristicFeatures,
    compute_heuristic_features,
    deduplicate_windows,
    heuristic_score,
)
from app.services.candidate_windows import CandidateWindow


def _window(start_ms: int, end_ms: int) -> CandidateWindow:
    return CandidateWindow(
        preset="shorts_campaign",
        start_ms=start_ms,
        end_ms=end_ms,
        start_sentence_index=0,
        end_sentence_index=1,
    )


def test_compute_heuristic_features_scopes_points_to_window() -> None:
    window = _window(1000, 5000)
    loudness = [
        {"t_ms": 500, "value": -50.0},  # before window, excluded
        {"t_ms": 1000, "value": -20.0},
        {"t_ms": 3000, "value": -10.0},
        {"t_ms": 5000, "value": -5.0},  # at/after end, excluded (half-open)
    ]
    pauses = [{"t_ms": 2000, "duration_ms": 400}]
    speech_rate = [{"t_ms": 1000, "value": 150.0}, {"t_ms": 6000, "value": 999.0}]
    scene_changes = [{"t_ms": 4000}]

    features = compute_heuristic_features(window, loudness, pauses, speech_rate, scene_changes)

    assert features.avg_loudness_dbfs == -15.0  # avg of -20 and -10
    assert features.pause_ratio == round(400 / 4000, 3)
    assert features.avg_speech_rate_wpm == 150.0
    assert features.scene_change_count == 1


def test_compute_heuristic_features_handles_no_points_in_window() -> None:
    window = _window(0, 1000)
    features = compute_heuristic_features(window, [], [], [], [])

    assert features.avg_loudness_dbfs == -60.0  # silence floor
    assert features.pause_ratio == 0.0
    assert features.avg_speech_rate_wpm == 0.0
    assert features.scene_change_count == 0


def test_heuristic_score_is_bounded_and_rewards_loud_flowing_speech() -> None:
    quiet_paused = HeuristicFeatures(
        avg_loudness_dbfs=-55.0, pause_ratio=0.8, avg_speech_rate_wpm=50.0, scene_change_count=0
    )
    loud_flowing = HeuristicFeatures(
        avg_loudness_dbfs=-12.0, pause_ratio=0.05, avg_speech_rate_wpm=150.0, scene_change_count=0
    )

    quiet_score = heuristic_score(quiet_paused)
    loud_score = heuristic_score(loud_flowing)

    assert 0.0 <= quiet_score <= 100.0
    assert 0.0 <= loud_score <= 100.0
    assert loud_score > quiet_score


def test_deduplicate_windows_drops_overlapping_lower_scored() -> None:
    a = _window(0, 30_000)  # best
    b = _window(5_000, 35_000)  # overlaps a heavily, lower score
    c = _window(60_000, 90_000)  # disjoint from a/b, should survive

    kept = deduplicate_windows([(a, 90.0), (b, 50.0), (c, 70.0)], iou_threshold=0.5)

    assert a in kept
    assert c in kept
    assert b not in kept


def test_deduplicate_windows_keeps_disjoint_windows() -> None:
    a = _window(0, 10_000)
    b = _window(20_000, 30_000)

    kept = deduplicate_windows([(a, 80.0), (b, 60.0)], iou_threshold=0.5)

    assert set(kept) == {a, b}


def test_deduplicate_windows_respects_max_keep() -> None:
    windows = [(_window(i * 100_000, i * 100_000 + 10_000), float(i)) for i in range(5)]

    kept = deduplicate_windows(windows, iou_threshold=0.5, max_keep=2)

    assert len(kept) == 2
    # The two highest-scored (i=4, i=3) should be the ones kept.
    kept_starts = {w.start_ms for w in kept}
    assert kept_starts == {400_000, 300_000}
