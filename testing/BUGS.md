# Bug Reports

> Maintained by the **test agent**. Dev agent: check this file for bugs to fix.

**Last updated:** 2026-02-07

---

## Bug Format

Each bug follows this format:
- **ID**: BUG-NNN
- **Severity**: critical / high / medium / low
- **Component**: which module
- **Summary**: one-line description
- **Expected**: what should happen
- **Actual**: what actually happens
- **Repro**: how to reproduce (test command or code snippet)
- **Status**: open / fixed / wontfix

---

## Open Bugs

_(none)_

---

## Fixed Bugs

### BUG-001 — Plate validation rejects valid input with dashes/spaces

- **Severity**: medium
- **Component**: `src/faaadmv/models/vehicle.py` (VehicleInfo)
- **Summary**: Pydantic `max_length=8` check on `plate` field runs BEFORE the `normalize_plate` validator strips non-alphanumeric characters. Plates with dashes or spaces that would normalize to <=8 chars are rejected.
- **Fix**: Removed `max_length` from the Field definition and enforced length in the `normalize_plate` validator after normalization.
- **Status**: fixed

---

### BUG-002 — Plate validation rejects valid input with spaces

- **Severity**: medium
- **Component**: `src/faaadmv/models/vehicle.py` (VehicleInfo)
- **Summary**: Same root cause as BUG-001 but with spaces. `"8 ABC 123"` is 9 chars raw but normalizes to 7.
- **Fix**: Same fix as BUG-001 — length check moved into validator.
- **Status**: fixed

---

### BUG-003 — Luhn check accepts all-zeros card number

- **Severity**: low
- **Component**: `src/faaadmv/models/payment.py` (PaymentInfo.validate_card_luhn)
- **Summary**: `"0000000000000000"` passes the Luhn algorithm (checksum 0 % 10 == 0). While mathematically correct, this is a degenerate card number that no real issuer uses.
- **Fix**: Added explicit all-zeros rejection before the Luhn check in `validate_card_luhn`.
- **Status**: fixed

---

### BUG-004 — `status` command has no `--headed` flag but error message references it

- **Severity**: low
- **Component**: `src/faaadmv/cli/commands/status.py` and `src/faaadmv/cli/app.py`
- **Summary**: When a CAPTCHA is detected during `faaadmv status`, the error message says "Try running with --headed flag" but the command didn't accept `--headed`.
- **Fix**: Added `--headed` flag to the `status` command in `app.py`, threaded it through `run_status` → `_check_status` → `BrowserManager(headless=not headed)`.
- **Status**: fixed

---

### BUG-005 — Owner validation allows invalid data to pass through

- **Severity**: medium
- **Component**: `src/faaadmv/cli/commands/register.py` (_collect_owner_info)
- **Summary**: `_collect_owner_info()` printed warnings on invalid data but continued, causing a crash in `_build_owner()`.
- **Fix**: Converted to a retry loop (matching vehicle and payment collection patterns). Invalid input now re-prompts instead of continuing.
- **Status**: fixed

---

### BUG-006 — `renew` decline payment shows "Unexpected error" instead of clean exit

- **Severity**: critical
- **Component**: `src/faaadmv/cli/commands/renew.py`
- **Summary**: Declining payment raised `typer.Exit(0)` inside async function, caught by broad `except Exception` handler, wrapped as "Unexpected error: 0".
- **Fix**: Added `except typer.Exit: raise` handler before `except Exception` to let clean exits propagate.
- **Status**: fixed
