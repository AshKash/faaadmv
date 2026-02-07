# PRD: faaadmv – Agentic DMV Renewal CLI

## Vision
An interactive CLI tool that turns the manual, hostile DMV renewal process into a single command.

## Target Audience
Power users and developers (distributed via GitHub/PyPI).

## Core Tech Stack
- **Runtime:** Python 3.11+
- **Browser Automation:** Playwright for Python
- **Secure Storage:** `keyring` (OS keychain) + `cryptography` (Fernet/AES-256-GCM)
- **CLI Framework:** Typer + Rich (interactive prompts, tables, progress bars)

---

## 1. Functional Requirements

### FR1: Registration Flow (`faaadmv register`)

Interactive setup wizard to gather and securely store user data for "Path A" (No-Login) renewal.

**Data Points:**
| Category | Fields |
|----------|--------|
| Vehicle | License Plate, Last 5 digits of VIN, Nickname (optional) |
| Owner | Full Name, Phone, Email, Physical Address |
| Payment | Card Number, Expiry (MM/YY), CVV, Billing ZIP |

**Multi-Vehicle Support:**
- Users can register multiple vehicles under a single profile
- Each vehicle is identified by its plate number (primary key)
- Owner and payment info are shared across vehicles
- First registered vehicle becomes the default

**Storage Requirements:**
- Location: `~/.config/faaadmv/`
- Encryption: AES-256-GCM with key derived via Argon2id from user passphrase
- Sensitive fields (CC, CVV) should use OS keychain via `keyring` when available
- Config schema must be versioned for future migrations

**Commands:**
```bash
faaadmv register               # Interactive first-time setup wizard (adds a vehicle)
faaadmv register --vehicle     # Add or update a vehicle
faaadmv register --payment     # Update payment info only
faaadmv register --verify      # Validate stored config (masked output)
faaadmv register --reset       # Wipe all stored data (with confirmation)
```

### FR1b: Vehicle Management (`faaadmv vehicles`) — *Planned*

Manage multiple registered vehicles.

**Commands:**
```bash
faaadmv vehicles               # List all registered vehicles
faaadmv vehicles --add         # Add a new vehicle (alias for register --vehicle)
faaadmv vehicles --remove 8ABC123  # Remove a vehicle by plate
faaadmv vehicles --default 8ABC123 # Set default vehicle
```

**Example Session:**
```bash
$ faaadmv vehicles

  ┌──────────────────────────────────────────────────┐
  │ Registered Vehicles                              │
  ├───┬──────────┬───────────┬────────────┬──────────┤
  │   │ Plate    │ VIN       │ Nickname   │ Default  │
  ├───┼──────────┼───────────┼────────────┼──────────┤
  │ 1 │ 8ABC123  │ ***12345  │ Honda      │ ✓        │
  │ 2 │ 7XYZ999  │ ***67890  │ Tesla      │          │
  └───┴──────────┴───────────┴────────────┴──────────┘

  2 vehicles registered.
```

**Vehicle Selection:**
When multiple vehicles are registered, `status` and `renew` commands:
1. Use `--plate <PLATE>` if specified
2. Use the default vehicle if only one, or if a default is set
3. Prompt the user to select interactively if ambiguous

---

### FR2: Renewal Flow (`faaadmv renew`)

The core agentic workflow to complete registration renewal via CA DMV Guest Portal.

**Trigger:** User runs command; agent pulls data from encrypted local config.

**Interactive Workflow:**
1. Launch browser (headless by default)
2. Navigate to DMV Renewal Guest Page
3. Input Plate and VIN
4. Handle CAPTCHA:
   - Primary: Attempt automated solve via 2Captcha/Anti-Captcha API
   - Fallback: Switch to headed mode, prompt user to solve manually
5. Verify eligibility (Smog/Insurance status)
   - If error: Surface specific error message to CLI, abort gracefully
6. Display fee breakdown to user
7. **Safety checkpoint:** Require explicit `y/N` confirmation before payment
8. Input payment and billing info
9. Submit and capture confirmation
10. Download/save PDF receipt to current directory

**Vehicle Selection:**
- If only one vehicle registered, it is used automatically
- If multiple vehicles, user must specify: `faaadmv renew --plate 8ABC123`
- Or select interactively from a list

