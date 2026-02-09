# PRD: faaadmv – DMV Renewal REPL

## 1. Overview

faaadmv is an interactive REPL that automates California DMV registration status checks and renewals. The UX is menu-driven, watchable (headed browser), and designed for human-in-the-loop reliability.

## 2. Goals

- Provide a fast, reliable REPL for status checks and renewals.
- Keep automation observable with a headed browser and screenshots.
- Store user data locally with encryption and OS keychain integration.
- Minimize setup friction while retaining strong privacy controls.

## 3. Non-Goals

- No background/daemon mode.
- No unattended batch processing.
- No multi-state support beyond CA for now.

## 4. Primary UX (REPL)

### Main Menu

- `s` Check registration status
- `r` Renew registration
- `d` Renew (dry-run, no payment submission)
- `a` Add a vehicle
- `x` Remove a vehicle
- `m` Set default vehicle
- `p` Add payment info
- `w` Toggle watch mode (headed browser)
- `q` Quit

### Watch Mode

- Default: ON
- When ON: browser runs headed + slowmo, pauses after each run until Enter.
- When OFF: browser runs headless and closes automatically.

### Artifacts

- After each status/renew run, a screenshot is captured.
- Artifacts are stored locally in the OS app data directory.

## 5. Functional Requirements

### FR1: Vehicle Management

- Add a vehicle with plate + last 5 of VIN.
- Store multiple vehicles with a single default.
- Remove vehicles, with confirmation and safe handling of last vehicle.
- Set default vehicle at any time.

### FR2: Status Check

- Navigate to CA DMV status page.
- Enter plate + VIN last 5.
- Parse and display status, effective date, and message text.
- Capture a screenshot at completion.

### FR3: Renewal

- Navigate renewal flow and collect fee breakdown.
- Display eligibility and fee results.
- Require confirmation before payment submission.
- Provide a dry-run option that stops before payment.
- Capture a screenshot at completion.

### FR4: Payment Storage

- Store payment details in the OS keychain.
- Do not serialize raw payment info to disk.

### FR5: Logging

- Write a local debug log for automation traces.
- Log Playwright fingerprint details and key page transitions.

## 6. Data & Storage

- Config: encrypted TOML in OS app data directory.
- Payment: OS keychain only.
- Logs: local debug log file.
- Artifacts: local screenshots folder.

## 7. Error Handling

- Surface clear error panels with actionable guidance.
- Treat “VIN not found” as a first-class error.
- Detect CAPTCHA surfaces and advise using watch mode.

## 8. Security & Privacy

- All user data is stored locally.
- Encryption uses scrypt + Fernet.
- Payment data never written to disk.

## 9. Success Metrics

- Status check completes in < 30 seconds.
- Renewal dry-run completes in < 90 seconds.
- Minimal manual intervention when watch mode is enabled.

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DMV page changes | Medium | High | Selector validation, logging, quick patching |
| Bot detection | Medium | High | Watch mode default, stealth init script, realistic browser settings |
| CAPTCHA blocks automation | Medium | High | Headed fallback, manual completion in watch mode |
| Payment processor changes | Low | High | Isolate payment flow, add guards before submission |

## 11. Legal Disclaimer

faaadmv automates publicly available DMV web portals on behalf of the user. Users must:
- Only use the tool for their own vehicles.
- Ensure all provided information is accurate.
- Accept responsibility for any transactions initiated.

This tool does not store or transmit data to third parties (except the DMV during the renewal session). The developers are not liable for failed transactions, incorrect renewals, or any fees incurred.
