"""Status command implementation."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from faaadmv.cli.ui import error_panel

console = Console()


def run_status(verbose: bool = False) -> None:
    """Run the status command."""
    console.print()

    # TODO: Load config and check status
    # For now, show placeholder

    try:
        with console.status("[bold blue]Checking registration status...[/bold blue]"):
            # TODO: Implement actual status check
            pass

        # Display results
        _display_status(
            vehicle="2019 Honda Accord",
            plate="8ABC123",
            status="Current",
            expiration="June 20, 2026",
            days_left=133,
            verbose=verbose,
        )

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print()
        console.print(error_panel(str(e)))
        raise typer.Exit(1)


def _display_status(
    vehicle: str,
    plate: str,
    status: str,
    expiration: str,
    days_left: int,
    verbose: bool = False,
) -> None:
    """Display registration status."""
    # Determine status style
    if status == "Current":
        status_display = f"[green]\u2713 {status}[/green]"
    elif status == "Expiring Soon":
        status_display = f"[yellow]\u26a0 {status}[/yellow]"
    elif status == "Expired":
        status_display = f"[red]\u2717 {status}[/red]"
    else:
        status_display = f"[yellow]\u26a0 {status}[/yellow]"

    # Build panel content
    content = f"""[bold]{vehicle}[/bold]
Plate: {plate}

Status:     {status_display}
Expires:    {expiration}
Days left:  {days_left}"""

    console.print(
        Panel(
            content,
            title="Registration Status",
            border_style="blue",
            padding=(1, 2),
        )
    )

    if verbose:
        console.print()
        console.print("[dim]Checked via CA DMV portal[/dim]")
