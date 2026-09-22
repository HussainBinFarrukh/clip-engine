export const VIDEO_PLAYER_ELEMENT_ID = "source-video-player";

export function seekVideoPlayer(startMs: number, autoplay = true): void {
  const player = document.getElementById(
    VIDEO_PLAYER_ELEMENT_ID,
  ) as HTMLVideoElement | null;
  if (!player) return;
  player.currentTime = startMs / 1000;
  if (autoplay) {
    player.play();
  }
}