**Example Session:**
```bash
$ faaadmv renew

  faaadmv v1.0.0 - DMV Registration Renewal

  Loading your saved configuration...

  Vehicle: 8ABC123 (VIN: ***12345)
  Owner:   Jane Doe

  Connecting to CA DMV portal...
  Submitting vehicle info... done
  Checking eligibility...

  ✓ Smog Check: Passed (01/15/2026)
  ✓ Insurance: Verified (State Farm)

  ┌─────────────────────────────────┐
  │ Registration Fees               │
  ├─────────────────────────────────┤
  │ Registration Fee      $168.00   │
  │ CHP Fee                $32.00   │
  │ County Fee             $48.00   │
  ├─────────────────────────────────┤
  │ Total                 $248.00   │
  └─────────────────────────────────┘

  Card: ****4242 (exp: 12/27)

  ⚠️  Pay $248.00 now? [y/N]: y

  Processing payment...

  ✓ Payment successful!
  ✓ Receipt saved to ./dmv_receipt_2026-02-07.pdf

  Your registration is now valid through February 2027.
```

**Dry Run Mode:**
```bash
faaadmv renew --dry-run  # Stops before payment, validates entire flow
```

---

### FR3: Status Check Flow (`faaadmv status`)

Non-mutating flow to verify current registration standing.

**Logic:** Navigate to DMV Registration Status Tool, extract data.

**Vehicle Selection:** Same rules as `renew` — auto-select single vehicle, `--plate` for multi, or interactive prompt.

**Example Session:**
```bash
$ faaadmv status

  faaadmv v1.0.0 - Registration Status Check

  Checking registration for 8ABC123...

  ┌─────────────────────────────────┐
  │ 2019 Honda Accord               │
  │ Plate: 8ABC123                  │
  ├─────────────────────────────────┤
  │ Status:     ✓ Current           │
  │ Expires:    June 20, 2026       │
  │ Days left:  133                 │
  └─────────────────────────────────┘
```

**Possible Status Values:**
- `✓ Current` — Registration valid
- `⚠️ Expiring Soon` — Within 90 days of expiration
- `⚠️ Pending` — Renewal submitted, processing
- `✗ Expired` — Past due (shows days overdue)
- `⚠️ Hold` — Issue on file (with reason if available)

---

## 2. Technical Architecture

### Provider Pattern (Multi-State Support)

```
faaadmv/
├── providers/
│   ├── base.py           # Abstract base class
│   ├── ca_dmv.py         # California implementation
│   └── tx_dmv.py         # Texas (future)
├── core/
│   ├── browser.py        # Playwright wrapper
│   ├── config.py         # Encrypted config management
│   ├── crypto.py         # Encryption utilities
│   └── captcha.py        # CAPTCHA solving strategies
├── cli/
│   ├── app.py            # Typer app definition
│   └── ui.py             # Rich console UI helpers
└── __main__.py           # Entry point
```

**BaseProvider Interface:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RegistrationStatus:
    plate: str
    expiration: str
    status: str  # "current", "expired", "pending"

class BaseProvider(ABC):
    state_code: str
    portal_url: str

    @abstractmethod
    async def get_registration_status(self, plate: str, vin: str) -> RegistrationStatus:
        ...

    @abstractmethod
    async def submit_renewal(self, config: dict) -> dict:
        ...

    @abstractmethod
    async def validate_eligibility(self, plate: str, vin: str) -> dict:
        ...

    @abstractmethod
    def get_selectors(self) -> dict[str, str]:
        """Return CSS/XPath selectors for this provider's portal."""
        ...
