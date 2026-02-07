# faaadmv Provider Design

## Overview

Providers encapsulate all state-specific DMV portal logic. Each provider knows how to:
- Navigate its state's DMV website
- Fill forms with user data
- Parse responses and errors
- Handle state-specific requirements

## Provider Interface

See `src/faaadmv/providers/base.py` for the full implementation. Key points:

```python
class BaseProvider(ABC):
    """Abstract base class for DMV providers."""

    # Class attributes - override in subclasses
    state_code: str
    state_name: str
    portal_base_url: str
    allowed_domains: list[str]

    def __init__(self, context: BrowserContext):
        self.context = context
        self.page: Optional[Page] = None

    # Abstract methods (must implement in each provider):
    # - get_registration_status(plate, vin_last5) -> RegistrationStatus
    # - validate_eligibility(plate, vin_last5) -> EligibilityResult
    # - get_fee_breakdown() -> FeeBreakdown
    # - submit_renewal(config) -> RenewalResult
    # - get_selectors() -> dict[str, str]

    # Built-in helpers (available to all providers):
    # - wait_for_navigation(timeout)
    # - fill_field(selector, value)
    # - click_and_wait(selector)
    # - has_captcha() -> bool
    # - screenshot(path)
    # - save_pdf(path)
```

## California DMV Provider

### Portal URLs (verified 2026-02-07)

```python
STATUS_URL = "https://www.dmv.ca.gov/wasapp/rsrc/vrapplication.do"
RENEW_URL = "https://www.dmv.ca.gov/wasapp/vrir/start.do?localeName=en"
```

### Selectors (verified against real website)

```python
{
    # Status check -- Step 1: plate
    "status_plate_input": "#licensePlateNumber",
    "status_continue": "button[type='submit']",
    # Status check -- Step 2: VIN
    "status_vin_input": "#individualVinHin",
    "status_vin_not_found": "#iVinNotFound",
    # Status check -- Results
    "status_results_fieldset": "fieldset",
    "status_results_legend": "legend",
    # Renewal -- single page: plate + VIN
    "renew_plate_input": "#plateNumber",
    "renew_vin_input": "#vinLast5",
    "renew_continue": "button[type='submit']",
    # Error selectors
    "error_message": ".error-message, .alert-danger, .text--red",
    "smog_error": ".smog-error",
    "insurance_error": ".insurance-error",
    # Confirmation
    "confirmation_number": ".confirmation-number",
}
```

### Status Check Flow (multi-step)

The CA DMV status check is a **multi-step form**, not a single-page submission:

```
Step 1: Navigate to STATUS_URL
        Enter plate in #licensePlateNumber
        Click submit button

Step 2: Page loads VIN input
        Enter VIN (last 5) in #individualVinHin
        Click submit button
        Check for #iVinNotFound error

Step 3: Parse results from <fieldset>
        Extract <p> tags for prose text
        Map prose to StatusType via _determine_status_from_text()
        Extract date from <span style="bold">
```

### Prose Text Parsing

The results page returns prose paragraphs, not structured data. The provider maps prose to `StatusType`:

| Prose Pattern | StatusType | DMV State |
|---------------|------------|-----------|
| "has been mailed" / "was mailed" | `CURRENT` | Mailed |
| "in progress" / "not yet been mailed" | `PENDING` | InProgress |
| "not yet received" | `PENDING` | NotYetReceived |
| "items due" / "action is required" | `HOLD` | ItemsDue |
| "no further action is required" | `PENDING` | (overrides HOLD) |
| "expired" | `EXPIRED` | - |
| (unrecognized) | `PENDING` | (safe default) |

Matching is case-insensitive. The "no further action" check takes priority over "action is required" to prevent false HOLD status.

### Date Parsing

`_parse_date()` supports multiple formats found on DMV pages:
- `"February 07, 2026"` (Month DD, YYYY)
- `"02/07/2026"` (MM/DD/YYYY)
- `"2026-02-07"` (ISO format)
- Dates embedded in longer text (regex extraction)

Returns `None` on failure rather than raising.

### Amount Parsing

`_parse_amount()` extracts dollar amounts from text:
- `"$168.00"` -> `Decimal("168.00")`
- `"$1,248.00"` -> `Decimal("1248.00")` (strips commas)
- `"Total: $248.00 due"` -> `Decimal("248.00")` (regex extraction)
- No amount found -> `Decimal("0")`

### Debug Screenshots

When parsing fails, `_debug_screenshot(label)` saves a full-page screenshot to `./dmv_debug_{label}_{date}.png` for manual investigation. Screenshot failures are silently caught to avoid masking real errors.

## Provider Registry

```python
from faaadmv.providers.registry import get_provider, list_providers

# Get provider class for a state
CADMVProvider = get_provider("CA")  # Returns class, not instance

# List available states
states = list_providers()  # ["CA"]

# Unknown state raises ValueError
get_provider("XX")  # ValueError: No provider for XX. Available: CA
```

## Adding New Providers

To add support for a new state:

1. Create `src/faaadmv/providers/{state}_dmv.py`
2. Implement all 5 abstract methods from `BaseProvider`
3. Add real selectors for the state's DMV portal
4. Register in `PROVIDERS` dict in `registry.py`
5. Add tests for the new provider

### Template for New Provider

```python
from faaadmv.providers.base import BaseProvider

class XXDMVProvider(BaseProvider):
    """[State Name] DMV provider."""

    state_code = "XX"
    state_name = "[State Name]"
    portal_base_url = "https://..."
    allowed_domains = ["..."]

    def get_selectors(self) -> dict[str, str]:
        return {
            # Map all required selectors
        }

    async def get_registration_status(self, plate, vin_last5):
        # Implement status check
        ...

    async def validate_eligibility(self, plate, vin_last5):
        # Implement eligibility check
        ...

    async def get_fee_breakdown(self):
        # Implement fee parsing
        ...

    async def submit_renewal(self, config):
        # Implement renewal submission
        ...
```
