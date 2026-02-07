"""Tests for provider registry."""

import pytest

from faaadmv.providers.registry import get_provider, list_providers
from faaadmv.providers.ca_dmv import CADMVProvider
from faaadmv.providers.base import BaseProvider


class TestGetProvider:
    def test_ca_provider(self):
        provider_cls = get_provider("CA")
        assert provider_cls is CADMVProvider

    def test_lowercase_accepted(self):
        provider_cls = get_provider("ca")
        assert provider_cls is CADMVProvider

    def test_invalid_state(self):
        with pytest.raises(ValueError) as exc_info:
            get_provider("XX")
        assert "XX" in str(exc_info.value)
        assert "CA" in str(exc_info.value)  # Should list available

    def test_empty_state(self):
        with pytest.raises(ValueError):
            get_provider("")


class TestListProviders:
    def test_returns_list(self):
        providers = list_providers()
        assert isinstance(providers, list)

    def test_ca_in_list(self):
        assert "CA" in list_providers()

    def test_sorted(self):
        providers = list_providers()
        assert providers == sorted(providers)


class TestCADMVProviderClass:
    def test_class_attributes(self):
        assert CADMVProvider.state_code == "CA"
        assert CADMVProvider.state_name == "California"
        assert "dmv.ca.gov" in CADMVProvider.portal_base_url

    def test_inherits_base(self):
        assert issubclass(CADMVProvider, BaseProvider)

    def test_selectors_not_empty(self):
        # We need a mock context to instantiate, but can test the method via class
        # Since get_selectors doesn't use self.context, we can test with a dummy
        from unittest.mock import MagicMock
        provider = CADMVProvider.__new__(CADMVProvider)
        selectors = provider.get_selectors()
        assert isinstance(selectors, dict)
        assert len(selectors) > 0
        assert "status_plate_input" in selectors
        assert "status_vin_input" in selectors
        assert "renew_plate_input" in selectors
