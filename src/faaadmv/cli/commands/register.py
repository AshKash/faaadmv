"""Register command implementation."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from faaadmv.cli.ui import error_panel, success_panel

console = Console()


def run_register(
    vehicle_only: bool = False,
    payment_only: bool = False,
    verify_only: bool = False,
    reset_config: bool = False,
) -> None:
    """Run the register command."""
    if reset_config:
        _handle_reset()
        return

    if verify_only:
        _handle_verify()
        return

    # Interactive setup
    console.print()
    console.print(
        Panel.fit(
            "[bold]Welcome to faaadmv![/bold]\n\nLet's set up your vehicle registration.",
            border_style="blue",
        )
    )
    console.print()

    try:
        if not payment_only:
            _collect_vehicle_info()
            _collect_owner_info()

        if not vehicle_only:
            _collect_payment_info()

        _save_config()
        console.print()
        console.print(success_panel("Configuration saved securely."))
        console.print()
        console.print("[dim]Run 'faaadmv status' to check your registration.[/dim]")

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Setup cancelled.[/yellow]")
        raise typer.Exit(1)


def _handle_reset() -> None:
    """Handle config reset."""
    console.print()
    if Confirm.ask("[yellow]Delete all saved configuration?[/yellow]", default=False):
        # TODO: Implement actual reset
        console.print(success_panel("Configuration deleted."))
    else:
        console.print("[dim]Cancelled.[/dim]")


def _handle_verify() -> None:
    """Handle config verification."""
    console.print()
    # TODO: Load and display config
    console.print(
        Panel(
            "[bold]Saved Configuration[/bold]\n\n"
            "Vehicle:  8ABC123 / ***45\n"
            "Owner:    Jane Doe\n"
            "Email:    j***e@example.com\n"
            "Card:     ****4242 (exp 12/27)",
            title="Config",
            border_style="blue",
        )
    )
    console.print()
    console.print(success_panel("All fields valid."))


def _collect_vehicle_info() -> dict:
    """Collect vehicle information interactively."""
    console.print("[bold cyan]--- Vehicle Information ---[/bold cyan]")
    console.print()

    plate = Prompt.ask("  License plate number")
    vin = Prompt.ask("  Last 5 digits of VIN")

    console.print()
    return {"plate": plate, "vin_last5": vin}


def _collect_owner_info() -> dict:
    """Collect owner information interactively."""
    console.print("[bold cyan]--- Owner Information ---[/bold cyan]")
    console.print()

    name = Prompt.ask("  Full name")
    phone = Prompt.ask("  Phone number")
    email = Prompt.ask("  Email address")

    console.print()
    console.print("[bold cyan]--- Address ---[/bold cyan]")
    console.print()

    street = Prompt.ask("  Street address")
    city = Prompt.ask("  City")
    state = Prompt.ask("  State", default="CA")
    zip_code = Prompt.ask("  ZIP code")

    console.print()
    return {
        "full_name": name,
        "phone": phone,
        "email": email,
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        },
    }


def _collect_payment_info() -> dict:
    """Collect payment information interactively."""
    console.print("[bold cyan]--- Payment Information ---[/bold cyan]")
    console.print()

    card = Prompt.ask("  Card number", password=True)
    exp_month = Prompt.ask("  Expiration month (MM)")
    exp_year = Prompt.ask("  Expiration year (YY)")
    cvv = Prompt.ask("  CVV", password=True)
    billing_zip = Prompt.ask("  Billing ZIP code")

    console.print()
    return {
        "card_number": card,
        "expiry_month": int(exp_month),
        "expiry_year": int(f"20{exp_year}"),
        "cvv": cvv,
        "billing_zip": billing_zip,
    }


def _save_config() -> None:
    """Save configuration to disk."""
    # TODO: Implement actual save
    pass
