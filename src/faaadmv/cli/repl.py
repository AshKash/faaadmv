"""Interactive REPL for faaadmv."""

import asyncio
import logging
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from faaadmv import __version__
from faaadmv.cli.ui import error_panel, success_panel
from faaadmv.core.browser import BrowserManager
from faaadmv.core.captcha import CaptchaSolver
from faaadmv.core.config import ConfigManager
from faaadmv.core.keychain import PaymentKeychain
from faaadmv.exceptions import (
    BrowserError,
    CaptchaDetectedError,
    DMVError,
    FaaadmvError,
    VehicleNotFoundError,
)
from faaadmv.models import RegistrationStatus, StatusType, UserConfig, VehicleInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleEntry
from faaadmv.providers import get_provider

logger = logging.getLogger(__name__)
console = Console()


class FaaadmvREPL:
    """Interactive REPL for managing vehicle registrations."""

    def __init__(self) -> None:
        self.manager = ConfigManager()
        self.config: Optional[UserConfig] = None
        self.payment: Optional[PaymentInfo] = None

    def run(self) -> None:
        """Main entry point."""
        self._show_banner()

        try:
            self._load_session()
            self._loop()
        except KeyboardInterrupt:
            console.print()
            console.print("[dim]Goodbye![/dim]")

    # --- Session management ---

    def _load_session(self) -> None:
        """Load existing config if available."""
        if not self.manager.exists:
            return

        try:
            self.config = self.manager.load()
            self.payment = PaymentKeychain.retrieve()
            logger.info("Session loaded: %d vehicles", len(self.config.vehicles))
        except Exception as e:
            logger.exception("Failed to load config")
            console.print()
            console.print(error_panel("Failed to load configuration.", str(e)))

    def _save(self) -> None:
        """Save current config to disk."""
        if self.config is None:
            return

        self.manager.save(self.config)
        logger.debug("Config saved")

    # --- Main loop ---

    def _loop(self) -> None:
        """Main menu loop."""
        while True:
            self._show_dashboard()
            actions = self._build_actions()
            self._show_menu(actions)

            choice = Prompt.ask("  [bold]>[/bold]").strip().lower()

            if choice == "q":
                console.print()
                console.print("[dim]Goodbye![/dim]")
                break

            action = actions.get(choice)
            if action:
                action["handler"]()
            else:
                console.print("  [red]Invalid choice.[/red]")

    # --- Dashboard ---

    def _show_banner(self) -> None:
        """Show app banner."""
        console.print()
        console.print(f"[bold blue]faaadmv[/bold blue] [dim]v{__version__}[/dim]")

    def _show_dashboard(self) -> None:
        """Show current state."""
        console.print()

        if not self.config or not self.config.vehicles:
            console.print("  [dim]No vehicles registered.[/dim]")
            return

        # Vehicles
        for entry in self.config.vehicles:
            default = " [green]\u2605[/green]" if entry.is_default else "  "
            name = f" \u2014 {entry.nickname}" if entry.nickname else ""
            console.print(
                f"  {default} [bold]{entry.vehicle.plate}[/bold]{name}"
                f" [dim](VIN …{entry.vehicle.vin_last5})[/dim]"
            )

        # Payment
        if self.payment:
            console.print(
                f"\n  [dim]Payment:[/dim] {self.payment.card_type} "
                f"{self.payment.masked_number} "
                f"[dim](exp {self.payment.expiry_display})[/dim]"
            )

    # --- Menu ---

    def _build_actions(self) -> dict:
        """Build contextual menu actions."""
        actions = {}
        has_vehicles = self.config and len(self.config.vehicles) > 0

        if has_vehicles:
            actions["s"] = {
                "label": "Check registration status",
                "handler": self._action_status,
            }
            actions["r"] = {
                "label": "Renew registration",
                "handler": self._action_renew,
            }

        actions["a"] = {
            "label": "Add a vehicle",
            "handler": self._action_add_vehicle,
        }

        if has_vehicles and len(self.config.vehicles) > 1:
            actions["d"] = {
                "label": "Set default vehicle",
                "handler": self._action_set_default,
            }

        if has_vehicles and len(self.config.vehicles) > 1:
            actions["x"] = {
                "label": "Remove a vehicle",
                "handler": self._action_remove_vehicle,
            }

        if has_vehicles:
            actions["p"] = {
                "label": "Update payment info" if self.payment else "Add payment info",
                "handler": self._action_payment,
            }

        actions["q"] = {"label": "Quit", "handler": lambda: None}

        return actions

    def _show_menu(self, actions: dict) -> None:
        """Display the menu."""
        console.print()
        for key, action in actions.items():
            console.print(f"  [bold cyan]\\[{key}][/bold cyan] {action['label']}")
        console.print()

    # --- Vehicle selection ---

    def _pick_vehicle(self, prompt_text: str = "Which vehicle?") -> Optional[VehicleEntry]:
        """Pick a vehicle. Auto-selects if only one."""
        if not self.config or not self.config.vehicles:
            return None

        if len(self.config.vehicles) == 1:
            return self.config.vehicles[0]

        console.print()
        console.print(f"  [bold]{prompt_text}[/bold]")
        for i, entry in enumerate(self.config.vehicles, 1):
            default = " [green]\u2605[/green]" if entry.is_default else ""
            name = f" \u2014 {entry.nickname}" if entry.nickname else ""
            console.print(f"    {i}. {entry.vehicle.plate}{name}{default}")

        console.print()
        choice = Prompt.ask("  Vehicle #", default="1")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.config.vehicles):
                return self.config.vehicles[idx]
        except ValueError:
            pass

        console.print("  [red]Invalid selection.[/red]")
        return None

    # --- Actions ---

    def _action_add_vehicle(self) -> None:
        """Add a new vehicle."""
        console.print()
        console.print("  [bold cyan]Add Vehicle[/bold cyan]")
        console.print()

        while True:
            plate = Prompt.ask("  License plate")
            vin = Prompt.ask("  Last 5 of VIN")

            try:
                vehicle = VehicleInfo(plate=plate, vin_last5=vin)
                break
            except ValidationError as e:
                for error in e.errors():
                    field = error["loc"][-1]
                    msg = error["msg"]
                    console.print(f"  [red]{field}: {msg}[/red]")
                console.print("  [dim]Try again.[/dim]")
                console.print()

        # Check duplicate
        if self.config and self.config.get_vehicle(vehicle.plate):
            console.print()
            console.print(f"  [yellow]{vehicle.plate} is already registered.[/yellow]")
            return

        nickname = Prompt.ask("  Nickname (optional, press Enter to skip)", default="")
        nickname = nickname.strip() or None

        if self.config is None:
            # First vehicle — create config
            entry = VehicleEntry(vehicle=vehicle, nickname=nickname, is_default=True)
            self.config = UserConfig(vehicles=[entry])
        else:
            make_default = len(self.config.vehicles) == 0 or Confirm.ask(
                "  Set as default?", default=False
            )
            self.config = self.config.add_vehicle(
                vehicle, nickname=nickname, is_default=make_default
            )

        self._save()
        console.print()
        console.print(success_panel(f"Vehicle {vehicle.plate} added."))

    def _action_remove_vehicle(self) -> None:
        """Remove a vehicle."""
        entry = self._pick_vehicle("Remove which vehicle?")
        if not entry:
            return

        if len(self.config.vehicles) == 1:
            console.print()
            console.print(error_panel(
                "Cannot remove the last vehicle.",
                "Use the register --reset command to delete all data.",
            ))
            return

        console.print()
        if not Confirm.ask(
            f"  Remove [bold]{entry.vehicle.plate}[/bold]"
            f" ({entry.display_name})?",
            default=False,
        ):
            console.print("  [dim]Cancelled.[/dim]")
            return

        self.config = self.config.remove_vehicle(entry.vehicle.plate)
        self._save()
        console.print()
        console.print(success_panel(f"Vehicle {entry.vehicle.plate} removed."))

    def _action_set_default(self) -> None:
        """Set default vehicle."""
        entry = self._pick_vehicle("Set which vehicle as default?")
        if not entry:
            return

        if entry.is_default:
            console.print()
            console.print(f"  [dim]{entry.vehicle.plate} is already the default.[/dim]")
            return

        self.config = self.config.set_default(entry.vehicle.plate)
        self._save()
        console.print()
        console.print(success_panel(f"{entry.vehicle.plate} is now the default."))

    def _action_payment(self) -> None:
        """Add or update payment info."""
        payment = self._collect_payment()
        if payment:
            PaymentKeychain.store(payment)
            self.payment = payment
            console.print()
            console.print(success_panel(
                f"Card {payment.masked_number} ({payment.card_type}) saved."
            ))

    def _action_status(self) -> None:
        """Check registration status for a vehicle."""
        entry = self._pick_vehicle()
        if not entry:
            return

        console.print()
        console.print(f"  Checking status for [bold]{entry.vehicle.plate}[/bold]...")
        logger.info("REPL status check: plate=%s vin=%s", entry.vehicle.plate, entry.vehicle.vin_last5)

        try:
            result = asyncio.run(
                self._check_status(entry.vehicle.plate, entry.vehicle.vin_last5)
            )
            self._display_status(result)
        except CaptchaDetectedError:
            console.print(error_panel(
                "CAPTCHA detected.",
                "Try: faaadmv status --headed",
            ))
        except VehicleNotFoundError as e:
            console.print(error_panel(e.message, e.details))
        except BrowserError as e:
            console.print(error_panel(
                "Browser error.",
                f"{e.message}. Run: playwright install chromium",
            ))
        except (DMVError, FaaadmvError) as e:
            console.print(error_panel(e.message, e.details))
        except Exception as e:
            logger.exception("Unexpected error in REPL status check")
            console.print(error_panel("Unexpected error.", str(e)))

    def _action_renew(self) -> None:
        """Start renewal process for a vehicle."""
        entry = self._pick_vehicle()
        if not entry:
            return

        # Lazy payment collection
        if not self.payment:
            console.print()
            console.print("  [yellow]Payment info is needed for renewal.[/yellow]")
            console.print()
            payment = self._collect_payment()
            if not payment:
                console.print("  [dim]Renewal cancelled.[/dim]")
                return
            if Confirm.ask("  Save card for future renewals?", default=True):
                PaymentKeychain.store(payment)
            self.payment = payment

        if self.payment.is_expired:
            console.print()
            console.print(error_panel(
                "Payment card is expired.",
                f"Card {self.payment.masked_number} expired {self.payment.expiry_display}.",
            ))
            if Confirm.ask("  Update payment info?", default=True):
                self._action_payment()
            return

        console.print()
        console.print(
            f"  Renewing [bold]{entry.vehicle.plate}[/bold] "
            f"with {self.payment.card_type} {self.payment.masked_number}..."
        )
        console.print()
        logger.info("REPL renew: plate=%s", entry.vehicle.plate)

        try:
            asyncio.run(
                self._run_renewal(entry.vehicle)
            )
        except CaptchaDetectedError:
            console.print(error_panel(
                "CAPTCHA detected.",
                "Try: faaadmv renew --headed",
            ))
        except (DMVError, FaaadmvError) as e:
            console.print(error_panel(e.message, e.details))
        except typer.Exit:
            pass  # User declined payment confirmation
        except Exception as e:
            logger.exception("Unexpected error in REPL renew")
            console.print(error_panel("Unexpected error.", str(e)))

    # --- Async operations ---

    async def _check_status(self, plate: str, vin_last5: str) -> RegistrationStatus:
        """Run status check against DMV."""
        state = self.config.state if self.config else "CA"
        provider_cls = get_provider(state)
        logger.debug("Using provider: %s", provider_cls.__name__)

        async with BrowserManager(headless=True) as bm:
            provider = provider_cls(bm.context)
            await provider.initialize()
            try:
                console.print("  [dim]Connecting to DMV portal...[/dim]")
                result = await provider.get_registration_status(plate, vin_last5)
                console.print("  [dim]Status retrieved.[/dim]")
                return result
            finally:
                await provider.cleanup()

    async def _run_renewal(self, vehicle: VehicleInfo) -> None:
        """Run the renewal flow."""
        state = self.config.state if self.config else "CA"
        provider_cls = get_provider(state)
        captcha_solver = CaptchaSolver()

        config_with_payment = self.config.with_payment(self.payment)

        async with BrowserManager(headless=True) as bm:
            provider = provider_cls(bm.context)
            await provider.initialize()

            try:
                console.print("  [dim]Connecting to DMV portal...[/dim]")
                console.print("  [dim]Checking eligibility...[/dim]")
                eligibility = await provider.validate_eligibility(
                    vehicle.plate, vehicle.vin_last5
                )

                if await provider.has_captcha():
                    solved = await captcha_solver.solve(provider.page, headed=False)
                    if not solved:
                        raise CaptchaDetectedError()

                # Show eligibility
                self._display_eligibility(eligibility)

                # Get fees
                console.print("  [dim]Retrieving fees...[/dim]")
                fees = await provider.get_fee_breakdown()

                self._display_fees(fees)

                # Confirm payment
                console.print()
                card_info = (
                    f"  Card: {self.payment.masked_number} "
                    f"(exp {self.payment.expiry_display})\n\n"
                )
                if not Confirm.ask(
                    f"{card_info}[yellow bold]\u26a0  Pay {fees.total_display} now?[/yellow bold]",
                    default=False,
                ):
                    console.print()
                    console.print("[yellow]Aborted. No payment was made.[/yellow]")
                    return

                # Submit
                console.print()
                console.print("  [dim]Processing payment...[/dim]")
                result = await provider.submit_renewal(config_with_payment)

                self._display_renewal_result(result)

            finally:
                await provider.cleanup()

    # --- Payment collection ---

    def _collect_payment(self) -> Optional[PaymentInfo]:
        """Collect payment info interactively."""
        while True:
            card = Prompt.ask("  Card number", password=True)
            if not card.strip():
                return None

            exp_month = Prompt.ask("  Exp month (MM)")
            exp_year = Prompt.ask("  Exp year (YYYY)")
            cvv = Prompt.ask("  CVV", password=True)
            billing_zip = Prompt.ask("  Billing ZIP")

            try:
                year_int = int(exp_year)
                if year_int < 100:
                    year_int += 2000
                month_int = int(exp_month)
            except ValueError:
                console.print("  [red]Invalid expiration date.[/red]")
                continue

            try:
                return PaymentInfo(
                    card_number=card,
                    expiry_month=month_int,
                    expiry_year=year_int,
                    cvv=cvv,
                    billing_zip=billing_zip,
                )
            except ValidationError as e:
                for error in e.errors():
                    console.print(f"  [red]{error['loc'][-1]}: {error['msg']}[/red]")
                console.print("  [dim]Try again.[/dim]")
                console.print()

    # --- Display helpers ---

    def _display_status(self, result: RegistrationStatus) -> None:
        """Display registration status."""
        status_styles = {
            StatusType.CURRENT: ("green", "\u2713"),
            StatusType.EXPIRING_SOON: ("yellow", "\u26a0"),
            StatusType.PENDING: ("yellow", "\u26a0"),
            StatusType.EXPIRED: ("red", "\u2717"),
            StatusType.HOLD: ("yellow", "\u26a0"),
        }
        color, icon = status_styles.get(result.status, ("white", "?"))

        content = f"[bold]{result.vehicle_description or 'Vehicle'}[/bold]"
        content += f"\nPlate:   {result.plate}"
        content += f"\nStatus:  [{color}]{icon} {result.status_display}[/{color}]"

        if result.expiration_date:
            content += f"\nExpires: {result.expiration_date.strftime('%B %d, %Y')}"
            if result.days_until_expiry is not None:
                if result.days_until_expiry > 0:
                    content += f"\nDays:    {result.days_until_expiry}"
                elif result.days_until_expiry == 0:
                    content += "\nDays:    [red]TODAY[/red]"
                else:
                    content += f"\nOverdue: [red]{abs(result.days_until_expiry)} days[/red]"

        if result.last_updated:
            content += f"\nAs of:   {result.last_updated.strftime('%B %d, %Y')}"

        if result.status_message:
            content += f"\n\n[dim]{result.status_message}[/dim]"

        console.print()
        console.print(Panel(content, title="Registration Status", border_style=color, padding=(1, 2)))

    def _display_eligibility(self, eligibility) -> None:
        """Display eligibility results."""
        console.print()
        if eligibility.smog.passed:
            console.print(f"  [green]\u2713[/green] Smog Check: Passed")
        else:
            console.print(f"  [red]\u2717[/red] Smog Check: [red]Failed[/red]")

        if eligibility.insurance.verified:
            ins = f" ({eligibility.insurance.provider})" if eligibility.insurance.provider else ""
            console.print(f"  [green]\u2713[/green] Insurance: Verified{ins}")
        else:
            console.print(f"  [red]\u2717[/red] Insurance: [red]Not Verified[/red]")

    def _display_fees(self, fees) -> None:
        """Display fee breakdown."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Desc", min_width=25)
        table.add_column("Amount", justify="right")

        for item in fees.items:
            table.add_row(item.description, item.amount_display)
        table.add_row("\u2500" * 25, "\u2500" * 10)
        table.add_row("[bold]Total[/bold]", f"[bold]{fees.total_display}[/bold]")

        console.print()
        console.print(Panel(table, title="Fees", border_style="blue", padding=(1, 2)))

    def _display_renewal_result(self, result) -> None:
        """Display renewal result."""
        console.print()
        if result.success:
            console.print(success_panel("Payment successful!"))
            if result.confirmation_number:
                console.print(f"  Confirmation: [bold]{result.confirmation_number}[/bold]")
            if result.new_expiration_date:
                exp = result.new_expiration_date.strftime("%B %Y")
                console.print(f"  [bold green]Valid through {exp}.[/bold green]")
        else:
            console.print(error_panel(
                "Renewal may not have completed.",
                result.error_message or "Check your email for confirmation.",
            ))


def run_repl() -> None:
    """Entry point for the REPL."""
    repl = FaaadmvREPL()
    repl.run()
