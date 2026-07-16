"""Tests that production bootstrap fails fast on a bad provider credential."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from m07b_service.app import bootstrap


def test_bootstrap_fails_fast_when_provider_build_fails(make_settings):
    # Simulate a missing credential: the real build_default_provider raises for a
    # provider whose key is absent. bootstrap must propagate that at startup.
    def failing_factory(settings):
        raise RuntimeError("missing OPENAI_API_KEY")

    with pytest.raises(RuntimeError, match="missing OPENAI_API_KEY"):
        bootstrap(make_settings(), provider_factory=failing_factory)


def test_bootstrap_skips_factory_when_provider_injected(make_settings, make_provider):
    # When a provider is injected (tests), the eager factory must not run.
    def failing_factory(settings):
        raise AssertionError("provider_factory must not be called when a provider is injected")

    app = bootstrap(make_settings(), provider=make_provider(), provider_factory=failing_factory)
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
