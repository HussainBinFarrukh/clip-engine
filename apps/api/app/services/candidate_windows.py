from dataclasses import dataclass

from app.services.clip_presets import ClipPreset


@dataclass(frozen=True)
class SentenceBoundary:
    """One sentence (transcript segment), used as the only place a
    candidate window is allowed to start or end."""

    index: int
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class CandidateWindow:
    preset: str
    start_ms: int
    end_ms: int
    start_sentence_index: int
    end_sentence_index: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def sentences_from_segments(segments: list[dict]) -> list[SentenceBoundary]:
    """Build sentence boundaries from transcript segments, in time order.

    `segments` items need only `start_ms`/`end_ms` (e.g. TranscriptSegment
    rows, or plain dicts in tests).
    """
    ordered = sorted(segments, key=lambda s: s["start_ms"])
    return [
        SentenceBoundary(index=i, start_ms=s["start_ms"], end_ms=s["end_ms"])
        for i, s in enumerate(ordered)
    ]


def generate_candidate_windows(
    sentences: list[SentenceBoundary], preset: ClipPreset
) -> list[CandidateWindow]:
    """Every window whose duration fits `preset`'s bounds, snapped to
    sentence boundaries.

    For each starting sentence, sentences are added one at a time until
    the window would exceed the preset's max duration; every window in
    between that also meets the min duration is kept. Because a window's
    start and end are always exactly some sentence's start_ms/end_ms, no
    window can ever cut a sentence. Overlapping windows (different start
    sentences covering the same stretch of time) are expected, not
    deduplicated — scoring in a later task picks among them.
    """
    windows: list[CandidateWindow] = []
    n = len(sentences)

    for i in range(n):
        start_ms = sentences[i].start_ms
        for j in range(i, n):
            end_ms = sentences[j].end_ms
            duration = end_ms - start_ms
            if duration > preset.max_duration_ms:
                break
            if duration >= preset.min_duration_ms:
                windows.append(
                    CandidateWindow(
                        preset=preset.name,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        start_sentence_index=i,
                        end_sentence_index=j,
                    )
                )

    return windows
