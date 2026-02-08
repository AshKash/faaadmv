"""Status command implementation."""

import asyncio
import logging
from typing import Optional

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
    ConfigNotFoundError,
    DMVError,
    FaaadmvError,
    VehicleNotFoundError,
)
from faaadmv.models import RegistrationStatus, StatusType
from faaadmv.models.vehicle import VehicleEntry
from faaadmv.providers import get_provider

logger = logging.getLogger(__name__)
console = Console()


def _select_vehicle(config, plate: Optional[str] = None) -> VehicleEntry:
    """Select a vehicle from config, prompting if needed."""
    if plate:
        entry = config.get_vehicle(plate)
        if not entry:
            console.print(error_panel(
                f"Vehicle '{plate}' not found.",
                f"Registered plates: {', '.join(v.plate for v in config.vehicles)}",
            ))
            raise typer.Exit(1)
        return entry

    # Single vehicle → auto-select
    if len(config.vehicles) == 1:
        return config.vehicles[0]

    # Multiple vehicles → prompt
    console.print()
    console.print("[bold]Select a vehicle:[/bold]")
    for i, entry in enumerate(config.vehicles, 1):
        default_marker = " [green](default)[/green]" if entry.is_default else ""
        name = entry.nickname or entry.vehicle.masked_vin
        console.print(f"  {i}. {entry.vehicle.plate} — {name}{default_marker}")

    console.print()
    choice = Prompt.ask(
        "  Vehicle number",
        default="1" if config.default_vehicle else None,
    )

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(config.vehicles):
            return config.vehicles[idx]
    except ValueError:
        pass

    console.print(error_panel("Invalid selection."))
    raise typer.Exit(1)


def run_status(
    headed: bool = False,
    verbose: bool = False,
    plate: Optional[str] = None,
    all_vehicles: bool = False,
) -> None:
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

    config = manager.load()

    if all_vehicles:
        for entry in config.vehicles:
            _run_single_status(entry, config.state, headed, verbose)
        return

    entry = _select_vehicle(config, plate)
    _run_single_status(entry, config.state, headed, verbose)


def _run_single_status(
    entry: VehicleEntry,
    state: str,
    headed: bool,
    verbose: bool,
) -> None:
    """Check status for a single vehicle."""
    console.print(f"  Checking [bold]{entry.vehicle.plate}[/bold]...")
    logger.info("Status check: plate=%s vin_last5=%s state=%s", entry.vehicle.plate, entry.vehicle.vin_last5, state)

    if verbose:
        console.print(f"[dim]  Vehicle: {entry.vehicle.plate} / {entry.vehicle.masked_vin}[/dim]")
        console.print(f"[dim]  Provider: {state}[/dim]")

    try:
        result = asyncio.run(
            _check_status(
                plate=entry.vehicle.plate,
                vin_last5=entry.vehicle.vin_last5,
                state=state,
                headed=headed,
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
        logger.exception("Unexpected error in status check")
        console.print()
        console.print(error_panel("Unexpected error.", str(e)))
        raise typer.Exit(1)


async def _check_status(
    plate: str,
    vin_last5: str,
    state: str,
    headed: bool = False,
    verbose: bool = False,
) -> RegistrationStatus:
    """Run the async status check against DMV portal."""
    provider_cls = get_provider(state)
    logger.debug("Using provider: %s", getattr(provider_cls, "__name__", str(provider_cls)))

    async with BrowserManager(headless=not headed) as bm:
        provider = provider_cls(bm.context)
        await provider.initialize()

        try:
            console.print("  [dim]Connecting to DMV portal...[/dim]")
            result = await provider.get_registration_status(plate, vin_last5)
            console.print("  [dim]Status retrieved.[/dim]")
            return result
        finally:
            await provider.cleanup()


def _display_status(result: RegistrationStatus, verbose: bool = False) -> None:
    """Display registration status with Rich formatting."""
    status_styles = {
        StatusType.CURRENT: ("green", "\u2713"),
        StatusType.EXPIRING_SOON: ("yellow", "\u26a0"),
        StatusType.PENDING: ("yellow", "\u26a0"),
        StatusType.EXPIRED: ("red", "\u2717"),
        StatusType.HOLD: ("yellow", "\u26a0"),
    }

    color, icon = status_styles.get(result.status, ("white", "?"))

    vehicle_line = f"[bold]{result.vehicle_description or 'Vehicle'}[/bold]"
    plate_line = f"Plate: {result.plate}"
    status_line = f"Status:     [{color}]{icon} {result.status_display}[/{color}]"

    content = f"{vehicle_line}\n{plate_line}\n\n{status_line}"

    if result.expiration_date:
        content += f"\nExpires:    {result.expiration_date.strftime('%B %d, %Y')}"

        if result.days_until_expiry is not None:
            if result.days_until_expiry > 0:
                content += f"\nDays left:  {result.days_until_expiry}"
            elif result.days_until_expiry == 0:
                content += "\nDays left:  [red]TODAY[/red]"
            else:
                content += f"\nOverdue:    [red]{abs(result.days_until_expiry)} days[/red]"

    if result.last_updated:
        content += f"\nAs of:      {result.last_updated.strftime('%B %d, %Y')}"

    if result.status_message:
        content += f"\n\n[dim]{result.status_message}[/dim]"

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
