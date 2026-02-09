# faaadmv Manual Testing Guide

## Overview

Automated tests are currently removed. Use the REPL to validate behavior manually. The goal is to verify that status checks and renewal flows work end-to-end with a visible browser session.

## Required Setup

```bash
uv pip install -e .
playwright install chromium
```

## Primary Manual Tests

### 1) Status Check (Happy Path)

1. Start REPL: `faaadmv`
2. Add or select a known valid vehicle.
3. Run status check: press `s`.
4. Confirm:
   - Browser opens (watch mode)
   - Status page loads and submits
   - Results show current status and date

### 2) Status Check (Wrong VIN)

1. Edit or re-add a vehicle with an intentionally wrong VIN last 5.
2. Run status check.
3. Confirm:
   - DMV returns "VIN/HIN NOT FOUND"
   - Screenshot is saved in `~/Library/Application Support/faaadmv/artifacts/`

### 3) Renewal Dry-Run

1. In REPL, press `d` (Renew dry-run).
2. Confirm:
   - Eligibility results are displayed
   - Fees are displayed
   - No payment prompt is shown

### 4) Renewal Full Flow (Decline Payment)

1. In REPL, press `r` (Renew registration).
2. Confirm:
   - Eligibility and fees display
   - Payment prompt appears
   - Declining does not submit payment

## Diagnostics

### Logs
- `~/Library/Application Support/faaadmv/debug.log`

### Screenshots
- `~/Library/Application Support/faaadmv/artifacts/`

## Notes

- Watch mode pauses after each run. Press Enter to close the browser.
- If the DMV site silently fails, check the debug log and screenshot.
