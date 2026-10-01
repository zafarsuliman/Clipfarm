from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from clipfarm.core.models import SourceMetadata

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def ingest_source(source: str, run_dir: Path) -> SourceMetadata:
    run_dir.mkdir(parents=True, exist_ok=True)
    media_dir = run_dir / "media"
    media_dir.mkdir(exist_ok=True)

    if _is_url(source):
        out_tmpl = media_dir / "source.%(ext)s"
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "bestvideo*+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "--no-playlist",
            "-o",
            str(out_tmpl),
            source,
        ]
        subprocess.run(cmd, check=True)
        candidates = [p for p in sorted(media_dir.glob("source.*")) if p.suffix.lower() in VIDEO_EXTENSIONS]
        if not candidates:
            raise RuntimeError("yt-dlp completed but no supported video file was produced")
        local = candidates[0]
    else:
        src = Path(source).expanduser().resolve()
        if not src.exists() or src.suffix.lower() not in VIDEO_EXTENSIONS:
            raise FileNotFoundError(f"Unsupported or missing local video: {src}")
        local = media_dir / f"source{src.suffix.lower()}"
        if src != local:
            shutil.copy2(src, local)

    probe = _probe(local)
    return SourceMetadata(source=source, local_path=str(local.resolve()), **probe)


def _probe(path: Path) -> dict[str, float | int | None]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate:format=duration",
        "-of",
        "json",
        str(path),
    ]
    raw = json.loads(_run(cmd).stdout)
    stream = (raw.get("streams") or [{}])[0]
    fmt = raw.get("format") or {}
    fps = None
    rate = stream.get("r_frame_rate")
    if rate and "/" in rate:
        a, b = rate.split("/", 1)
        try:
            fps = float(a) / float(b)
        except (TypeError, ValueError, ZeroDivisionError):
            fps = None
    duration = None
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        pass
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "duration": duration,
        "fps": fps,
    }
