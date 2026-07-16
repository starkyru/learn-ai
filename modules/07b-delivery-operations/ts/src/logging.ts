/**
 * Structured (JSON) logging with secret redaction.
 *
 * Each call serialises one JSON line to an injectable sink (stdout by default,
 * an in-memory buffer in tests). Three safeguards keep credentials out:
 *
 * 1. The app logs `redactConfig(config)`, which never emits the raw secret.
 * 2. Every field passes through `redact`, so a credential-shaped key
 *    (`authorization`, `api_key`, `token`, …) is masked even if handed to the
 *    logger by mistake.
 * 3. As a final net, every emitted line is scrubbed of any *registered* secret
 *    substring (`logger.registerSecret`). This catches a secret that leaked into
 *    a free-text `msg` — which `redact` (field VALUES only) cannot reach.
 *
 * IMPORTANT: never interpolate a secret into the `msg` string. `redact` does not
 * see `msg`; only the registered-secret scrub does, and only for values you
 * actually registered. Prefer structured fields with credential-shaped names.
 *
 * The correlation id is passed explicitly per call as `request_id` (Fastify
 * threads it from the request).
 */

export interface LogSink {
  write(chunk: string): void;
}

export type LogFields = Record<string, unknown>;

export interface Logger {
  info(msg: string, fields?: LogFields): void;
  error(msg: string, fields?: LogFields): void;
  /** Register a secret so it is scrubbed from every future emitted line. */
  registerSecret(value: string | undefined | null): void;
}

const REDACT_KEYS = new Set([
  "authorization",
  "api_key",
  "apikey",
  "provider_api_key",
  "providerapikey",
  "password",
  "secret",
  "token",
  "x-api-key",
]);
const REDACTED = "[REDACTED]";

function redact(fields: LogFields): LogFields {
  const out: LogFields = {};
  for (const [key, value] of Object.entries(fields)) {
    out[key] = REDACT_KEYS.has(key.toLowerCase()) ? REDACTED : redactValue(value);
  }
  return out;
}

function redactValue(value: unknown): unknown {
  // Recurse through arrays AND objects so a credential nested in a list — e.g.
  // {items: [{api_key: "..."}]} — is still masked.
  if (Array.isArray(value)) return value.map(redactValue);
  if (value && typeof value === "object") return redact(value as LogFields);
  return value;
}

export function createLogger(options: { level?: string; sink?: LogSink } = {}): Logger {
  const sink: LogSink = options.sink ?? process.stdout;
  // Per-logger secret registry: no global state, so tests never bleed secrets
  // into one another.
  const secrets = new Set<string>();

  function scrub(line: string): string {
    let out = line;
    for (const secret of secrets) {
      if (out.includes(secret)) out = out.split(secret).join(REDACTED);
    }
    return out;
  }

  function emit(level: string, msg: string, fields?: LogFields): void {
    const record = {
      ts: new Date().toISOString(),
      level,
      msg,
      ...redact(fields ?? {}),
    };
    sink.write(scrub(JSON.stringify(record)) + "\n");
  }

  return {
    info: (msg, fields) => emit("info", msg, fields),
    error: (msg, fields) => emit("error", msg, fields),
    registerSecret: (value) => {
      if (value) secrets.add(value);
    },
  };
}
