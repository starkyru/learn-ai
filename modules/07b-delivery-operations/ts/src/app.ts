/**
 * Fastify application factory.
 *
 * `buildApp` takes its `Config`, and optionally a provider and a log sink, so
 * tests inject a deterministic fake provider and capture logs. `bootstrap`
 * wraps it for production, eagerly resolving the provider so a missing
 * credential fails fast at startup (see `server.ts`).
 *
 * Protected routes (`/ask`, and the operator-only `/documents`) run an auth
 * `preValidation` hook (see `auth.ts`) that resolves the bearer token to a
 * `Principal` and enforces RBAC BEFORE body validation and the handler;
 * retrieval is tenant-scoped (`retrieval.ts`).
 */

import { randomUUID } from "node:crypto";

import Fastify, {
  type FastifyError,
  type FastifyInstance,
  type FastifyReply,
  type FastifyRequest,
} from "fastify";

import type { LLMProvider } from "@learn-ai/llm-core";

import {
  hasRole,
  lookupPrincipal,
  parseBearerToken,
  type Principal,
  recordAudit,
} from "./auth.js";
import { type Config, PROVIDER_CREDENTIAL_ENV_VARS, redactConfig } from "./config.js";
import { enqueue, getJob } from "./jobs.js";
import { createLogger, type LogSink } from "./logging.js";
import { checkReady } from "./migrations.js";
import { buildDefaultProvider } from "./provider.js";
import { buildEnvelope, ReliabilityEnvelope, ReliabilityError } from "./reliability.js";
import { createDocument, documentExists, retrieve } from "./retrieval.js";

// The authenticated caller is attached to the request by the auth preHandler.
declare module "fastify" {
  interface FastifyRequest {
    principal?: Principal;
  }
}

const REQUEST_ID_HEADER = "x-request-id";

// Bound the request surface: cap the body size (Fastify's default is 1 MB) and
// the question length so a single request cannot exhaust memory or the model.
const MAX_BODY_BYTES = 64 * 1024;
const MAX_QUESTION_CHARS = 4000;
const MAX_TITLE_CHARS = 200;

const SYSTEM_PROMPT =
  "You are the Module 07b reference assistant. Answer the user's question clearly and concisely.";

/** Build an Error carrying a `statusCode` the sanitising error handler maps. */
function httpError(statusCode: number): Error {
  const err = new Error(`http_${statusCode}`);
  (err as Error & { statusCode: number }).statusCode = statusCode;
  return err;
}

/** A stable action label for the audit trail — method + route path, never the body. */
function auditAction(req: FastifyRequest): string {
  const path = req.routeOptions?.url ?? req.url.split("?")[0];
  return `${req.method} ${path}`;
}

export interface BuildOptions {
  config: Config;
  /** Inject a fake provider in tests; omitted → the real llm-core provider. */
  provider?: LLMProvider;
  /** Inject an envelope with small limits or a fake clock in tests. */
  reliability?: ReliabilityEnvelope;
  /** Capture logs in tests; omitted → stdout. */
  logSink?: LogSink;
}

