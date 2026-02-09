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
| Log leakage | Logs stay local; avoid writing PII beyond plate/VIN last 5. Delete logs if needed. |

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

## Sensitive Data Handling

```python
from pydantic import SecretStr

class PaymentInfo(BaseModel):
    card_number: SecretStr
    cvv: SecretStr

# Access secret value only when needed
card = payment.card_number.get_secret_value()
```

## Local Files and Artifacts

- Config file: `~/Library/Application Support/faaadmv/config.toml` (macOS)
- Debug log: `~/Library/Application Support/faaadmv/debug.log`
- Screenshots: `~/Library/Application Support/faaadmv/artifacts/`

Delete these files if you do not want local traces.
