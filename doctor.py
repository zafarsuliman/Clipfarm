from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def run_doctor() -> list[Check]:
    checks = []
    for binary in ("ffmpeg", "ffprobe"):
        path = shutil.which(binary)
        checks.append(Check(binary, bool(path), path or "not found on PATH"))

    for module in ("yt_dlp", "faster_whisper", "cv2", "pydantic", "typer", "rich"):
        ok = importlib.util.find_spec(module) is not None
        checks.append(Check(module, ok, "installed" if ok else "missing"))
    return checks
