"""Status command implementation."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from faaadmv.cli.ui import error_panel
from faaadmv.core.browser import BrowserManager
from faaadmv.core.captcha import CaptchaSolver
from faaadmv.core.config import ConfigManager
from faaadmv.exceptions import (
    BrowserError,
    CaptchaDetectedError,
    ConfigDecryptionError,
    ConfigNotFoundError,
    DMVError,
    FaaadmvError,
    VehicleNotFoundError,
)
from faaadmv.models import RegistrationStatus, StatusType
from faaadmv.providers import get_provider

console = Console()


def run_status(verbose: bool = False) -> None:
    """Run the status command."""
    console.print()

    # Load config
    manager = ConfigManager()
    if not manager.exists:
        console.print(error_panel(
            "No configuration found.",
            "Run 'faaadmv register' to set up your vehicle first.",
        ))
        raise typer.Exit(1)

    passphrase = Prompt.ask("  Enter your passphrase", password=True)

    try:
        config = manager.load(passphrase)
    except ConfigDecryptionError:
        console.print()
        console.print(error_panel("Wrong passphrase.", "Check your passphrase and try again."))
        raise typer.Exit(1)

    if verbose:
        console.print(f"[dim]  Vehicle: {config.vehicle.plate}[/dim]")
        console.print(f"[dim]  Provider: {config.state}[/dim]")

    # Run async status check
    try:
        result = asyncio.run(
            _check_status(
                plate=config.vehicle.plate,
                vin_last5=config.vehicle.vin_last5,
                state=config.state,
                verbose=verbose,
            )
        )
        _display_status(result, verbose)
    except CaptchaDetectedError:
        console.print()
        console.print(error_panel(
            "CAPTCHA detected.",
            "Try running with --headed flag: faaadmv status --headed",
        ))
        raise typer.Exit(1)
    except VehicleNotFoundError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except BrowserError as e:
        console.print()
        console.print(error_panel(
            "Browser error.",
            f"{e.message}. Make sure Playwright is installed: playwright install chromium",
        ))
        raise typer.Exit(1)
    except DMVError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except FaaadmvError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print()
        console.print(error_panel("Unexpected error.", str(e)))
        raise typer.Exit(1)


async def _check_status(
    plate: str,
    vin_last5: str,
    state: str,
    verbose: bool = False,
) -> RegistrationStatus:
    """Run the async status check against DMV portal.

    Args:
        plate: License plate number
        vin_last5: Last 5 of VIN
        state: State code for provider selection
        verbose: Show detailed output

    Returns:
        RegistrationStatus from provider
    """
    provider_cls = get_provider(state)

    async with BrowserManager(headless=True) as bm:
        provider = provider_cls(bm.context)
        await provider.initialize()

        try:
            with console.status("[bold blue]Checking registration status...[/bold blue]"):
                result = await provider.get_registration_status(plate, vin_last5)
            return result
        finally:
            await provider.cleanup()


def _display_status(result: RegistrationStatus, verbose: bool = False) -> None:
    """Display registration status with Rich formatting."""
    # Status styling
    status_styles = {
        StatusType.CURRENT: ("green", "\u2713"),
        StatusType.EXPIRING_SOON: ("yellow", "\u26a0"),
        StatusType.PENDING: ("yellow", "\u26a0"),
        StatusType.EXPIRED: ("red", "\u2717"),
        StatusType.HOLD: ("yellow", "\u26a0"),
    }

    color, icon = status_styles.get(result.status, ("white", "?"))

    # Build panel content
    vehicle_line = f"[bold]{result.vehicle_description or 'Vehicle'}[/bold]"
    plate_line = f"Plate: {result.plate}"

    status_line = f"Status:     [{color}]{icon} {result.status_display}[/{color}]"
    expiry_line = f"Expires:    {result.expiration_date.strftime('%B %d, %Y')}"

    # Days display
    if result.days_until_expiry > 0:
        days_line = f"Days left:  {result.days_until_expiry}"
    elif result.days_until_expiry == 0:
        days_line = "Days left:  [red]TODAY[/red]"
    else:
        days_line = f"Overdue:    [red]{abs(result.days_until_expiry)} days[/red]"

    content = f"{vehicle_line}\n{plate_line}\n\n{status_line}\n{expiry_line}\n{days_line}"

    # Add hold reason if present
    if result.hold_reason:
        content += f"\n\nReason:     [yellow]{result.hold_reason}[/yellow]"

    console.print()
    console.print(
        Panel(
            content,
            title="Registration Status",
            border_style=color,
            padding=(1, 2),
        )
    )

    if verbose:
        console.print()
        console.print(f"[dim]  Checked via {result.plate} / ***{result.vin_last5[-2:]}[/dim]")
        console.print(f"[dim]  Renewable: {'Yes' if result.is_renewable else 'No'}[/dim]")
