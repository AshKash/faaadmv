"""Main CLI application."""

from typing import Optional

import typer
from rich.console import Console

from faaadmv import __version__

app = typer.Typer(
    name="faaadmv",
    help="Renew your vehicle registration from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
    ),
) -> None:
    """faaadmv - Agentic DMV registration renewal CLI."""
    if version:
        console.print(f"faaadmv v{__version__}")
        raise typer.Exit()


@app.command()
def register(
    vehicle: bool = typer.Option(False, "--vehicle", help="Update vehicle info only"),
    payment: bool = typer.Option(False, "--payment", help="Update payment info only"),
    verify: bool = typer.Option(False, "--verify", help="Verify saved configuration"),
    reset: bool = typer.Option(False, "--reset", help="Reset all saved data"),
) -> None:
    """Set up or update your vehicle and payment information."""
    from faaadmv.cli.commands.register import run_register

    run_register(
        vehicle_only=vehicle,
        payment_only=payment,
        verify_only=verify,
        reset_config=reset,
    )


@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Check your current registration status."""
    from faaadmv.cli.commands.status import run_status

    run_status(verbose=verbose)


@app.command()
def renew(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Run without making payment"
    ),
    headed: bool = typer.Option(
        False, "--headed", help="Show browser window (for CAPTCHA)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Renew your vehicle registration."""
    from faaadmv.cli.commands.renew import run_renew

    run_renew(dry_run=dry_run, headed=headed, verbose=verbose)


if __name__ == "__main__":
    app()
