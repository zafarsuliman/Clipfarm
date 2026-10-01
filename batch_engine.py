from __future__ import annotations

import json
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

from clipfarm.core.models import RunManifest
from clipfarm.pipeline import run_pipeline


@dataclass
class BatchItemResult:
    source: str
    ok: bool
    run_dir: str | None = None
    error: str | None = None
    attempts: int = 0


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def run_with_retries(
    source: str,
    output_root: Path,
    attempts: int = 2,
    **pipeline_kwargs,
) -> BatchItemResult:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            manifest = run_pipeline(source, output_root=output_root, **pipeline_kwargs)
            return BatchItemResult(
                source=source,
                ok=True,
                run_dir=manifest.run_dir,
                attempts=attempt,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
    return BatchItemResult(
        source=source,
        ok=False,
        error=last_error,
        attempts=attempts,
    )


def run_batch(
    sources: list[str],
    output_root: Path,
    workers: int = 2,
    attempts: int = 2,
    **pipeline_kwargs,
) -> list[BatchItemResult]:
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[BatchItemResult] = []

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(
                run_with_retries,
                source,
                output_root,
                attempts,
                **pipeline_kwargs,
            ): source
            for source in sources
        }
        for future in as_completed(futures):
            results.append(future.result())

    report = {
        "total": len(results),
        "succeeded": sum(r.ok for r in results),
        "failed": sum(not r.ok for r in results),
        "items": [asdict(r) for r in results],
    }
    (output_root / "batch_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return results
