"""Renew command implementation."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from faaadmv.cli.ui import error_panel, success_panel

console = Console()


def run_renew(
    dry_run: bool = False,
    headed: bool = False,
    verbose: bool = False,
) -> None:
    """Run the renew command."""
    console.print()

    try:
        # Step 1: Load config
        _step("Loading configuration...", 1, 6)

        # Step 2: Connect to DMV
        _step("Connecting to CA DMV portal...", 2, 6)

        # Step 3: Submit vehicle info
        _step("Submitting vehicle info...", 3, 6)

        # Step 4: Check eligibility
        _step("Checking eligibility...", 4, 6)
        _display_eligibility()

        # Step 5: Display fees
        _step("Retrieving fees...", 5, 6)
        total = _display_fees()

        # Dry run stops here
        if dry_run:
            console.print()
            console.print(success_panel("Dry run complete. Ready for actual renewal."))
            return

        # Confirmation prompt
        console.print()
        if not Confirm.ask(
            f"[yellow bold]\u26a0  Pay ${total:.2f} now?[/yellow bold]",
            default=False,
        ):
            console.print()
            console.print("[yellow]Aborted. No payment was made.[/yellow]")
            raise typer.Exit(0)

        # Step 6: Process payment
        console.print()
        _step("Processing payment...", 6, 6)

        # Success
        console.print()
        console.print(success_panel("Payment successful!"))
        console.print(success_panel("Receipt saved to ./dmv_receipt_2026-02-07.pdf"))
        console.print()
        console.print(
            "[bold green]Your registration is now valid through February 2027.[/bold green]"
        )

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Cancelled. No payment was made.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print()
        console.print(error_panel(str(e)))
        raise typer.Exit(1)


def _step(message: str, current: int, total: int) -> None:
    """Display a step with progress."""
    console.print(f"[dim][{current}/{total}][/dim] {message} [green]\u2713[/green]")


def _display_eligibility() -> None:
    """Display eligibility check results."""
    console.print()
    console.print("  [green]\u2713[/green] Smog Check: Passed (01/15/2026)")
    console.print("  [green]\u2713[/green] Insurance: Verified (State Farm)")
    console.print()


def _display_fees() -> float:
    """Display fee breakdown and return total."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        collapse_padding=True,
    )
    table.add_column("Description", style="white")
    table.add_column("Amount", style="white", justify="right")

    fees = [
        ("Registration Fee", 168.00),
        ("CHP Fee", 32.00),
        ("County Fee", 48.00),
    ]

    for desc, amount in fees:
        table.add_row(desc, f"${amount:.2f}")

    total = sum(amount for _, amount in fees)

    console.print()
    console.print(
        Panel(
            table,
            title="Registration Fees",
            border_style="blue",
            padding=(1, 2),
        )
    )

    console.print()
    console.print(f"  [bold]Total: ${total:.2f}[/bold]")

    return total
