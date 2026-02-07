"""Encryption utilities for secure config storage."""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from faaadmv.exceptions import ConfigDecryptionError


class ConfigCrypto:
    """Handles config encryption/decryption using Fernet."""

    SALT_SIZE = 16
    SCRYPT_N = 2**14  # CPU/memory cost parameter
    SCRYPT_R = 8  # Block size parameter
    SCRYPT_P = 1  # Parallelization parameter
    KEY_LENGTH = 32  # 256 bits for Fernet

    def __init__(self, passphrase: str) -> None:
        """Initialize with user passphrase.

        Args:
            passphrase: User-provided passphrase for key derivation

        Raises:
            ValueError: If passphrase is empty
        """
        if not passphrase:
            raise ValueError("Passphrase cannot be empty")
        self._passphrase = passphrase.encode("utf-8")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from passphrase using scrypt.

        Args:
            salt: Random salt for key derivation

        Returns:
            Fernet-compatible base64-encoded key
        """
        kdf = Scrypt(
            salt=salt,
            length=self.KEY_LENGTH,
            n=self.SCRYPT_N,
            r=self.SCRYPT_R,
            p=self.SCRYPT_P,
            backend=default_backend(),
        )
        key = kdf.derive(self._passphrase)
        return base64.urlsafe_b64encode(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Bytes containing salt + ciphertext
        """
        salt = os.urandom(self.SALT_SIZE)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(plaintext.encode("utf-8"))
        return salt + ciphertext

    def decrypt(self, data: bytes) -> str:
        """Decrypt ciphertext.

        Args:
            data: Bytes containing salt + ciphertext

        Returns:
            Decrypted plaintext string

        Raises:
            ConfigDecryptionError: If decryption fails (wrong passphrase)
        """
        if len(data) < self.SALT_SIZE:
            raise ConfigDecryptionError()

        salt = data[: self.SALT_SIZE]
        ciphertext = data[self.SALT_SIZE :]

        try:
            key = self._derive_key(salt)
            fernet = Fernet(key)
            plaintext = fernet.decrypt(ciphertext)
            return plaintext.decode("utf-8")
        except InvalidToken:
            raise ConfigDecryptionError()
