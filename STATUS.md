# faaadmv Status

## Current State

- REPL-first UX with watch mode as default.
- CA DMV status check working (plate + VIN last 5).
- Renewal flow with dry-run and interactive confirmation.
- Multi-vehicle support with add/remove/default selection.
- Local debug logging and screenshots per run.

## Feature Checklist

### REPL

| Feature | Status | Notes |
|---------|--------|-------|
| Menu-driven workflow | implemented | `s`, `r`, `d`, `a`, `x`, `m`, `p`, `w`, `q` |
| Watch mode (headed) | implemented | Default ON, pauses for Enter |
| Screenshots per run | implemented | Stored in local artifacts dir |
| Errors surfaced via panels | implemented | Includes VIN-not-found and CAPTCHA guidance |

### Vehicle Management

| Feature | Status | Notes |
|---------|--------|-------|
| Add vehicle | implemented | Plate + VIN last 5 |
| Remove vehicle | implemented | Confirmation required |
| Set default | implemented | For multi-vehicle configs |
| Multi-vehicle config | implemented | Encrypted local config |

### Status Check

| Feature | Status | Notes |
|---------|--------|-------|
| CA DMV status flow | implemented | Parses status text + date |
| VIN-not-found detection | implemented | Error panel + screenshot |

### Renewal

| Feature | Status | Notes |
|---------|--------|-------|
| Fee breakdown | implemented | Displayed before confirmation |
| Dry-run renewal | implemented | Stops before payment |
| Payment submission | implemented | Confirmed by user |

### Storage & Logs

| Feature | Status | Notes |
|---------|--------|-------|
| Encrypted config | implemented | scrypt + Fernet |
| Payment in keychain | implemented | No disk storage |
| Debug log | implemented | Local file in app data dir |
| Screenshots | implemented | Local artifacts folder |

## Known Gaps

- CAPTCHA may still require manual completion in watch mode.
- Renewal success flow depends on live DMV portal behavior.
