from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from clipfarm.core.io import read_json
from clipfarm.pipeline import run_pipeline

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def run(
    source: str = typer.Argument(..., help="Authorized video URL or local file path"),
    output_dir: Path = typer.Option(Path("runs"), "--output-dir"),
    model: str = typer.Option("small", "--model"),
    device: str = typer.Option("cpu", "--device"),
    compute_type: str = typer.Option("int8", "--compute-type"),
    language: str | None = typer.Option(None, "--language"),
    min_duration: float = typer.Option(18.0, "--min-duration"),
    max_duration: float = typer.Option(45.0, "--max-duration"),
    clips: int = typer.Option(8, "--clips", min=1, max=30),
) -> None:
    manifest = run_pipeline(
        source=source,
        output_root=output_dir,
        model=model,
        device=device,
        compute_type=compute_type,
        language=language,
        min_duration=min_duration,
        max_duration=max_duration,
        clips=clips,
    )
    candidates = read_json(Path(manifest.candidates_path))
    table = Table(title="Clipfarm candidates")
    table.add_column("#", justify="right")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Score")
    table.add_column("Hook")
    table.add_column("Reasons")
    for idx, item in enumerate(candidates, 1):
        table.add_row(
            str(idx),
            f"{item['start']:.2f}",
            f"{item['end']:.2f}",
            f"{item['overall']:.2f}/10",
            item["hook"],
            ", ".join(item.get("reasons") or []),
        )
    console.print(table)
    console.print(f"Run manifest: [bold]{manifest.path}[/bold]")


if __name__ == "__main__":
    app()
