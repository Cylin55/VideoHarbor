from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class DownloadCancelled(Exception):
    """Raised when a user cancels an active download."""


class MissingDependency(RuntimeError):
    """Raised when a required external program is unavailable."""


@dataclass(frozen=True)
class MediaInfo:
    title: str
    uploader: str
    duration: int | None
    thumbnail: str | None
    resolutions: tuple[int, ...]


def validate_url(url: str) -> str:
    value = url.strip()
    if not value.lower().startswith(("https://", "http://")):
        raise ValueError("請貼上以 http:// 或 https:// 開頭的影片網址。")
    return value


def _ydl_class():
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise MissingDependency(
            "尚未安裝 yt-dlp。請先執行「啟動程式.bat」，或執行 pip install -r requirements.txt。"
        ) from exc
    return YoutubeDL


def inspect_media(url: str) -> MediaInfo:
    url = validate_url(url)
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    with _ydl_class()(options) as ydl:
        info = ydl.extract_info(url, download=False)

    heights = {
        int(item["height"])
        for item in info.get("formats", [])
        if item.get("height") and item.get("vcodec") != "none"
    }
    return MediaInfo(
        title=info.get("title") or "未命名影片",
        uploader=info.get("uploader") or info.get("channel") or "未知發布者",
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        resolutions=tuple(sorted(heights, reverse=True)),
    )


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "--:--"
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def build_format_selector(container: str, height: int | None) -> str:
    if container == "MP3":
        return "bestaudio/best"
    extension = container.lower()
    limit = f"[height<={height}]" if height else ""
    # Prefer native container streams, then fall back to any compatible source.
    return (
        f"bestvideo{limit}[ext={extension}]+bestaudio[ext={extension}]/"
        f"bestvideo{limit}+bestaudio/best{limit}"
    )


def build_single_file_selector(container: str, height: int | None) -> str:
    """Select a stream that needs no FFmpeg merge."""
    extension = container.lower()
    limit = f"[height<={height}]" if height else ""
    return f"best{limit}[ext={extension}]/best{limit}"


def download_media(
    url: str,
    output_dir: Path,
    container: str,
    height: int | None,
    progress_callback: Callable[[dict[str, Any]], None],
    cancel_event: threading.Event,
) -> Path:
    url = validate_url(url)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    container = container.upper()
    if container not in {"MP4", "WEBM", "MP3"}:
        raise ValueError("不支援的輸出格式。")
    if container == "MP3" and not shutil.which("ffmpeg"):
        raise MissingDependency("輸出 MP3 需要 FFmpeg。請安裝 FFmpeg 並重新啟動程式。")

    completed_path: Path | None = None

    def hook(status: dict[str, Any]) -> None:
        nonlocal completed_path
        if cancel_event.is_set():
            raise DownloadCancelled("下載已取消。")
        if status.get("filename"):
            completed_path = Path(status["filename"])
        progress_callback(status)

    ffmpeg_available = bool(shutil.which("ffmpeg"))
    selector = build_format_selector(container, height)
    if container != "MP3" and not ffmpeg_available:
        selector = build_single_file_selector(container, height)

    options: dict[str, Any] = {
        "format": selector,
        "outtmpl": str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "windowsfilenames": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
    }
    if container == "MP3":
        options["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}
        ]
    elif ffmpeg_available:
        options["merge_output_format"] = container.lower()

    with _ydl_class()(options) as ydl:
        result = ydl.extract_info(url, download=True)
        requested = result.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            completed_path = Path(requested[0]["filepath"])
        elif result.get("_filename"):
            completed_path = Path(result["_filename"])

    if completed_path is None:
        completed_path = output_dir
    if container == "MP3" and completed_path.suffix.lower() != ".mp3":
        completed_path = completed_path.with_suffix(".mp3")
    return completed_path
