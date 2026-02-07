# faaadmv Security Design

## Threat Model

### Assets to Protect

| Asset | Sensitivity | Storage |
|-------|-------------|---------|
| Credit Card Number | Critical | OS Keychain |
| CVV | Critical | OS Keychain |
| Card Expiry | High | OS Keychain |
| Full Name | Medium | Encrypted config |
| Address | Medium | Encrypted config |
| Phone/Email | Medium | Encrypted config |
| License Plate | Low | Encrypted config |
| VIN (last 5) | Low | Encrypted config |

### Threat Actors

1. **Local Attacker** - Has access to user's filesystem
2. **Network Attacker** - Can intercept network traffic
3. **Malicious DMV Clone** - Phishing site impersonating DMV
4. **Memory Scraper** - Malware reading process memory

### Attack Vectors & Mitigations

| Attack Vector | Mitigation |
|---------------|------------|
| Config file theft | Fernet encryption with user passphrase |
| Keychain extraction | OS-level keychain protection |
| Shoulder surfing | Masked CLI output for sensitive fields |
| MITM on DMV traffic | HTTPS only, certificate validation |
| Phishing redirect | Strict URL validation in provider |
| Memory dump | SecretStr, minimize plaintext lifetime |
| Log leakage | No PII in logs, explicit --debug required |

## Encryption Implementation

### Config File Encryption

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import os
import base64

class ConfigCrypto:
    """Handles config encryption/decryption."""

    SALT_SIZE = 16
    SCRYPT_N = 2**14  # CPU/memory cost
    SCRYPT_R = 8      # Block size
    SCRYPT_P = 1      # Parallelization

    def __init__(self, passphrase: str):
        self.passphrase = passphrase.encode()

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from passphrase using scrypt."""
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=self.SCRYPT_N,
            r=self.SCRYPT_R,
            p=self.SCRYPT_P,
            backend=default_backend(),
        )
        return base64.urlsafe_b64encode(kdf.derive(self.passphrase))

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt plaintext, returns salt + ciphertext."""
        salt = os.urandom(self.SALT_SIZE)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(plaintext.encode())
        return salt + ciphertext

    def decrypt(self, data: bytes) -> str:
        """Decrypt salt + ciphertext, returns plaintext."""
        salt = data[:self.SALT_SIZE]
        ciphertext = data[self.SALT_SIZE:]
        key = self._derive_key(salt)
        fernet = Fernet(key)
        return fernet.decrypt(ciphertext).decode()
```

### Keychain Integration

```python
import keyring
from typing import Optional

KEYRING_SERVICE = "faaadmv"

class PaymentKeychain:
    """Secure storage for payment credentials."""

    @staticmethod
    def store(card_number: str, expiry: str, cvv: str, billing_zip: str) -> None:
        """Store payment info in OS keychain."""
        keyring.set_password(KEYRING_SERVICE, "card_number", card_number)
        keyring.set_password(KEYRING_SERVICE, "card_expiry", expiry)
        keyring.set_password(KEYRING_SERVICE, "card_cvv", cvv)
        keyring.set_password(KEYRING_SERVICE, "billing_zip", billing_zip)

    @staticmethod
    def retrieve() -> Optional[dict]:
        """Retrieve payment info from OS keychain."""
        card_number = keyring.get_password(KEYRING_SERVICE, "card_number")
        if not card_number:
            return None
        return {
            "card_number": card_number,
            "expiry": keyring.get_password(KEYRING_SERVICE, "card_expiry"),
            "cvv": keyring.get_password(KEYRING_SERVICE, "card_cvv"),
            "billing_zip": keyring.get_password(KEYRING_SERVICE, "billing_zip"),
        }

    @staticmethod
    def delete() -> None:
        """Remove all payment info from keychain."""
        for key in ("card_number", "card_expiry", "card_cvv", "billing_zip"):
            try:
                keyring.delete_password(KEYRING_SERVICE, key)
            except keyring.errors.PasswordDeleteError:
                pass  # Key doesn't exist