export function buildApp(options: BuildOptions): FastifyInstance {
  const { config } = options;
  const logger = createLogger({ level: config.logLevel, sink: options.logSink });

  // The reliability envelope (deadline, concurrency, rate limit, retry, circuit
  // breaker) wraps every model call. Tests may inject one with small limits or a
  // fake clock; otherwise it is built from the config.
  const reliability = options.reliability ?? buildEnvelope(config);

  // A provider slot resolved lazily: injected fake in tests, real one otherwise.
  // Async because the real client is loaded on demand (see provider.ts).
  // In production `bootstrap` injects an eagerly-built provider, so this lazy
  // path (and its build) only runs on the default-provider dev route.
  let provider = options.provider;
  const resolveProvider = async (): Promise<LLMProvider> => {
    if (!provider) provider = await buildDefaultProvider(config);
    return provider;
  };

  // Resolve the bearer token to a Principal or reject with 401 — auditing the
  // unauthenticated deny. Runs BEFORE any retrieval / tool execution.
  const authenticate = (req: FastifyRequest): Principal => {
    const token = parseBearerToken(req.headers.authorization);
    const principal = token ? lookupPrincipal(config.dbPath, token) : null;
    if (!principal) {
      recordAudit(config.dbPath, {
        actor: null,
        tenantId: null,
        action: auditAction(req),
        decision: "deny",
        requestId: req.id,
      });
      throw httpError(401);
    }
    return principal;
  };

  // A preValidation hook that authenticates and (optionally) enforces a role.
  // preValidation runs AFTER the body-size cap (413) but BEFORE schema validation
  // (400) and the handler — so auth gates BOTH validation and the privileged
  // action, and this mirrors the Python order exactly (413 pre-auth via
  // middleware; 401/403 before the 422 body check).
  const requireAuth =
    (requiredRole?: string) =>
    async (req: FastifyRequest): Promise<void> => {
      const principal = authenticate(req);
      if (requiredRole && !hasRole(principal, requiredRole)) {
        recordAudit(config.dbPath, {
          actor: principal.userId,
          tenantId: principal.tenantId,
          action: auditAction(req),
          decision: "deny",
          requestId: req.id,
        });
        throw httpError(403);
      }
      req.principal = principal;
    };

  const app = Fastify({
    logger: false,
    // Reject an oversized body with 413 before it is buffered/parsed.
    bodyLimit: MAX_BODY_BYTES,
    // Reject unknown body fields (400) instead of Fastify's default of silently
    // stripping them — parity with the Python model's extra="forbid".
    ajv: { customOptions: { removeAdditional: false } },
    // Always mint the correlation id ourselves: reuse an inbound X-Request-Id
    // if present, else generate one. `requestIdHeader: false` stops Fastify from
    // reading its own default header so genReqId is authoritative.
    requestIdHeader: false,
    genReqId(req) {
      const inbound = req.headers[REQUEST_ID_HEADER];
      return typeof inbound === "string" && inbound.length > 0 ? inbound : randomUUID();
    },
  });

  // Register secrets so they are scrubbed from every log line: the service's own
  // configured secret AND the provider credentials llm-core reads directly from
  // the environment. Then log the redacted config — which never emits them.
  logger.registerSecret(config.providerApiKey);
  for (const name of PROVIDER_CREDENTIAL_ENV_VARS)
    logger.registerSecret(process.env[name]);
  logger.info("service_configured", redactConfig(config));

  // Sanitising error handler: never leak a provider error message or the raw
  // request body to the client. Log the real detail via the scrubbing logger and
  // return a generic message + request id.
  app.setErrorHandler((err: FastifyError, req, reply) => {
    const statusCode =
      typeof err.statusCode === "number" &&
      err.statusCode >= 400 &&
      err.statusCode < 600
        ? err.statusCode
        : 500;
    logger.error("request_error", {
      request_id: req.id,
      status: statusCode,
      code: err.code,
      // Scrubbed by the logger; a validation error's field paths carry no values.
      error: err.message,
    });
    // A generic, status-appropriate message — never a raw detail. 401 vs 403 is
    // surfaced distinctly (both by status code AND message) so the two are clear.
    let publicMessage: string;
    if (statusCode === 401) publicMessage = "unauthorized";
    else if (statusCode === 403) publicMessage = "forbidden";
    else if (statusCode >= 500) publicMessage = "internal server error";
    else publicMessage = "bad request";
    reply.code(statusCode).send({ error: publicMessage, request_id: req.id });
  });

  // Echo the correlation id back to the caller on every response.
  app.addHook("onSend", async (req, reply, payload) => {
    reply.header(REQUEST_ID_HEADER, req.id);
    return payload;
  });

  app.addHook("onResponse", async (req, reply) => {
    logger.info("request_completed", {
      request_id: req.id,
      method: req.method,
      path: req.url,
      status: reply.statusCode,
      duration_ms: Math.round(reply.elapsedTime),
    });
  });

  // Liveness: if the process can answer, it is alive. No dependencies.
  app.get("/healthz", async () => ({ status: "ok" }));

  // Readiness reflects the real, MIGRATED, WRITABLE database (versions + column
  // fingerprint + write probe), not just that the file opens.
  app.get("/readyz", async (_req, reply) => {
    const dbOk = checkReady(config.dbPath, config.migrationsDir);
    const checks = { db: dbOk ? "ok" : "error" };
    if (dbOk) return { status: "ready", checks };
    reply.code(503);
    return { status: "not_ready", checks };
  });

  app.post<{ Body: { question: string } }>(
    "/ask",
    {
      // Authenticate (any signed-in user) BEFORE validation + the handler, so
      // retrieval / generation never runs for an unauthenticated caller.
      preValidation: requireAuth(),
      schema: {
        body: {
          type: "object",
          required: ["question"],
          additionalProperties: false,
          properties: {
            question: { type: "string", minLength: 1, maxLength: MAX_QUESTION_CHARS },
          },
        },
      },
    },
    async (req) => {
      const principal = req.principal!;
      const { question } = req.body;
      // Tenant-scoped retrieval: the `tenant_id = ?` filter is IN THE QUERY, so
      // only the caller's tenant's chunks are ever fetched — never after.
      const chunks = retrieve(config.dbPath, principal.tenantId, question);
      const context = chunks.map((chunk) => chunk.content).join("\n\n");
      const systemPrompt = context
        ? `${SYSTEM_PROMPT}\n\nContext:\n${context}`
        : SYSTEM_PROMPT;

      const activeProvider = await resolveProvider();
      // The model call runs inside the reliability envelope, keyed per identity.
      // A bounded failure (rate/circuit/concurrency/deadline/provider) maps to its
      // HTTP status; the error handler returns a generic message (never a raw
      // provider detail), so the response stays safe and bounded.
      let result;
      try {
        result = await reliability.call(
          () =>
            activeProvider.chat(
              [
                { role: "system", content: systemPrompt },
                { role: "user", content: question },
              ],
              { temperature: 0, maxTokens: 512, model: config.chatModel },
            ),
          principal.userId,
        );
      } catch (err) {
        if (err instanceof ReliabilityError) {
          // Log the failure MODE (not the raw cause, which could carry a
          // credential); then surface the bounded status.
          logger.info("provider_call_failed", {
            request_id: req.id,
            reason: err.reason,
          });
          throw httpError(err.status);
        }
        throw err;
      }

      recordAudit(config.dbPath, {
        actor: principal.userId,
        tenantId: principal.tenantId,
        action: auditAction(req),
        decision: "allow",
        requestId: req.id,
      });
      return { answer: result.text, request_id: req.id };
    },
  );

  // Operator-only privileged write: create a document in the CALLER'S tenant.
  app.post<{ Body: { title: string } }>(
    "/documents",
    {
      // require_operator: a viewer (or unauthenticated caller) is rejected with
      // 403 / 401 BEFORE this write runs — the role check gates the action.
      preValidation: requireAuth("operator"),
      schema: {
        body: {
          type: "object",
          required: ["title"],
          additionalProperties: false,
          properties: {
            title: { type: "string", minLength: 1, maxLength: MAX_TITLE_CHARS },
          },
        },
      },
    },
    async (req: FastifyRequest<{ Body: { title: string } }>, reply: FastifyReply) => {
      const principal = req.principal!;
      const id = createDocument(config.dbPath, {
        tenantId: principal.tenantId,
        title: req.body.title,
      });
      recordAudit(config.dbPath, {
        actor: principal.userId,
        tenantId: principal.tenantId,
        action: auditAction(req),
        decision: "allow",
        requestId: req.id,
      });
      reply.code(201);
      return { id, request_id: req.id };
    },
  );

  // Operator-only: enqueue a DURABLE indexing job for a document in the caller's
  // tenant. The slow work runs in the background worker, not here, so the request
  // returns at once. An `Idempotency-Key` header makes the enqueue idempotent — a
  // retried client request produces one job / one effect (202 first, 200 replay).
  app.post<{ Body: { document_id: string } }>(
    "/jobs",
    {
      preValidation: requireAuth("operator"),
      schema: {
        body: {
          type: "object",
          required: ["document_id"],
          additionalProperties: false,
          properties: {
            document_id: { type: "string", minLength: 1, maxLength: MAX_TITLE_CHARS },
          },
        },
      },
    },
    async (
      req: FastifyRequest<{ Body: { document_id: string } }>,
      reply: FastifyReply,
    ) => {
      const principal = req.principal!;
      const documentId = req.body.document_id;
      // Missing OR another tenant's document — a clean 404, not an FK 500.
      if (!documentExists(config.dbPath, principal.tenantId, documentId)) {
        throw httpError(404);
      }
      const header = req.headers["idempotency-key"];
      const idempotencyKey =
        typeof header === "string" && header.length > 0 ? header : null;
      const result = enqueue(config.dbPath, {
        tenantId: principal.tenantId,
        documentId,
        idempotencyKey,
      });
      recordAudit(config.dbPath, {
        actor: principal.userId,
        tenantId: principal.tenantId,
        action: auditAction(req),
        decision: "allow",
        requestId: req.id,
      });
      // Report the job's CURRENT status (a replay may already be processed).
      const job = getJob(config.dbPath, principal.tenantId, result.jobId);
      reply.code(result.created ? 202 : 200);
      return {
        job_id: result.jobId,
        status: job?.status ?? "pending",
        request_id: req.id,
      };
    },
  );

  // Any authenticated caller may inspect a job — but only IN THEIR tenant:
  // getJob filters by tenant_id, so another tenant's job id is a 404, never a
  // cross-tenant status leak.
  app.get<{ Params: { jobId: string } }>(
    "/jobs/:jobId",
    { preValidation: requireAuth() },
    async (req: FastifyRequest<{ Params: { jobId: string } }>) => {
      const principal = req.principal!;
      const job = getJob(config.dbPath, principal.tenantId, req.params.jobId);
      if (job === null) throw httpError(404);
      return {
        id: job.id,
        document_id: job.documentId,
        status: job.status,
        retries: job.retries,
        max_retries: job.maxRetries,
        request_id: req.id,
      };
    },
  );

  return app;
}

export interface BootstrapOptions {
  config: Config;
  /** Inject a provider (tests) to skip the eager build. */
  provider?: LLMProvider;
  logSink?: LogSink;
  /** Override the provider builder (tests assert fail-fast without a network). */
  providerFactory?: (config: Config) => Promise<LLMProvider>;
}

/**
 * Build the app for production, eagerly resolving the provider.
 *
 * Building the provider now means a missing/invalid provider credential fails
 * fast at startup — before the port is bound — rather than 500-ing on the first
 * `/ask`. It also removes the lazy first-request build. When a provider is
 * injected (tests), the factory is skipped entirely.
 */
export async function bootstrap(options: BootstrapOptions): Promise<FastifyInstance> {
  const factory = options.providerFactory ?? buildDefaultProvider;
  const provider = options.provider ?? (await factory(options.config));
  return buildApp({ config: options.config, provider, logSink: options.logSink });
}
