"""Direct unit tests for the log-redaction primitives.

These exercise the redaction logic in isolation (not just the end-to-end
service log), covering nested dicts, case variants, and the exception-traceback
path that the key-based ``_redact`` cannot reach on its own.
"""

from __future__ import annotations

import io

from m07b_service.logging_setup import (
    _redact,
    _scrub_secrets,
    clear_secrets,
    configure_logging,
    register_provider_credentials,
    register_secret,
)


def test_redact_masks_credential_keys_case_insensitively():
    result = _redact({"API_KEY": "abc", "Authorization": "Bearer x", "safe": 1})
    assert result == {
        "API_KEY": "[REDACTED]",
        "Authorization": "[REDACTED]",
        "safe": 1,
    }


def test_redact_recurses_into_nested_mappings():
    result = _redact({"outer": {"token": "t", "keep": "v"}, "count": 2})
    assert result == {"outer": {"token": "[REDACTED]", "keep": "v"}, "count": 2}


def test_redact_recurses_into_arrays():
    # A credential key nested inside a list must still be masked.
    result = _redact({"items": [{"api_key": "x", "keep": 1}, {"api_key": "y"}], "n": 2})
    assert result == {
        "items": [{"api_key": "[REDACTED]", "keep": 1}, {"api_key": "[REDACTED]"}],
        "n": 2,
    }


def test_redact_leaves_non_credential_fields_untouched():
    result = _redact({"provider": "ollama", "port": 8000})
    assert result == {"provider": "ollama", "port": 8000}


def test_scrub_replaces_registered_secret_substring():
    clear_secrets()
    register_secret("hunter2-secret")
    try:
        assert _scrub_secrets("before hunter2-secret after") == "before [REDACTED] after"
        # An unregistered value is left alone.
        assert _scrub_secrets("nothing here") == "nothing here"
    finally:
        clear_secrets()


def test_register_provider_credentials_scrubs_env_key():
    # A provider credential that llm_core reads directly from the env must be
    # registered so a later log line containing it is scrubbed.
    clear_secrets()
    try:
        register_provider_credentials(env={"OPENAI_API_KEY": "env-openai-key-abc"})
        assert _scrub_secrets("upstream said env-openai-key-abc") == "upstream said [REDACTED]"
    finally:
        clear_secrets()


def test_exception_traceback_is_scrubbed_of_registered_secret():
    buffer = io.StringIO()
    # configure_logging clears the registry, so register AFTER it.
    logger = configure_logging("INFO", stream=buffer)
    register_secret("tb-secret-xyz")
    try:
        try:
            raise ValueError("boom with tb-secret-xyz embedded")
        except ValueError:
            logger.exception("handler failed")
        output = buffer.getvalue()
        assert "tb-secret-xyz" not in output  # scrubbed from the traceback text
        assert "[REDACTED]" in output
        assert "handler failed" in output
    finally:
        clear_secrets()