```

## Secure Coding Practices

### Sensitive Data Handling

```python
from pydantic import SecretStr

# DO: Use SecretStr for sensitive fields
class PaymentInfo(BaseModel):
    card_number: SecretStr
    cvv: SecretStr

# DO: Access secret value only when needed
def submit_payment(payment: PaymentInfo):
    card = payment.card_number.get_secret_value()  # Only here
    # ... submit to DMV ...
    del card  # Explicit cleanup (hint to GC)

# DON'T: Log sensitive data
logger.info(f"Card: {payment.card_number}")  # NEVER

# DO: Log masked version
logger.info(f"Card: {payment.masked_number}")  # ****4242
```

### Output Masking

```python
def mask_card(card: str) -> str:
    """Mask all but last 4 digits."""
    return f"****{card[-4:]}"

def mask_vin(vin: str) -> str:
    """Mask all but last 2 characters."""
    return f"***{vin[-2:]}"

def mask_email(email: str) -> str:
    """Mask email address."""
    local, domain = email.split("@")
    return f"{local[0]}***@{domain}"
```

### Browser Security

```python
async def create_secure_browser_context(playwright) -> BrowserContext:
    """Create browser context with security settings."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-extensions",
            "--disable-plugins",
            "--disable-sync",
            "--no-first-run",
        ]
    )

    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
        ignore_https_errors=False,  # IMPORTANT: Validate certs
        java_script_enabled=True,
    )

    # Block tracking/analytics
    await context.route("**/*google-analytics*", lambda route: route.abort())
    await context.route("**/*facebook*", lambda route: route.abort())
    await context.route("**/*doubleclick*", lambda route: route.abort())

    return context
```

### URL Validation

```python
from urllib.parse import urlparse

ALLOWED_DMV_DOMAINS = {
    "CA": ["dmv.ca.gov", "www.dmv.ca.gov"],
    "TX": ["txdmv.gov", "www.txdmv.gov"],
}

def validate_dmv_url(url: str, state: str) -> bool:
    """Ensure URL is legitimate DMV domain."""
    parsed = urlparse(url)

    # Must be HTTPS
    if parsed.scheme != "https":
        return False

    # Must be known DMV domain
    allowed = ALLOWED_DMV_DOMAINS.get(state, [])
    if parsed.netloc not in allowed:
        return False

    return True
```

## Logging Policy

### What We Log

- Command invocations (without arguments)
- Navigation steps (URLs visited)
- Success/failure status
- Error messages (sanitized)
- Timing information

### What We NEVER Log

- Credit card numbers (full or partial)
- CVV codes
- Passwords or passphrases
- Full names
- Addresses
- Email addresses
- Phone numbers
- VIN numbers

### Log Sanitization

```python
import re

SENSITIVE_PATTERNS = [
    (r"\b\d{13,16}\b", "[CARD]"),           # Credit card
    (r"\b\d{3,4}\b(?=.*cvv)", "[CVV]"),     # CVV
    (r"\b[A-Z0-9]{17}\b", "[VIN]"),         # Full VIN
    (r"\b\d{5}(-\d{4})?\b", "[ZIP]"),       # ZIP code
    (r"[\w.-]+@[\w.-]+\.\w+", "[EMAIL]"),   # Email
]

def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message
```

## Incident Response

### If Config File Compromised

1. User should run `faaadmv register --reset`
2. Change any passwords that may have been reused
3. Monitor credit card for unauthorized charges
4. Config is encrypted, but treat as potentially exposed

### If Keychain Compromised

1. Contact credit card company immediately
2. Request new card number
3. Update faaadmv with new payment info
4. Review recent transactions

## Security Checklist

- [ ] Config file encrypted at rest
- [ ] Payment data in OS keychain, not config file
- [ ] No secrets in CLI output
- [ ] No secrets in logs
- [ ] HTTPS enforced for DMV connections
- [ ] Certificate validation enabled
- [ ] URL validation before navigation
- [ ] SecretStr used for sensitive Pydantic fields
- [ ] Passphrase required to decrypt config
- [ ] Secure key derivation (scrypt)
