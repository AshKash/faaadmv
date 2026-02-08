"""Renew command implementation."""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from faaadmv.cli.ui import error_panel, success_panel
from faaadmv.core.browser import BrowserManager
from faaadmv.core.captcha import CaptchaSolver
from faaadmv.core.config import ConfigManager
from faaadmv.core.keychain import PaymentKeychain
from faaadmv.exceptions import (
    BrowserError,
    CaptchaDetectedError,
    CaptchaSolveFailedError,
    DMVError,
    EligibilityError,
    FaaadmvError,
    InsuranceError,
    PaymentDeclinedError,
    PaymentError,
    SmogCheckError,
    VehicleNotFoundError,
)
from faaadmv.models import (
    EligibilityResult,
    FeeBreakdown,
    RenewalResult,
    UserConfig,
    VehicleInfo,
)
from faaadmv.providers import get_provider

logger = logging.getLogger(__name__)
console = Console()


def run_renew(
    dry_run: bool = False,
    headed: bool = False,
    verbose: bool = False,
    plate: Optional[str] = None,
) -> None:
    """Run the renew command."""
    console.print()

    # Step 1: Load config
    manager = ConfigManager()
    if not manager.exists:
        console.print(error_panel(
            "No configuration found.",
            "Run 'faaadmv register' to set up your vehicle first.",
        ))
        raise typer.Exit(1)

    config = manager.load()

    # Select vehicle
    from faaadmv.cli.commands.status import _select_vehicle
    entry = _select_vehicle(config, plate)
    selected_vehicle = entry.vehicle

    # Load payment from keychain (required for non-dry-run)
    payment = PaymentKeychain.retrieve()

    if not dry_run and not payment:
        console.print()
        console.print(error_panel(
            "Payment information not found.",
            "Run 'faaadmv register --payment' to add payment info.",
        ))
        raise typer.Exit(1)

    if payment:
        config = config.with_payment(payment)

        if payment.is_expired:
            console.print()
            console.print(error_panel(
                "Payment card is expired.",
                f"Card {payment.masked_number} expired {payment.expiry_display}. "
                "Run 'faaadmv register --payment' to update.",
            ))
            raise typer.Exit(1)

    console.print()
    _step("Loading configuration...", 1, 6)

    if verbose:
        console.print(f"[dim]    Vehicle: {selected_vehicle.plate} / {selected_vehicle.masked_vin}[/dim]")
        if config.owner:
            console.print(f"[dim]    Owner: {config.owner.full_name}[/dim]")
        if payment:
            console.print(f"[dim]    Card: {payment.masked_number} ({payment.card_type})[/dim]")

    logger.info("Renew: plate=%s dry_run=%s headed=%s", selected_vehicle.plate, dry_run, headed)

    # Run async renewal flow
    try:
        asyncio.run(
            _run_renewal(
                config=config,
                vehicle=selected_vehicle,
                dry_run=dry_run,
                headed=headed,
                verbose=verbose,
            )
        )
    except CaptchaDetectedError:
        console.print()
        console.print(error_panel(
            "CAPTCHA detected.",
            "Try running with --headed flag: faaadmv renew --headed",
        ))
        raise typer.Exit(1)
    except CaptchaSolveFailedError as e:
        console.print()
        console.print(error_panel("CAPTCHA solving failed.", e.details))
        raise typer.Exit(1)
    except SmogCheckError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except InsuranceError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except EligibilityError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except PaymentDeclinedError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
        raise typer.Exit(1)
    except PaymentError as e:
        console.print()
        console.print(error_panel(e.message, e.details))
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
        console.print("[yellow]Cancelled. No payment was made.[/yellow]")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Unexpected error in renew")
        console.print()
        console.print(error_panel("Unexpected error.", str(e)))
        raise typer.Exit(1)


