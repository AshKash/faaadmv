# faaadmv Feature Status

> This file tracks implementation status and testability for each feature.
> Updated as features are implemented. Used by the testing agent to know what's ready.
>
> **Statuses:** `not started` | `in progress` | `testable` | `tested`

---

## Data Models (`src/faaadmv/models/`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| VehicleInfo validation | testable | `VehicleInfo(plate="8abc-123", vin_last5="12345")` normalizes to `8ABC123`. Reject `vin_last5="12O45"` (O not allowed). |
| OwnerInfo validation | testable | Phone `"(555) 123-4567"` normalizes to `"5551234567"`. Reject phone `"123"` (too short). EmailStr validates format. |
| Address validation | testable | State `"ca"` normalizes to `"CA"`. ZIP must match `^\d{5}(-\d{4})?$`. |
| PaymentInfo Luhn check | testable | `"4242424242424242"` passes Luhn. `"1234567890123456"` fails. CVV must be 3-4 digits. |
| PaymentInfo expiry check | testable | `PaymentInfo(..., expiry_month=1, expiry_year=2020).is_expired` is `True`. |
| PaymentInfo masking | testable | `.masked_number` returns `"****4242"`. `.card_type` returns `"Visa"` for cards starting with 4. |
| UserConfig serialization | testable | `model_dump(mode="json", exclude_none=True)` excludes `payment` field. `with_payment()` returns new config with payment attached. |
| RegistrationStatus properties | testable | `.is_renewable` is True for CURRENT and EXPIRING_SOON. `.status_emoji` returns correct symbols. |
| FeeBreakdown total | testable | `.total` sums all `FeeItem.amount` values. `.total_display` formats as `"$248.00"`. |
| RenewalResult | testable | `RenewalResult(success=True, amount_paid=Decimal("248.00")).amount_display` returns `"$248.00"`. |

## Encryption (`src/faaadmv/core/crypto.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Encrypt/decrypt roundtrip | testable | `crypto.decrypt(crypto.encrypt("secret"))` == `"secret"`. |
| Wrong passphrase fails | testable | Encrypt with passphrase A, decrypt with B raises `ConfigDecryptionError`. |
| Salt uniqueness | testable | Two encryptions of same plaintext produce different ciphertext. |
| Empty passphrase rejected | testable | `ConfigCrypto("")` raises `ValueError`. |

## Config Manager (`src/faaadmv/core/config.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Save and load roundtrip | testable | `manager.save(config, "pass"); loaded = manager.load("pass")` — fields match. Use `tmp_path` for `config_dir`. |
| Config file is encrypted | testable | Read raw bytes of `config.enc` — should not contain plaintext like `"Jane Doe"`. |
| Wrong passphrase | testable | `manager.load("wrong")` raises `ConfigDecryptionError`. |
| Config not found | testable | New dir, `manager.load("any")` raises `ConfigNotFoundError`. |
| Delete config | testable | `manager.delete()` returns True, file gone. Second `delete()` returns False. |
| Schema migration | testable | Config with `version=1` loads successfully with current `CURRENT_VERSION`. |
| Config dir auto-creation | testable | `manager.save()` on non-existent dir creates it. |

## Keychain (`src/faaadmv/core/keychain.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Store and retrieve payment | testable | `PaymentKeychain.store(info); retrieved = PaymentKeychain.retrieve()` — fields match. Mock `keyring` for unit tests. |
| Delete payment | testable | `PaymentKeychain.delete()` removes all keys. `PaymentKeychain.exists()` returns False after. |
| Retrieve returns None when empty | testable | Fresh keyring, `PaymentKeychain.retrieve()` returns `None`. |

## Exceptions (`src/faaadmv/exceptions.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Exception hierarchy | testable | `isinstance(ConfigNotFoundError(), ConfigError)` is True. All inherit `FaaadmvError`. |
| Exception messages | testable | `ConfigNotFoundError().message` == `"Configuration not found"`. `.details` contains user guidance. |
| PaymentDeclinedError | testable | Inherits from `PaymentError`. `.message` == `"Payment failed"`. |

## CLI App (`src/faaadmv/cli/app.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| `--version` flag | testable | `runner.invoke(app, ["--version"])` output contains `"0.1.0"`. |
| No args enters REPL | testable | `runner.invoke(app, [], input="q\n")` — output contains `"faaadmv"`. Does NOT show help text. |
| `--help` flag | testable | `runner.invoke(app, ["--help"])` exit code 0, output contains `register`, `status`, `vehicles`, `renew`. |
| Command routing | testable | `register`, `status`, `vehicles`, `renew` are valid subcommands (appear in help). |
| Invalid command | testable | `runner.invoke(app, ["invalid_command"])` exit code != 0. |

