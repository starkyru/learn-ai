/** Fail-fast configuration validation. */

import { ConfigError, loadConfig } from "../src/config.js";

test("a missing SERVICE_ENV fails fast with a named error", () => {
  expect(() => loadConfig({})).toThrow(ConfigError);
  expect(() => loadConfig({})).toThrow(/SERVICE_ENV/);
});

test("an invalid PORT reports PORT, not a generic error", () => {
  expect(() =>
    loadConfig({ SERVICE_ENV: "development", PORT: "not-a-number" }),
  ).toThrow(/PORT/);
});

test("an unknown provider is rejected and the options are listed", () => {
  expect(() => loadConfig({ SERVICE_ENV: "development", LLM_PROVIDER: "wat" })).toThrow(
    /LLM_PROVIDER.*ollama/s,
  );
});

test("an unknown service env is rejected", () => {
  expect(() => loadConfig({ SERVICE_ENV: "prod" })).toThrow(/SERVICE_ENV/);
});

test("a valid environment produces the expected typed config", () => {
  const config = loadConfig({
    SERVICE_ENV: "staging",
    LLM_PROVIDER: "openai",
    PORT: "9000",
    REQUEST_TIMEOUT_MS: "12500",
    LOG_LEVEL: "DEBUG",
  });
  expect(config.serviceEnv).toBe("staging");
  expect(config.provider).toBe("openai");
  expect(config.port).toBe(9000);
  expect(config.requestTimeoutMs).toBe(12500);
  expect(config.logLevel).toBe("debug"); // normalised to lower-case
});

test("defaults are applied when optional variables are absent", () => {
  const config = loadConfig({ SERVICE_ENV: "development" });
  expect(config.provider).toBe("ollama");
  expect(config.port).toBe(8001);
  expect(config.requestTimeoutMs).toBe(30000);
  expect(config.logLevel).toBe("info");
  expect(config.providerApiKey).toBeUndefined();
});
