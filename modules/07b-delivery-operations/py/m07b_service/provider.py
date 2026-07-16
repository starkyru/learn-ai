"""The ``llm_core`` seam.

Every model call in this service goes through the provider-agnostic client — we
never import an OpenAI/Anthropic SDK directly. Tests inject a fake provider that
implements the same :class:`~llm_core.LLMProvider` protocol, so the request path
is exercised deterministically and offline.
"""

from __future__ import annotations

from llm_core import LLMProvider, get_provider

from .config import Settings


def build_default_provider(settings: Settings) -> LLMProvider:
    """Construct the real provider selected by configuration.

    ``get_provider`` reads the provider-specific credentials from the
    environment itself; we only pass the validated provider name.
    """
    return get_provider(settings.provider)
