"""`sybl indicator demo` — preview the capture overlay without the daemon."""

from __future__ import annotations

import math
import time

import typer

from sybl.config import ConfigManager
from sybl.indicator import create_indicator

indicator_app = typer.Typer(
    help="Capture overlay diagnostics.",
    no_args_is_help=True,
)


@indicator_app.command("demo")
def indicator_demo(
    duration: float = typer.Option(
        0.0,
        "--duration",
        "-d",
        help="Seconds to run (0 = until Ctrl+C).",
    ),
    force_pill: bool = typer.Option(
        False,
        "--pill",
        help="Force strategy=pill regardless of config.",
    ),
    force_orb: bool = typer.Option(
        False,
        "--orb",
        help="Deprecated alias for --pill.",
        hidden=True,
    ),
) -> None:
    """Show the capture overlay and animate mic levels (no daemon required)."""
    config = ConfigManager().load()
    use_pill = force_pill or force_orb
    if use_pill:
        config = config.model_copy(
            update={
                "indicator": config.indicator.model_copy(
                    update={"strategy": "pill", "enabled": True},
                ),
            },
        )

    ind = create_indicator(config)
    impl = type(ind).__name__
    strategy = config.indicator.strategy
    typer.echo(f"Indicator: {impl} (strategy={strategy})")

    typer.echo("Pill visible — press Ctrl+C to exit.")
    ind.show()
    if getattr(ind, "degraded", False):
        typer.secho(
            "Overlay failed to start — install PySide6: uv sync --extra pill",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    try:
        start = time.monotonic()
        processing_at = start + max(duration * 0.6, 1.0) if duration > 0 else None
        while True:
            t = time.monotonic()
            level = 0.15 + 0.35 * (1.0 + math.sin(t * 4.0)) / 2.0
            if processing_at is not None and t >= processing_at:
                ind.set_phase("processing")
            else:
                ind.update_level(level)
            time.sleep(1.0 / 30.0)
            if duration > 0 and (t - start) >= duration:
                break
    except KeyboardInterrupt:
        typer.echo("")
    finally:
        ind.hide()
        ind.shutdown()
    typer.echo("Done.")


def register(app: typer.Typer) -> None:
    app.add_typer(indicator_app, name="indicator")
