"""Tests for fail-fast configuration validation."""

from __future__ import annotations

import pytest
from m07b_service.config import ConfigError, Settings, load_settings


def test_missing_required_var_fails_fast_with_named_error():
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={})
    # The message must name the offending variable, not dump a traceback.
    assert "SERVICE_ENV" in str(excinfo.value)


def test_invalid_port_reports_port_not_a_generic_error():
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={"SERVICE_ENV": "development", "PORT": "not-a-number"})
    assert "PORT" in str(excinfo.value)


def test_unknown_provider_rejected():
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={"SERVICE_ENV": "development", "LLM_PROVIDER": "wat"})
    message = str(excinfo.value)
    assert "LLM_PROVIDER" in message
    assert "ollama" in message  # lists the valid options


def test_unknown_service_env_rejected():
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={"SERVICE_ENV": "prod"})  # must be 'production'
    assert "SERVICE_ENV" in str(excinfo.value)


def test_valid_env_produces_expected_typed_settings():
    settings = load_settings(
        env={
            "SERVICE_ENV": "staging",
            "LLM_PROVIDER": "openai",
            "PORT": "9000",
            "REQUEST_TIMEOUT_S": "12.5",
            "LOG_LEVEL": "debug",
        }
    )
    assert isinstance(settings, Settings)
    assert settings.service_env == "staging"
    assert settings.provider == "openai"
    assert settings.port == 9000
    assert settings.request_timeout_s == 12.5
    assert settings.log_level == "DEBUG"  # normalised to upper-case


def test_defaults_applied_when_optional_vars_absent():
    settings = load_settings(env={"SERVICE_ENV": "development"})
    assert settings.provider == "ollama"
    assert settings.port == 8000
    assert settings.request_timeout_s == 30.0
    assert settings.log_level == "INFO"
    assert settings.provider_api_key is None


def test_secret_is_not_exposed_by_repr():
    settings = load_settings(
        env={"SERVICE_ENV": "development", "PROVIDER_API_KEY": "top-secret-value"}
    )
    # SecretStr must hide the value in its string forms.
    assert "top-secret-value" not in repr(settings)
    assert settings.provider_api_key is not None
    assert settings.provider_api_key.get_secret_value() == "top-secret-value"