## Interactive REPL (`src/faaadmv/cli/repl.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| REPL starts with no args | testable | `runner.invoke(app, [], input="q\n")` enters REPL, shows dashboard. |
| No config: shows "Add a vehicle" | testable | Fresh state (no config), REPL shows "No vehicles registered" and "Add a vehicle" option. |
| Quit with "q" | testable | Input `"q\n"` exits cleanly with "Goodbye" message. |
| Add vehicle flow | testable | In REPL, input `"a\n8ABC123\n12345\n\ntest1234\ntest1234\nq\n"` → adds vehicle, shows "Vehicle 8ABC123 added". Mock `ConfigManager` to use `tmp_path`. |
| Dashboard shows vehicles | testable | After adding vehicle, dashboard lists plate numbers. Default vehicle marked with star. |
| Dashboard masks payment | testable | If payment stored in keychain, dashboard shows `****XXXX` masked card number. |
| Status check from REPL | testable | With registered vehicle, "s" action queries DMV portal via async provider. Mock provider for unit tests. |
| Renew from REPL | testable | With registered vehicle, "r" action checks for payment, shows eligibility/fees, confirms payment. Lazy: only asks for CC when renewing. Mock provider. |
| Lazy payment collection | testable | Renew prompts for payment only if not already stored. Collected inline, saved to keychain. |
| Remove vehicle | testable | With 2+ vehicles, "d" action removes selected vehicle with confirmation. Cannot remove last vehicle. |
| Set default vehicle | testable | With 2+ vehicles, "f" action sets default. Already-default shows info message. |
| Vehicle picker (multi) | testable | With 2+ vehicles, actions requiring vehicle selection show numbered list. |
| Session passphrase caching | testable | Passphrase prompted once on session load, reused for subsequent saves without re-prompting. |

## UI Helpers (`src/faaadmv/cli/ui.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| success_panel | testable | Returns a `Panel` with green border. |
| error_panel with details | testable | Returns a `Panel` with red border. If details provided, they appear in output. |
| warning_panel | testable | Returns a `Panel` with yellow border. |
| masked_value | testable | `masked_value("4242424242424242", 4)` returns `"************4242"`. |
| format_phone | testable | `format_phone("5551234567")` returns `"(555) 123-4567"`. |

## Register Command (`src/faaadmv/cli/commands/register.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Interactive full setup | testable | Use `typer.testing.CliRunner`. Provide all inputs via `input=` kwarg (newline-separated). Config file should be created. Mock `keyring` for payment storage. |
| Input validation (vehicle) | testable | Enter invalid VIN like `"12O45"` — should show validation error and re-prompt. Needs `while True` loop in `_collect_vehicle_info`. |
| Input validation (payment) | testable | Enter invalid card number — should show Luhn error and re-prompt. |
| Passphrase prompt + confirm | testable | After all data collected, prompts for passphrase twice. Mismatch re-prompts. Min length 4 chars. |
| Save config (encrypted) | testable | After register, `ConfigManager(config_dir=...).exists` is True. Raw bytes don't contain plaintext. |
| Save payment to keychain | testable | After register, `keyring.get_password("faaadmv", "card_number")` returns the card. Mock `keyring`. |
| `--verify` with real data | testable | After registering, `register --verify` loads real config and shows masked fields (plate, masked VIN, masked email, masked card). |
| `--verify` no config | testable | Without config, shows error "No configuration found". Exit code 1. |
| `--verify` wrong passphrase | testable | With config, wrong passphrase shows "Wrong passphrase" error. Exit code 1. |
| `--reset` deletes everything | testable | `register --reset` + confirm yes → config file deleted, keychain cleared. |
| `--reset` cancel | testable | `register --reset` + confirm no → "Cancelled", nothing deleted. |
| `--vehicle` partial update | testable | With existing config, `--vehicle` only prompts for vehicle info, preserves owner. Requires passphrase first. |
| `--payment` partial update | testable | With existing config, `--payment` only prompts for payment info, stores in keychain. |
| `--vehicle` no existing config | testable | Shows error "No existing configuration found". Exit code 1. |
| Ctrl+C cancellation | testable | KeyboardInterrupt → "Setup cancelled" message, exit code 1. |

## Browser Manager (`src/faaadmv/core/browser.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Launch headless browser | testable | `async with BrowserManager() as bm: assert bm.is_launched`. Requires `playwright install chromium`. |
| Launch headed browser | testable | `BrowserManager(headless=False)` — opens visible window. Manual/visual test. |
| New page creation | testable | `page = await bm.new_page(); assert page is not None`. |
| Context available | testable | `bm.context` is not None after launch. |
| Tracker blocking | testable | `bm.BLOCKED_PATTERNS` contains google-analytics, facebook, doubleclick entries. Route interception set up on context. |
| Cleanup on exit | testable | After `async with` block exits, `bm.is_launched` is False, `bm.context` is None. |
| Timeout configuration | testable | `BrowserManager(timeout=5000)` — `bm.timeout` == 5000. |
| Error if not launched | testable | `bm.new_page()` without `launch()` raises `RuntimeError`. |

