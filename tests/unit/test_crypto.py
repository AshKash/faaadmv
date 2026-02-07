"""Tests for ConfigCrypto."""

import pytest

from faaadmv.core.crypto import ConfigCrypto
from faaadmv.exceptions import ConfigDecryptionError


class TestConfigCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        crypto = ConfigCrypto("test-passphrase")
        plaintext = "sensitive data here"
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_unicode(self):
        crypto = ConfigCrypto("test-passphrase")
        plaintext = "Hello, world! Special chars: \u00e9\u00e0\u00fc\u00f1"
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_long_text(self):
        crypto = ConfigCrypto("test-passphrase")
        plaintext = "A" * 10000
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_different_passphrases_fail(self):
        crypto1 = ConfigCrypto("passphrase-1")
        crypto2 = ConfigCrypto("passphrase-2")
        encrypted = crypto1.encrypt("secret")
        with pytest.raises(ConfigDecryptionError):
            crypto2.decrypt(encrypted)

    def test_salt_uniqueness(self):
        crypto = ConfigCrypto("same-passphrase")
        enc1 = crypto.encrypt("same data")
        enc2 = crypto.encrypt("same data")
        assert enc1 != enc2  # Different salts produce different ciphertext

    def test_empty_passphrase_rejected(self):
        with pytest.raises(ValueError):
            ConfigCrypto("")

    def test_encrypted_output_is_bytes(self):
        crypto = ConfigCrypto("test")
        encrypted = crypto.encrypt("hello")
        assert isinstance(encrypted, bytes)

    def test_decrypt_garbage_data(self):
        crypto = ConfigCrypto("test")
        with pytest.raises(ConfigDecryptionError):
            crypto.decrypt(b"x" * 100)

    def test_decrypt_too_short_data(self):
        crypto = ConfigCrypto("test")
        with pytest.raises(ConfigDecryptionError):
            crypto.decrypt(b"short")

    def test_decrypt_empty_data(self):
        crypto = ConfigCrypto("test")
        with pytest.raises(ConfigDecryptionError):
            crypto.decrypt(b"")

    def test_encrypt_empty_string(self):
        crypto = ConfigCrypto("test")
        encrypted = crypto.encrypt("")
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == ""