```

**Adding New States:**
Contributors create a new provider class without touching CLI core logic. Each provider owns:
- Portal URLs and navigation flow
- CSS/XPath selectors (with AI fallback descriptions)
- State-specific fee calculations
- Error message parsing

---

### Browser Automation Strategy

**Engine:** Playwright (bundled Chromium)

**Selector Resilience:**
1. Primary: Explicit CSS/XPath selectors per provider
2. Fallback: AI-assisted selector finding using element descriptions
   - "Find the input field labeled 'License Plate Number'"
   - Uses local LLM or Claude API for interpretation

**CAPTCHA Handling (Priority Order):**
1. Check if CAPTCHA present; skip if not
2. Attempt 2Captcha/Anti-Captcha API solve (if API key configured)
3. Fall back to headed browser mode with user prompt
4. Timeout after 120s with clear error

**Session Management:**
- Use persistent browser context to maintain cookies
- Implement request interception to block analytics/tracking scripts
- Set realistic user-agent and viewport

---

### Security Implementation

**Zero-Cloud Policy:**
- No user data transmitted except to DMV portal during active session
- No telemetry or analytics collected
- All config stored locally

**Encryption Spec:**
```
Primary: Fernet (AES-128-CBC + HMAC-SHA256, via `cryptography` library)
Alternative: AES-256-GCM with PBKDF2/scrypt key derivation
Key Derivation: scrypt (n=2^14, r=8, p=1) from user passphrase
Storage: ~/.config/faaadmv/config.enc (or platform-appropriate via `platformdirs`)
```

**Sensitive Data Handling:**
- Payment data preferentially stored in OS keychain (`keyring` library)
- CLI output masks sensitive fields: `Card: ****1234`
- Logs never contain PII; debug mode requires explicit `--debug` flag
- Memory: Use `SecretStr` from Pydantic for sensitive fields where applicable

**Config Validation:**
- Luhn check for credit card numbers
- Format validation for plate, VIN, ZIP
- Expiry date must be future

---

## 3. Error Handling

| Error Type | Detection | User Message | Recovery |
|------------|-----------|--------------|----------|
| Smog Check Failed | DMV error page text | "Smog certification not found. Visit a STAR station." | Abort with instructions |
| Insurance Invalid | DMV error page text | "Insurance not verified. Contact your insurer." | Abort with instructions |
| Card Declined | Payment error response | "Payment declined. Check card details or try another." | Return to config |
| Session Timeout | Navigation timeout | "DMV session expired. Retrying..." | Auto-retry once |
| CAPTCHA Failed | Solve timeout | "Could not solve CAPTCHA. Try --headed mode." | Suggest manual fallback |
| Selector Not Found | Element timeout | "Page structure changed. Please report this issue." | Log HTML, abort |

**Retry Logic:**
- Network errors: 3 retries with exponential backoff (1s, 2s, 4s)
- Session errors: 1 automatic retry with fresh session
- Payment errors: No auto-retry (require user confirmation)

---

## 4. CLI Interface

This is an **interactive CLI application** using Rich for beautiful terminal UI.

### Installation
```bash
uv pip install faaadmv

# Install Playwright browsers (first time only)
playwright install chromium
```

### Commands Overview
```bash
faaadmv register      # Interactive setup wizard (add vehicle + owner + payment)
faaadmv vehicles      # List / add / remove registered vehicles (planned)
faaadmv status        # Check current registration status
faaadmv renew         # Renew registration (with payment)
faaadmv help          # Show help
```

### Example: First-Time Setup
```bash
$ faaadmv register

  Welcome to faaadmv! Let's set up your vehicle.

  ─── Vehicle Information ───

  ? License plate number: 8ABC123
  ? Last 5 digits of VIN: 12345

  ─── Owner Information ───

  ? Full name: Jane Doe
  ? Phone number: (555) 123-4567
  ? Email: jane@example.com
  ? Street address: 123 Main Street
  ? City: Los Angeles
  ? State: CA
  ? ZIP code: 90001

  ─── Payment Information ───

  ? Card number: ****-****-****-4242
  ? Expiration (MM/YY): 12/27
  ? CVV: ***
  ? Billing ZIP: 90001

  ✓ Configuration saved securely.

  Run 'faaadmv status' to check your registration.
```

### Example: Verify Saved Config
```bash
$ faaadmv register --verify

  ┌─────────────────────────────────┐
  │ Saved Configuration             │
  ├─────────────────────────────────┤
  │ Vehicle:  8ABC123 / ***12345    │
  │ Owner:    Jane Doe              │
  │ Email:    jane@example.com      │
  │ Card:     ****4242 (exp 12/27)  │
  └─────────────────────────────────┘

  ✓ All fields valid.
