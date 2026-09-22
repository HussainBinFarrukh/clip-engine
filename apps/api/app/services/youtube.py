from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class DownloadedVideo:
    path: Path
    title: str


class YouTubeDownloadError(RuntimeError):
    pass


class YouTubeSourceProvider(ABC):
    """Downloads the video behind a YouTube URL for local processing.

    This runs against YouTube's Terms of Service and API Developer Policies;
    the user providing the URL is responsible for having the rights to it.
    See docs/DECISIONS.md ("Remove Source Rights Gate; Allow YouTube Download").
    """

    @abstractmethod
    def fetch(self, url: str, dest_dir: Path) -> DownloadedVideo: ...


class YtDlpYouTubeProvider(YouTubeSourceProvider):
    def fetch(self, url: str, dest_dir: Path) -> DownloadedVideo:
        try:
            import yt_dlp
        except ImportError as exc:  # pragma: no cover - dependency always installed in the image
            raise YouTubeDownloadError("yt-dlp is not installed") from exc

        dest_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(dest_dir / "%(id)s.%(ext)s")

        options = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_path = Path(ydl.prepare_filename(info))
        except Exception as exc:  # yt_dlp raises its own DownloadError subclasses
            raise YouTubeDownloadError(f"failed to download {url}: {exc}") from exc

        if downloaded_path.suffix != ".mp4":
            downloaded_path = downloaded_path.with_suffix(".mp4")

        if not downloaded_path.exists():
            raise YouTubeDownloadError(f"downloaded file not found for {url}")

        return DownloadedVideo(path=downloaded_path, title=info.get("title") or url)


@lru_cache
def get_youtube_provider() -> YouTubeSourceProvider:
    return YtDlpYouTubeProvider()
