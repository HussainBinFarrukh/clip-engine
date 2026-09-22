from dataclasses import dataclass


@dataclass(frozen=True)
class ClipPreset:
    name: str
    min_duration_ms: int
    max_duration_ms: int
    aspect_ratio: str


# Mirrors the "Clip length presets" table in AGENTS.md. Single source of
# truth for candidate window generation (T07) and, later, rendering (T11+).
CLIP_PRESETS: dict[str, ClipPreset] = {
    "shorts_campaign": ClipPreset("shorts_campaign", 15_000, 60_000, "9:16"),
    "shorts_long": ClipPreset("shorts_long", 60_000, 180_000, "9:16"),
    "tiktok_rewards": ClipPreset("tiktok_rewards", 61_000, 180_000, "9:16"),
    "longform": ClipPreset("longform", 8 * 60_000, 20 * 60_000, "16:9"),
}
