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
| `--version` flag | testable | `runner.invoke(app, ["--version"])` output contains `"faaadmv v0.1.0"`. |
| `--help` / no args | testable | `runner.invoke(app, [])` shows help text with `register`, `status`, `renew`. |
| Command routing | testable | `register`, `status`, `renew` are valid subcommands (appear in help). |

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
| Query DMV portal | testable | Launches browser via `BrowserManager`, calls `provider.get_registration_status()`. For unit tests: mock the provider and browser. |
| Display real status | testable | `_display_status(result)` renders panel with vehicle, plate, expiration, status. Test by calling directly with a `RegistrationStatus` object. |
| Display status colors | testable | CURRENT = green, EXPIRING_SOON = yellow, EXPIRED = red. |
| Display days remaining | testable | Positive days show "Days left: N". Zero shows "TODAY". Negative shows "Overdue: N days". |
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
| CA DMV selectors | testable | `CADMVProvider.get_selectors()` returns dict with keys: `plate_input`, `vin_input`, `submit_button`, `card_number`, etc. |
| CA DMV date parsing | testable | `provider._parse_date("06/20/2026")` returns `date(2026, 6, 20)`. Supports `%B %d, %Y` format too. |
| CA DMV amount parsing | testable | `provider._parse_amount("$168.00")` returns `Decimal("168.00")`. Handles commas: `"$1,234.56"` → `Decimal("1234.56")`. |
| CA DMV status determination | testable | `_determine_status("Current", 100)` → `CURRENT`. `_determine_status("Current", 50)` → `EXPIRING_SOON`. `_determine_status("Expired", -10)` → `EXPIRED`. |
| BaseProvider helpers | testable | `has_captcha()`, `fill_field()`, `click_and_wait()`, `wait_for_navigation()` — test with mocked Playwright page. |

## Multi-Vehicle Support — *Planned (Phase 5)*

| Feature | Status | Test Hints |
|---------|--------|------------|
| Config schema v2 (vehicle list) | not started | `UserConfig` with `vehicles: list[VehicleEntry]` instead of single `vehicle`. |
| v1 → v2 migration | not started | Load v1 config → auto-migrated to v2 with single vehicle in list, marked default. |
| `faaadmv vehicles` list | not started | Shows table of registered vehicles with plate, VIN, nickname, default marker. |
| `faaadmv vehicles --add` | not started | Interactive prompt for plate + VIN + optional nickname. Appended to vehicle list. |
| `faaadmv vehicles --remove <plate>` | not started | Removes vehicle by plate. Confirmation prompt. Promotes next vehicle to default if needed. |
| `faaadmv vehicles --default <plate>` | not started | Sets default vehicle. |
| `--plate` flag on status/renew | not started | `faaadmv status --plate 8ABC123` selects specific vehicle. |
| Auto-select single vehicle | not started | If only 1 vehicle, use it without prompting. |
| Interactive vehicle picker | not started | If multiple vehicles + no `--plate` + no default → Rich prompt to select. |
| Vehicle nickname | not started | Optional label for easy identification in lists. |
| `faaadmv status --all` | not started | Batch status check for all registered vehicles. |
