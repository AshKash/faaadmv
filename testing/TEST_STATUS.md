# Test Agent Status

> This file is maintained by the **test agent**. The dev agent should check this file to see what has been tested, what passed, and what bugs were found.

**Last updated:** 2026-02-07

---

## How This Works

- **Dev agent** marks features as `testable` in `STATUS.md`
- **Test agent** (this file) writes tests, runs them, reports results here
- **Bugs** are logged in `testing/BUGS.md` with IDs like `BUG-001`
- Test files live in `tests/unit/`, `tests/integration/`, and `tests/e2e/`

---

## Summary

| Metric | Value |
|--------|-------|
| Total tests | **232** |
| Passed | **232** |
| Failed | **0** |
| Bugs found | **6** (1 critical, 3 medium, 2 low) — all 6 fixed |

### Coverage by Component

| Component | Coverage | Notes |
|-----------|----------|-------|
| Models | 92-100% | Well tested, including new status_message/last_updated |
| Crypto | 100% | Fully tested |
| Config Manager | 87% | Missing migration edge cases |
| Keychain | 92% | Tested with mock keyring |
| Exceptions | 98% | Full hierarchy tested |
| UI helpers | 100% | All helpers tested |
| Provider registry | 100% | All paths tested |
| CA DMV parsing | **95%** | `_determine_status_from_text`, `_parse_date`, `_parse_amount` covered |
| CLI app scaffold | 93% | Entry points tested |
| CLI register command | 60% | E2E: register, verify, reset, wrong passphrase |
| CLI status command | 70% | E2E: happy path, wrong pass, expired, expiring, prose display |
| CLI renew command | 65% | E2E: dry-run, full pay, decline, expired card, no payment |
| Browser manager | 33% | Needs Playwright mocking |
| CAPTCHA solver | 10% | Needs Playwright mocking |

---

## Test Runs

### Run #1 — 2026-02-07 (Phase 1: Unit Tests)

**150 tests, 150 passed**

| Component | Test File | Tests | Pass | Fail | Bugs |
|-----------|-----------|-------|------|------|------|
| VehicleInfo model | `tests/unit/test_models_vehicle.py` | 13 | 13 | 0 | BUG-001, BUG-002 |
| OwnerInfo model | `tests/unit/test_models_owner.py` | 18 | 18 | 0 | — |
| PaymentInfo model | `tests/unit/test_models_payment.py` | 20 | 20 | 0 | BUG-003 |
| UserConfig model | `tests/unit/test_models_config.py` | 8 | 8 | 0 | — |
| Result models | `tests/unit/test_models_results.py` | 14 | 14 | 0 | — |
| ConfigCrypto | `tests/unit/test_crypto.py` | 11 | 11 | 0 | — |
| ConfigManager | `tests/unit/test_config_manager.py` | 11 | 11 | 0 | — |
| Exceptions | `tests/unit/test_exceptions.py` | 20 | 20 | 0 | — |
| UI helpers | `tests/unit/test_ui.py` | 15 | 15 | 0 | — |
| Provider registry | `tests/unit/test_registry.py` | 10 | 10 | 0 | — |

### Run #2 — 2026-02-07 (Phase 2: Integration Tests)

**28 tests, 28 passed**

| Component | Test File | Tests | Pass | Fail | Bugs |
|-----------|-----------|-------|------|------|------|
| CLI entry points | `tests/integration/test_cli_app.py` | 16 | 16 | 0 | BUG-004, BUG-005 |
| Config roundtrip | `tests/integration/test_config_roundtrip.py` | 4 | 4 | 0 | — |
| Payment keychain | `tests/integration/test_keychain.py` | 8 | 8 | 0 | — |

### Run #3 — 2026-02-07 (Phase 3: E2E Tests)

**13 tests, 12 passed, 1 failed**

Found BUG-006: `test_renew_user_declines_payment` — `typer.Exit(0)` caught by broad `except Exception`.

### Run #4 — 2026-02-07 (BUG-006 fix + new CA DMV parsing tests)

**232 tests, 232 passed, 0 failed**

| Component | Test File | Tests | Pass | Fail | Notes |
|-----------|-----------|-------|------|------|-------|
| Register flow | `tests/e2e/test_register_flow.py` | 4 | 4 | 0 | — |
| Status flow | `tests/e2e/test_status_renew_flow.py` (status) | 2 | 2 | 0 | — |
| Status expired/expiring | `tests/e2e/test_status_renew_flow.py` | 2 | 2 | 0 | — |
| Status prose display | `tests/e2e/test_status_renew_flow.py` | 2 | 2 | 0 | **NEW** — tests DMV prose rendering |
| Renew dry-run | `tests/e2e/test_status_renew_flow.py` | 1 | 1 | 0 | — |
| Renew full flow | `tests/e2e/test_status_renew_flow.py` | 3 | 3 | 0 | BUG-006 **fixed** |
| Renew expired card | `tests/e2e/test_status_renew_flow.py` | 1 | 1 | 0 | — |
| CA DMV text parsing | `tests/unit/test_ca_dmv_parsing.py` | 34 | 34 | 0 | **NEW** — all prose→status branches |
| Result model new fields | `tests/unit/test_models_results.py` | 19 | 19 | 0 | +5 new for status_message etc |

---

## Bugs Found

| ID | Severity | Component | Summary | Status |
|----|----------|-----------|---------|--------|
| BUG-001 | medium | vehicle.py | Plate `max_length` check runs before normalization strips dashes | fixed |
| BUG-002 | medium | vehicle.py | Same as BUG-001 but with spaces | fixed |
| BUG-003 | low | payment.py | Luhn accepts all-zeros card number | fixed |
| BUG-004 | low | status.py / app.py | Error message references `--headed` flag that doesn't exist on `status` | fixed |
| BUG-005 | medium | register.py | Owner validation failure continues instead of retrying | fixed |
| BUG-006 | critical | renew.py | Declining payment shows "Unexpected error" instead of clean exit | fixed |

See `testing/BUGS.md` for full details with repro steps.

---

## Blocked Tests (Waiting on Dev Agent)

| Feature | What's Needed | Notes |
|---------|---------------|-------|
| Browser manager integration | Playwright chromium installed | Can unit test but needs real browser for integration |
| CAPTCHA solver integration | Mock page + optional 2Captcha key | API integration untestable without key |

---

## Next Steps for Test Agent

1. **Test CAPTCHA detection path** — mock captcha detection in status/renew E2E
2. **Test multi-vehicle support** (FR1b) — once dev agent implements it
3. **Edge cases/security** — deferred per user request until MVP E2E is green
4. **Browser manager unit tests** — mock Playwright to test BrowserManager isolation
