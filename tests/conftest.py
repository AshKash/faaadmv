"""Shared test fixtures for faaadmv."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide isolated config directory for tests."""
    config_dir = tmp_path / ".config" / "faaadmv"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def mock_keyring(monkeypatch):
    """Mock keyring for payment data tests."""
    storage = {}

    def mock_get(service, key):
        return storage.get(f"{service}:{key}")

    def mock_set(service, key, value):
        storage[f"{service}:{key}"] = value

    def mock_delete(service, key):
        k = f"{service}:{key}"
        if k not in storage:
            from keyring.errors import PasswordDeleteError
            raise PasswordDeleteError(f"No password for {key}")
        storage.pop(k)

    monkeypatch.setattr("keyring.get_password", mock_get)
    monkeypatch.setattr("keyring.set_password", mock_set)
    monkeypatch.setattr("keyring.delete_password", mock_delete)

    return storage