async def _run_renewal(
    config: UserConfig,
    vehicle: VehicleInfo,
    dry_run: bool,
    headed: bool,
    verbose: bool,
) -> None:
    """Execute the full renewal flow."""
    provider_cls = get_provider(config.state)
    captcha_solver = CaptchaSolver()

    headless = not headed

    async with BrowserManager(headless=headless) as bm:
        provider = provider_cls(bm.context)
        await provider.initialize()

        try:
            # Step 2: Connect to DMV
            _step("Connecting to CA DMV portal...", 2, 6)

            # Step 3: Validate eligibility (also submits vehicle info)
            _step("Submitting vehicle info...", 3, 6)
            eligibility = await provider.validate_eligibility(
                vehicle.plate,
                vehicle.vin_last5,
            )

            # Handle CAPTCHA if detected during eligibility
            if await provider.has_captcha():
                solved = await captcha_solver.solve(provider.page, headed=headed)
                if not solved:
                    raise CaptchaDetectedError()

            _step("Checking eligibility...", 4, 6)
            _display_eligibility(eligibility)

            # Step 5: Get fees
            _step("Retrieving fees...", 5, 6)
            fees = await provider.get_fee_breakdown()
            _display_fees(fees)

            # Dry run stops here
            if dry_run:
                console.print()
                console.print(success_panel(
                    "Dry run complete. Ready for actual renewal."
                ))
                console.print("[dim]Run 'faaadmv renew' (without --dry-run) to proceed.[/dim]")
                return

            # Payment confirmation
            console.print()
            card_info = ""
            if config.payment:
                card_info = f"  Card: {config.payment.masked_number} (exp {config.payment.expiry_display})\n\n"

            if not Confirm.ask(
                f"{card_info}[yellow bold]\u26a0  Pay {fees.total_display} now?[/yellow bold]",
                default=False,
            ):
                console.print()
                console.print("[yellow]Aborted. No payment was made.[/yellow]")
                raise typer.Exit(0)

            # Step 6: Submit payment
            console.print()
            with console.status("[bold blue]Processing payment...[/bold blue]"):
                result = await provider.submit_renewal(config)

            _step("Payment processed!", 6, 6)
            _display_result(result)

        finally:
                await provider.cleanup()


def _step(message: str, current: int, total: int) -> None:
    """Display a step with progress."""
    console.print(f"  [dim][{current}/{total}][/dim] {message} [green]\u2713[/green]")


def _display_eligibility(eligibility: EligibilityResult) -> None:
    """Display eligibility check results."""
    console.print()

    if eligibility.smog.passed:
        smog_detail = ""
        if eligibility.smog.check_date:
            smog_detail = f" ({eligibility.smog.check_date.strftime('%m/%d/%Y')})"
        console.print(f"  [green]\u2713[/green] Smog Check: Passed{smog_detail}")
    else:
        console.print("  [red]\u2717[/red] Smog Check: [red]Failed[/red]")

    if eligibility.insurance.verified:
        ins_detail = ""
        if eligibility.insurance.provider:
            ins_detail = f" ({eligibility.insurance.provider})"
        console.print(f"  [green]\u2713[/green] Insurance: Verified{ins_detail}")
    else:
        console.print("  [red]\u2717[/red] Insurance: [red]Not Verified[/red]")

    console.print()


def _display_fees(fees: FeeBreakdown) -> None:
    """Display fee breakdown table."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        collapse_padding=True,
    )
    table.add_column("Description", style="white", min_width=25)
    table.add_column("Amount", style="white", justify="right")

    for item in fees.items:
        table.add_row(item.description, item.amount_display)

    table.add_row("\u2500" * 25, "\u2500" * 10)
    table.add_row("[bold]Total[/bold]", f"[bold]{fees.total_display}[/bold]")

    console.print()
    console.print(
        Panel(
            table,
            title="Registration Fees",
            border_style="blue",
            padding=(1, 2),
        )
    )


def _display_result(result: RenewalResult) -> None:
    """Display renewal result."""
    console.print()

    if result.success:
        console.print(success_panel("Payment successful!"))

        if result.confirmation_number:
            console.print(f"  Confirmation: [bold]{result.confirmation_number}[/bold]")

        if result.receipt_path:
            console.print(success_panel(f"Receipt saved to {result.receipt_path}"))

        if result.new_expiration_date:
            exp_str = result.new_expiration_date.strftime("%B %Y")
            console.print()
            console.print(
                f"  [bold green]Your registration is now valid through {exp_str}.[/bold green]"
            )
    else:
        console.print(error_panel(
            "Renewal may not have completed.",
            result.error_message or "Check your email for confirmation.",
        ))