```

### Global Flags
| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Show detailed step-by-step logging |
| `--headed` | Force visible browser (for CAPTCHA solving) |
| `--dry-run` | Run without making payment |
| `--plate <PLATE>` | Specify vehicle (required when multiple registered) |
| `--state <code>` | Override state (default: CA) |

---

## 5. Success Metrics

| Metric | Target |
|--------|--------|
| End-to-end completion (no CAPTCHA) | < 90 seconds |
| End-to-end completion (with CAPTCHA API) | < 120 seconds |
| Setup flow completion | < 60 seconds |
| Status check | < 15 seconds |
| Zero manual intervention rate | > 80% of renewals |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DMV redesigns portal | Medium | High | Selector versioning, AI fallback, quick-patch release process |
| CAPTCHA blocks automation | High | High | Multi-strategy: API solve → headed fallback → manual mode |
| Rate limiting/IP blocking | Medium | Medium | Request throttling, residential proxy support (opt-in) |
| Payment processor changes | Low | High | Abstract payment flow, monitor for changes |
| Legal/ToS concerns | Medium | Medium | Clear disclaimer, user takes responsibility |

---

## 7. Implementation Roadmap

### Phase 1: Foundation
- [ ] CLI scaffold with Typer + Rich
- [ ] Interactive prompts for `faaadmv register`
- [ ] Config encryption/decryption with `cryptography` (Fernet or AES-256-GCM)
- [ ] `keyring` integration for payment storage
- [ ] Config validation (Luhn, format checks) with Pydantic

### Phase 2: Read-Only Flows
- [ ] Playwright integration with headed/headless modes
- [ ] CA DMV provider: `get_registration_status()` implementation
- [ ] `faaadmv status` command with Rich output
- [ ] Basic error handling and logging

### Phase 3: Renewal Flow (Dry Run)
- [ ] CA DMV provider: full navigation flow
- [ ] CAPTCHA detection and headed fallback
- [ ] `faaadmv renew --dry-run` (stops before payment)
- [ ] Eligibility verification (smog/insurance)

### Phase 4: Payment & Release
- [ ] Payment submission flow
- [ ] PDF receipt capture and download
- [ ] Confirmation checkpoint
- [ ] End-to-end testing with real accounts
- [ ] GitHub release with documentation

### Phase 5: Multi-Vehicle Support
- [ ] Migrate config schema v1 → v2 (single vehicle → vehicle list)
- [ ] `faaadmv vehicles` command (list, add, remove, set default)
- [ ] `--plate` flag on `status` and `renew` for vehicle selection
- [ ] Interactive vehicle picker when multiple vehicles registered
- [ ] Optional vehicle nickname for easy identification
- [ ] Batch status check: `faaadmv status --all`

### Phase 6: Hardening
- [ ] 2Captcha/Anti-Captcha integration
- [ ] Retry logic and session recovery
- [ ] Selector versioning system
- [ ] AI-assisted selector fallback
- [ ] Community provider contributions (TX, NY, etc.)

---

## 8. Legal Disclaimer

faaadmv automates publicly available DMV web portals on behalf of the user. Users must:
- Only use the tool for their own vehicles
- Ensure all provided information is accurate
- Accept responsibility for any transactions initiated

This tool does not store or transmit data to third parties (except the DMV during the renewal session). The developers are not liable for failed transactions, incorrect renewals, or any fees incurred.

---

## Appendix A: Tech Stack Details

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Runtime | Python 3.11+ | Clean async support, Playwright native bindings |
| CLI Framework | Typer + Rich | Type hints, beautiful UI, interactive prompts |
| Terminal UI | Rich | Tables, progress bars, styled text, prompts |
| Browser | Playwright for Python | Cross-platform, best automation APIs, async-native |
| Encryption | `cryptography` (Fernet) | Audited, batteries-included, AES-256-CBC + HMAC |
| Keychain | `keyring` | Native OS credential storage (macOS/Windows/Linux) |
| Config | `platformdirs` + TOML | XDG-compliant paths, human-readable config |
| Validation | Pydantic | Data validation, type coercion, SecretStr |
| CAPTCHA | 2Captcha API (optional) | Reliable, affordable |
| Async | `asyncio` + `playwright.async_api` | Non-blocking browser operations |

## Appendix B: Alternative Browser Automation Options

If Playwright proves insufficient, consider:

1. **Browser Use** - LLM-driven automation, Python-native, pairs well with Playwright
2. **Stagehand (Browserbase)** - AI-native, open-source (has Python SDK)
3. **AgentQL** - Natural language selectors
4. **Selenium** - More mature but slower, larger community

MultiOn was considered but rejected due to:
- Vendor lock-in concerns
- Limited debugging capabilities
- Cost at scale
- Less control over browser state