## CAPTCHA Handler (`src/faaadmv/core/captcha.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Detect reCAPTCHA | testable | Mock page with `query_selector("iframe[src*='recaptcha']")` returning truthy → `detect()` returns True. |
| Detect hCaptcha | testable | Mock page with `query_selector("iframe[src*='hcaptcha']")` returning truthy → `detect()` returns True. |
| No CAPTCHA detected | testable | Mock page where all selectors return None → `detect()` returns False. |
| Solve returns True when no CAPTCHA | testable | `solve(page)` on page without CAPTCHA returns True immediately. |
| Manual fallback prompt | testable | When `headed=True`, no API key, CAPTCHA present → waits for user to solve (polls `detect()`). |
| API key from env | testable | `CaptchaSolver()` reads `CAPTCHA_API_KEY` from `os.environ`. |
| CaptchaDetectedError in headless | testable | CAPTCHA present, `headed=False`, no API key → raises `CaptchaDetectedError`. |
| Sitekey extraction | testable | Mock page with `data-sitekey="abc123"` → `_extract_sitekey()` returns `"abc123"`. |

## Status Command (`src/faaadmv/cli/commands/status.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Load config + passphrase | testable | Prompts for passphrase, loads real config via `ConfigManager`. |
| Query DMV portal | tested | Launches browser via `BrowserManager`, calls `provider.get_registration_status()`. Verified against real CA DMV 2026-02-07. Multi-step form: plate → VIN → results. |
| Display real status | testable | `_display_status(result)` renders panel with vehicle, plate, status. Handles optional `expiration_date`, `status_message`, `last_updated`. |
| Display status colors | testable | CURRENT = green, EXPIRING_SOON = yellow, EXPIRED = red. |
| Display days remaining | testable | Positive days show "Days left: N". Zero shows "TODAY". Negative shows "Overdue: N days". Skips when `days_until_expiry` is None. |
| Error: config not found | testable | No config → error panel "No configuration found" + guidance. Exit code 1. |
| Error: wrong passphrase | testable | Bad passphrase → error panel "Wrong passphrase". Exit code 1. |
| Error: vehicle not found | testable | Provider raises `VehicleNotFoundError` → shown to user. |
| Error: browser not installed | testable | `BrowserError` → message includes "playwright install chromium". |
| Error: CAPTCHA | testable | `CaptchaDetectedError` → message suggests `--headed` flag. |
| `--verbose` output | testable | Shows vehicle plate and provider info before query. Shows plate/VIN and renewable status after. |

## Renew Command (`src/faaadmv/cli/commands/renew.py`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Load config + payment | testable | Loads encrypted config via `ConfigManager`, payment via `PaymentKeychain.retrieve()`. For unit tests: mock both. |
| Expired card rejection | testable | Payment with expired card → error panel "Payment card is expired" before any browser activity. |
| Missing payment (non-dry-run) | testable | No payment in keychain + not `--dry-run` → error "Payment information not found". |
| Eligibility check | testable | Calls `provider.validate_eligibility()`. Mock provider for unit tests. |
| Eligibility display | testable | `_display_eligibility(result)` shows green check for passed smog/insurance, red X for failed. Test by calling directly. |
| Fee breakdown display | testable | `_display_fees(fees)` renders Rich table with items and total. Test by calling directly with `FeeBreakdown`. |
| Payment confirmation prompt | testable | Shows total, asks y/N. Input `n` → "Aborted. No payment was made." |
| Payment confirmation shows card | testable | Confirmation prompt includes masked card number and expiry. |
| Submit payment | testable | Calls `provider.submit_renewal(config)` with payment attached. Mock provider for tests. |
| Result display (success) | testable | `_display_result(result)` with `success=True` shows confirmation number, receipt path, new expiration. |
| Result display (failure) | testable | `_display_result(result)` with `success=False` shows error message. |
| `--dry-run` mode | testable | After fee display, shows "Dry run complete" and returns without payment. |
| `--headed` mode | testable | `BrowserManager(headless=False)` used. CAPTCHA solver gets `headed=True`. |
| `--verbose` output | testable | Shows vehicle plate, owner name, card info after loading config. |
| Error: smog check failed | testable | `SmogCheckError` → error panel with smog station guidance. |
| Error: insurance not verified | testable | `InsuranceError` → error panel with insurance provider guidance. |
| Error: payment declined | testable | `PaymentDeclinedError` → error panel "Card declined". |
| Error: CAPTCHA detected | testable | `CaptchaDetectedError` → suggests `--headed` flag. |
| Step progress display | testable | `_step("msg", 1, 6)` outputs `[1/6] msg ✓`. |

