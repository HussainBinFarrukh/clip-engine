from fastapi.testclient import TestClient

from app.services.candidate_windows import (
    generate_candidate_windows,
    sentences_from_segments,
)
from app.services.clip_presets import CLIP_PRESETS
from tests.conftest import FIXTURE_VIDEO


def _synthetic_segments(count: int, sentence_ms: int, gap_ms: int) -> list[dict]:
    """`count` back-to-back sentences of `sentence_ms` each, `gap_ms` apart —
    enough total duration to exercise presets longer than the real fixture
    (whose actual spoken content is only ~37s)."""
    segments = []
    t = 0
    for _ in range(count):
        segments.append({"start_ms": t, "end_ms": t + sentence_ms})
        t += sentence_ms + gap_ms
    return segments


def _assert_windows_are_bounded_and_snapped(windows, preset, sentences) -> None:
    boundary_starts = {s.start_ms for s in sentences}
    boundary_ends = {s.end_ms for s in sentences}
    for window in windows:
        assert preset.min_duration_ms <= window.duration_ms <= preset.max_duration_ms
        assert window.start_ms in boundary_starts
        assert window.end_ms in boundary_ends
        assert window.preset == preset.name


def test_all_presets_yield_only_correctly_bounded_snapped_windows() -> None:
    # 200 sentences comfortably covers every preset, including longform's
    # 8-20 minute range, without needing an actual multi-minute fixture.
    segments = _synthetic_segments(count=200, sentence_ms=4_000, gap_ms=500)
    sentences = sentences_from_segments(segments)

    for preset in CLIP_PRESETS.values():
        windows = generate_candidate_windows(sentences, preset)
        assert len(windows) > 0, f"{preset.name} produced no windows at all"
        _assert_windows_are_bounded_and_snapped(windows, preset, sentences)


def test_windows_never_cut_a_sentence() -> None:
    segments = _synthetic_segments(count=30, sentence_ms=3_000, gap_ms=400)
    sentences = sentences_from_segments(segments)
    preset = CLIP_PRESETS["shorts_campaign"]

    windows = generate_candidate_windows(sentences, preset)
    assert len(windows) > 0

    for window in windows:
        for sentence in sentences:
            # A window boundary must never fall strictly inside a sentence.
            cuts_start = sentence.start_ms < window.start_ms < sentence.end_ms
            cuts_end = sentence.start_ms < window.end_ms < sentence.end_ms
            assert not cuts_start
            assert not cuts_end


def test_overlapping_windows_are_produced_not_deduplicated() -> None:
    segments = _synthetic_segments(count=10, sentence_ms=5_000, gap_ms=1_000)
    sentences = sentences_from_segments(segments)
    preset = CLIP_PRESETS["shorts_campaign"]

    windows = generate_candidate_windows(sentences, preset)

    # Multiple windows should start at different sentences but cover
    # overlapping time ranges (a real preset yields more than one option
    # per moment, per AGENTS.md: "A strong moment may yield candidates for
    # several presets" — and, within a preset, several start points).
    starts = {w.start_sentence_index for w in windows}
    assert len(starts) > 1
    first_window = windows[0]
    overlapping = [
        w
        for w in windows
        if w is not first_window
        and w.start_ms < first_window.end_ms
        and w.end_ms > first_window.start_ms
    ]
    assert len(overlapping) > 0


def test_no_sentences_yields_no_windows() -> None:
    preset = CLIP_PRESETS["shorts_campaign"]
    assert generate_candidate_windows([], preset) == []


def test_sentences_from_segments_sorts_and_reindexes() -> None:
    segments = [
        {"start_ms": 5000, "end_ms": 6000},
        {"start_ms": 0, "end_ms": 1000},
        {"start_ms": 2000, "end_ms": 3000},
    ]
    sentences = sentences_from_segments(segments)
    assert [s.start_ms for s in sentences] == [0, 2000, 5000]
    assert [s.index for s in sentences] == [0, 1, 2]


def test_real_fixture_transcript_yields_bounded_unsnapped_free_windows(
    client: TestClient,
) -> None:
    project_id = client.post("/projects", json={"name": "Windows Project"}).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Fixture", "source_kind": "local_upload"},
    ).json()
    with FIXTURE_VIDEO.open("rb") as fixture_file:
        client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("speech_45s.mp4", fixture_file, "video/mp4")},
        )
    client.post(f"/projects/{project_id}/sources/{source['id']}/transcribe")

    transcript = client.get(f"/sources/{source['id']}/transcript").json()
    segments = transcript["segments"]
    words = [word for segment in segments for word in segment["words"]]

    sentences = sentences_from_segments(segments)
    preset = CLIP_PRESETS["shorts_campaign"]
    windows = generate_candidate_windows(sentences, preset)

    assert len(windows) > 0
    for window in windows:
        assert preset.min_duration_ms <= window.duration_ms <= preset.max_duration_ms
        # Stronger, word-level version of "never cuts a sentence": no word
        # is left straddling a window boundary.
        for word in words:
            assert not (word["start_ms"] < window.start_ms < word["end_ms"])
            assert not (word["start_ms"] < window.end_ms < word["end_ms"])
