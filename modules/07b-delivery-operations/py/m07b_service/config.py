"""Typed, fail-fast configuration.

The whole service is configured from environment variables — nothing is read
from a file at runtime and no secret is compiled into the image. We validate
*once, at startup*: a missing or malformed required variable raises a clear
:class:`ConfigError` before the process starts serving, rather than surfacing as
a 500 in the middle of a request.

``provider_api_key`` is stored as a pydantic ``SecretStr`` so it never leaks
through ``repr()``/``str()`` or an accidental log of the config object.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, SecretStr, ValidationError, field_validator

# The providers ``llm_core.get_provider`` understands. We validate against this
# set here so a typo fails at startup instead of deep inside a request.
KNOWN_PROVIDERS = frozenset({"openai", "anthropic", "ollama", "nvidia", "lmstudio", "gemini"})
KNOWN_ENVS = frozenset({"development", "staging", "production"})
KNOWN_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR"})

# Credential env vars that llm_core reads DIRECTLY (bypassing our Settings). We
# register any that are set with the log scrubber at startup so a provider SDK
# error or log line can never print one verbatim. (Ollama/LM Studio use dummy
# non-secret keys, so they are intentionally absent.)
PROVIDER_CREDENTIAL_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "NVIDIA_API_KEY",
    "GEMINI_API_KEY",
)

# Maps the public env-var name to the Settings field it populates. Keeping this
# explicit (rather than magic prefixing) makes the .env.example self-documenting.
_ENV_TO_FIELD: dict[str, str] = {
    "SERVICE_ENV": "service_env",
    "LLM_PROVIDER": "provider",
    "CHAT_MODEL": "chat_model",
    "PORT": "port",
    "DB_PATH": "db_path",
    "MIGRATIONS_DIR": "migrations_dir",
    "REQUEST_TIMEOUT_S": "request_timeout_s",
    "PROVIDER_MAX_CONCURRENCY": "provider_max_concurrency",
    "RATE_LIMIT_PER_MINUTE": "rate_limit_per_minute",
    "PROVIDER_MAX_RETRIES": "provider_max_retries",
    "CIRCUIT_FAILURE_THRESHOLD": "circuit_failure_threshold",
    "CIRCUIT_COOLDOWN_S": "circuit_cooldown_s",
    "PROVIDER_API_KEY": "provider_api_key",
    "LOG_LEVEL": "log_level",
}
_FIELD_TO_ENV: dict[str, str] = {field: env for env, field in _ENV_TO_FIELD.items()}


class ConfigError(RuntimeError):
    """Raised at startup when configuration is missing or invalid.

    Carrying a readable, aggregated message is the point: operators should see
    *which* variable is wrong, not a pydantic traceback.
    """


class Settings(BaseModel):
    """Validated runtime configuration. Immutable once built."""

    model_config = {"frozen": True}

    # Required, no default: declaring which environment you are deploying to is
    # an operational decision, not something to guess.
    service_env: str

    provider: str = "ollama"
    chat_model: str | None = None
    port: int = 8000
    db_path: str = "data/07b-service.sqlite"
    # Directory of the numbered .sql migrations. None → the runner's default
    # (module-relative, or the MIGRATIONS_DIR env var).
    migrations_dir: str | None = None
    # Reliability envelope (see reliability.py). All enforced around the model
    # call in /ask: a per-request deadline that bounds total time across retries,
    # a cap on concurrent provider calls, a per-identity request-rate cap, a
    # bounded retry count for transient failures, and a circuit breaker that
    # opens after N consecutive provider failures and recovers after a cool-off.
    request_timeout_s: float = 30.0
    provider_max_concurrency: int = 8
    rate_limit_per_minute: int = 60
    provider_max_retries: int = 2
    circuit_failure_threshold: int = 5
    circuit_cooldown_s: float = 30.0
    provider_api_key: SecretStr | None = None
    log_level: str = "INFO"

    @field_validator("service_env")
    @classmethod
    def _check_env(cls, value: str) -> str:
        if value not in KNOWN_ENVS:
            raise ValueError(f"must be one of {sorted(KNOWN_ENVS)}, got {value!r}")
        return value

    @field_validator("provider")
    @classmethod
    def _check_provider(cls, value: str) -> str:
        if value not in KNOWN_PROVIDERS:
            raise ValueError(f"must be one of {sorted(KNOWN_PROVIDERS)}, got {value!r}")
        return value

    @field_validator("port")
    @classmethod
    def _check_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError(f"must be between 1 and 65535, got {value}")
        return value

    @field_validator("request_timeout_s", "circuit_cooldown_s")
    @classmethod
    def _check_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(f"must be greater than 0, got {value}")
        return value

    @field_validator(
        "provider_max_concurrency", "rate_limit_per_minute", "circuit_failure_threshold"
    )
    @classmethod
    def _check_positive_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError(f"must be at least 1, got {value}")
        return value

    @field_validator("provider_max_retries")
    @classmethod
    def _check_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError(f"must be 0 or greater, got {value}")
        return value

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in KNOWN_LOG_LEVELS:
            raise ValueError(f"must be one of {sorted(KNOWN_LOG_LEVELS)}, got {value!r}")
        return upper

    def redacted_summary(self) -> dict[str, object]:
        """A log-safe view of the config.

        The secret is emitted as ``"[REDACTED]"`` / ``None`` and is NEVER
        extracted here — mirroring the TypeScript ``redactConfig``. This is what
        the app logs at startup, so the raw credential cannot leak even if the
        key-based redaction in ``logging_setup`` is bypassed.
        """
        return {
            "service_env": self.service_env,
            "provider": self.provider,
            "chat_model": self.chat_model,
            "port": self.port,
            "db_path": self.db_path,
            "migrations_dir": self.migrations_dir,
            "request_timeout_s": self.request_timeout_s,
            "provider_max_concurrency": self.provider_max_concurrency,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "provider_max_retries": self.provider_max_retries,
            "circuit_failure_threshold": self.circuit_failure_threshold,
            "circuit_cooldown_s": self.circuit_cooldown_s,
            "log_level": self.log_level,
            "provider_api_key": "[REDACTED]" if self.provider_api_key is not None else None,
        }


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from an environment mapping (defaults to os.environ).

    Accepting an explicit mapping keeps this pure and testable — tests never have
    to mutate the real process environment. Any validation failure is re-raised
    as :class:`ConfigError` with a single, readable, env-var-named message.
    """
    import os

    source: Mapping[str, str] = os.environ if env is None else env

    kwargs: dict[str, str] = {}
    for env_name, field in _ENV_TO_FIELD.items():
        if env_name in source and source[env_name] != "":
            kwargs[field] = source[env_name]

    try:
        return Settings(**kwargs)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ConfigError(_format_errors(exc)) from exc


def _format_errors(exc: ValidationError) -> str:
    """Turn a pydantic ValidationError into an operator-friendly message."""
    lines = ["Invalid service configuration:"]
    for err in exc.errors():
        field = str(err["loc"][0]) if err["loc"] else "?"
        env_name = _FIELD_TO_ENV.get(field, field.upper())
        message = err["msg"]
        if err["type"] == "missing":
            message = "is required but was not set"
        lines.append(f"  - {env_name}: {message}")
    return "\n".join(lines)
