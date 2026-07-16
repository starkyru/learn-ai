/**
 * Typed, fail-fast configuration.
 *
 * Everything is read from the environment and validated once. A missing or
 * malformed required variable throws a `ConfigError` with a readable,
 * variable-named message — the process refuses to start rather than failing
 * mid-request. `providerApiKey` is a representative secret: it is loaded here
 * but only ever surfaced through `redactConfig`, never logged raw.
 */

export type ServiceEnv = "development" | "staging" | "production";

export interface Config {
  serviceEnv: ServiceEnv;
  provider: string;
  chatModel?: string;
  port: number;
  dbPath: string;
  /** Directory of the numbered .sql migrations; undefined → the runner default. */
  migrationsDir?: string;
  /**
   * Reliability envelope (see reliability.ts). All enforced around the model
   * call in /ask: a per-request deadline that bounds total time across retries,
   * a cap on concurrent provider calls, a per-identity request-rate cap, a
   * bounded retry count for transient failures, and a circuit breaker that opens
   * after N consecutive provider failures and recovers after a cool-off.
   */
  requestTimeoutMs: number;
  providerMaxConcurrency: number;
  rateLimitPerMinute: number;
  providerMaxRetries: number;
  circuitFailureThreshold: number;
  circuitCooldownMs: number;
  providerApiKey?: string;
  logLevel: string;
}

/** Thrown at startup for missing/invalid configuration. */
export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

/**
 * Credential env vars that `@learn-ai/llm-core` reads DIRECTLY (bypassing this
 * config). We register any that are set with the log scrubber at startup so a
 * provider SDK error can never print one verbatim. (Ollama/LM Studio use dummy
 * non-secret keys, so they are intentionally absent.)
 */
export const PROVIDER_CREDENTIAL_ENV_VARS = [
  "OPENAI_API_KEY",
  "ANTHROPIC_API_KEY",
  "NVIDIA_API_KEY",
  "GEMINI_API_KEY",
] as const;

const KNOWN_PROVIDERS = new Set([
  "openai",
  "anthropic",
  "ollama",
  "nvidia",
  "lmstudio",
  "gemini",
]);
const KNOWN_ENVS = new Set(["development", "staging", "production"]);
const KNOWN_LOG_LEVELS = new Set(["debug", "info", "warning", "error"]);

type Env = Record<string, string | undefined>;

function parseIntField(
  raw: string | undefined,
  fallback: number,
  name: string,
  min: number,
  max: number,
  errors: string[],
): number {
  if (raw === undefined || raw === "") return fallback;
  // Reject "12abc" as well as "abc": Number() is too lenient, so match strictly.
  if (!/^-?\d+$/.test(raw.trim())) {
    errors.push(`${name} must be an integer, got "${raw}"`);
    return fallback;
  }
  const value = Number.parseInt(raw, 10);
  if (value < min || value > max) {
    errors.push(`${name} must be between ${min} and ${max}, got ${value}`);
    return fallback;
  }
  return value;
}

function parsePositiveFloat(
  raw: string | undefined,
  fallback: number,
  name: string,
  errors: string[],
): number {
  if (raw === undefined || raw === "") return fallback;
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    errors.push(`${name} must be a number greater than 0, got "${raw}"`);
    return fallback;
  }
  return value;
}

export function loadConfig(env: Env = process.env): Config {
  const errors: string[] = [];

  const serviceEnvRaw = env.SERVICE_ENV;
  if (serviceEnvRaw === undefined || serviceEnvRaw === "") {
    errors.push("SERVICE_ENV is required (development | staging | production)");
  } else if (!KNOWN_ENVS.has(serviceEnvRaw)) {
    errors.push(
      `SERVICE_ENV must be one of ${[...KNOWN_ENVS].join(" | ")}, got "${serviceEnvRaw}"`,
    );
  }

  const provider = env.LLM_PROVIDER ?? "ollama";
  if (!KNOWN_PROVIDERS.has(provider)) {
    errors.push(
      `LLM_PROVIDER must be one of ${[...KNOWN_PROVIDERS].join(" | ")}, got "${provider}"`,
    );
  }

  const port = parseIntField(env.PORT, 8001, "PORT", 1, 65535, errors);
  const requestTimeoutMs = parsePositiveFloat(
    env.REQUEST_TIMEOUT_MS,
    30000,
    "REQUEST_TIMEOUT_MS",
    errors,
  );
  const providerMaxConcurrency = parseIntField(
    env.PROVIDER_MAX_CONCURRENCY,
    8,
    "PROVIDER_MAX_CONCURRENCY",
    1,
    1_000_000,
    errors,
  );
  const rateLimitPerMinute = parseIntField(
    env.RATE_LIMIT_PER_MINUTE,
    60,
    "RATE_LIMIT_PER_MINUTE",
    1,
    1_000_000,
    errors,
  );
  const providerMaxRetries = parseIntField(
    env.PROVIDER_MAX_RETRIES,
    2,
    "PROVIDER_MAX_RETRIES",
    0,
    100,
    errors,
  );
  const circuitFailureThreshold = parseIntField(
    env.CIRCUIT_FAILURE_THRESHOLD,
    5,
    "CIRCUIT_FAILURE_THRESHOLD",
    1,
    1_000_000,
    errors,
  );
  const circuitCooldownMs = parsePositiveFloat(
    env.CIRCUIT_COOLDOWN_MS,
    30000,
    "CIRCUIT_COOLDOWN_MS",
    errors,
  );

  const logLevel = (env.LOG_LEVEL ?? "info").toLowerCase();
  if (!KNOWN_LOG_LEVELS.has(logLevel)) {
    errors.push(
      `LOG_LEVEL must be one of ${[...KNOWN_LOG_LEVELS].join(" | ")}, got "${logLevel}"`,
    );
  }

  if (errors.length > 0) {
    throw new ConfigError(
      "Invalid service configuration:\n" + errors.map((e) => `  - ${e}`).join("\n"),
    );
  }

  return {
    serviceEnv: serviceEnvRaw as ServiceEnv,
    provider,
    chatModel: env.CHAT_MODEL || undefined,
    port,
    dbPath: env.DB_PATH ?? "data/07b-service.sqlite",
    migrationsDir: env.MIGRATIONS_DIR || undefined,
    requestTimeoutMs,
    providerMaxConcurrency,
    rateLimitPerMinute,
    providerMaxRetries,
    circuitFailureThreshold,
    circuitCooldownMs,
    providerApiKey: env.PROVIDER_API_KEY || undefined,
    logLevel,
  };
}

/** A log-safe view of the config: the secret is masked. */
export function redactConfig(config: Config): Record<string, unknown> {
  return {
    serviceEnv: config.serviceEnv,
    provider: config.provider,
    chatModel: config.chatModel ?? null,
    port: config.port,
    dbPath: config.dbPath,
    migrationsDir: config.migrationsDir ?? null,
    requestTimeoutMs: config.requestTimeoutMs,
    providerMaxConcurrency: config.providerMaxConcurrency,
    rateLimitPerMinute: config.rateLimitPerMinute,
    providerMaxRetries: config.providerMaxRetries,
    circuitFailureThreshold: config.circuitFailureThreshold,
    circuitCooldownMs: config.circuitCooldownMs,
    logLevel: config.logLevel,
    providerApiKey: config.providerApiKey ? "[REDACTED]" : null,
  };
}