## Provider Layer (`src/faaadmv/providers/`)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Provider registry | testable | `get_provider("CA")` returns `CADMVProvider`. `get_provider("XX")` raises `ValueError`. |
| List providers | testable | `list_providers()` returns `["CA"]`. |
| BaseProvider interface | testable | Subclass without all abstract methods → `TypeError`. |
| CA DMV selectors | tested | `CADMVProvider.get_selectors()` returns dict with keys: `status_plate_input`, `status_vin_input`, `renew_plate_input`, etc. Verified against real website. |
| CA DMV status check | tested | Multi-step form: `#licensePlateNumber` → Continue → `#individualVinHin` → Continue → parse fieldset. Verified 2026-02-07. |
| CA DMV vehicle not found | tested | Invalid plate/VIN → `#iVinNotFound` error label → `VehicleNotFoundError`. Verified 2026-02-07. |
| CA DMV date parsing | testable | `provider._parse_date("February 07, 2026")` returns `date(2026, 2, 7)`. Supports `%m/%d/%Y` format too. Returns None on failure. |
| CA DMV amount parsing | testable | `provider._parse_amount("$168.00")` returns `Decimal("168.00")`. Handles commas: `"$1,234.56"` → `Decimal("1234.56")`. |
| CA DMV status from text | testable | `_determine_status_from_text("in progress")` → `PENDING`. `"has been mailed"` → `CURRENT`. `"items due"` → `HOLD`. |
| BaseProvider helpers | testable | `has_captcha()`, `fill_field()`, `click_and_wait()`, `wait_for_navigation()` — test with mocked Playwright page. |

## Multi-Vehicle Support (Phase 5)

| Feature | Status | Test Hints |
|---------|--------|------------|
| Config schema v2 (vehicle list) | testable | `UserConfig(vehicles=[VehicleEntry(vehicle=VehicleInfo(plate="8ABC123", vin_last5="12345"), is_default=True)], owner=...)`. `config.vehicle` backward compat returns default vehicle's `VehicleInfo`. `config.vehicles` is a `list[VehicleEntry]`. |
| VehicleEntry model | testable | `VehicleEntry(vehicle=info, nickname="My Car", is_default=True)`. `.plate` and `.vin_last5` shortcuts. `.display_name` returns nickname or plate. |
| v1 → v2 migration | testable | Write v1 TOML with `vehicle: {plate, vin_last5}`, encrypt, load via `ConfigManager`. Should auto-migrate: `loaded.version == 2`, `len(loaded.vehicles) == 1`, `loaded.vehicles[0].is_default == True`. |
| `config.add_vehicle()` | testable | Returns new config with vehicle appended. `is_default=True` clears other defaults. |
| `config.remove_vehicle()` | testable | Returns new config minus vehicle. Raises if last vehicle. Promotes next to default if removed was default. |
| `config.set_default()` | testable | Returns new config with given plate as default, clears others. Raises if plate not found. |
| `config.get_vehicle()` | testable | `config.get_vehicle("8ABC123")` returns `VehicleEntry` or `None`. |
| `faaadmv vehicles` list | testable | With config, `runner.invoke(app, ["vehicles"], input="passphrase\n")` shows table of vehicles. Mock `ConfigManager`. |
| `faaadmv vehicles --add` | testable | Interactive prompt for plate + VIN + nickname. Saves updated config. Mock `ConfigManager`. Rejects duplicate plates. |
| `faaadmv vehicles --remove <plate>` | testable | Removes vehicle by plate with confirmation. Rejects last vehicle removal. Mock `ConfigManager`. |
| `faaadmv vehicles --default <plate>` | testable | Sets default vehicle. Already-default shows message. Not-found shows error. Mock `ConfigManager`. |
| `--plate` flag on status/renew | testable | `faaadmv status --plate 8ABC123` selects specific vehicle. Not-found plate shows error with list of registered plates. |
| Auto-select single vehicle | testable | With 1 vehicle, status/renew auto-selects without prompting (no vehicle picker shown). |
| Interactive vehicle picker | testable | With 2+ vehicles, no `--plate` flag → shows numbered list, prompts for selection. Provide number via `input=`. |
| Vehicle nickname | testable | `VehicleEntry(vehicle=..., nickname="My Tesla")`. `.display_name` returns `"My Tesla"`. |
| `faaadmv status --all` | testable | Batch status check for all registered vehicles. Each vehicle checked in sequence. Mock provider. |
| Payment optional in register | testable | `faaadmv register` prompts "Add payment information now?" defaulting No. Skipping still saves config. `faaadmv register --payment` adds later. |
| `register --vehicle` adds to list | testable | With existing config, `--vehicle` adds a new vehicle or updates existing plate. Prompts for nickname and default. |
