"""Provider registry for discovering and instantiating providers."""

from typing import Type

from faaadmv.providers.base import BaseProvider


def _get_providers() -> dict[str, Type[BaseProvider]]:
    """Get all available providers.

    Lazy import to avoid circular dependencies.
    """
    from faaadmv.providers.ca_dmv import CADMVProvider

    return {
        "CA": CADMVProvider,
        # Future providers:
        # "TX": TXDMVProvider,
        # "NY": NYDMVProvider,
    }


def get_provider(state: str) -> Type[BaseProvider]:
    """Get provider class for a state.

    Args:
        state: Two-letter state code (e.g., "CA")

    Returns:
        Provider class for the state

    Raises:
        ValueError: If no provider exists for the state
    """
    providers = _get_providers()
    state_upper = state.upper()

    if state_upper not in providers:
        available = ", ".join(sorted(providers.keys()))
        raise ValueError(
            f"No provider available for '{state}'. "
            f"Supported states: {available}"
        )

    return providers[state_upper]


def list_providers() -> list[str]:
    """List available state codes.

    Returns:
        List of supported state codes
    """
    return sorted(_get_providers().keys())
