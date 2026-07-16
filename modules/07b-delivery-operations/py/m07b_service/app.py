"""FastAPI application factory.

``create_app`` takes its :class:`Settings`, and optionally a provider and a log
stream, so tests can inject a deterministic fake provider and capture logs.
``bootstrap`` wraps it for production: it eagerly resolves the provider so a
missing credential fails fast at startup (see :mod:`m07b_service.asgi`).

Protected routes (``/ask``, and the operator-only ``/documents``) depend on the
``authenticate`` / ``require_operator`` dependencies (see
:mod:`m07b_service.auth`), which resolve the bearer token to a
:class:`~m07b_service.auth.Principal` and enforce RBAC BEFORE the handler runs;
retrieval is tenant-scoped (see :mod:`m07b_service.retrieval`).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, TextIO
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from llm_core import ChatMessage, ChatOptions, LLMProvider
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .auth import (
    Principal,
    has_role,
    lookup_principal,
    parse_bearer_token,
    record_audit,
)
from .config import Settings, load_settings
from .jobs import JobWorker, enqueue, get_job, index_document
from .logging_setup import (
    configure_logging,
    log_event,
    register_provider_credentials,
    register_secret,
    request_id_var,
)
from .migrations import apply_pending, check_ready
from .provider import build_default_provider
from .reliability import ReliabilityEnvelope, ReliabilityError, build_envelope
from .retrieval import create_document, document_exists, retrieve


class StartupError(RuntimeError):
    """Generic startup failure — carries NO original detail (which could hold a
    credential). The real, scrubbed detail is in the ``startup_failed`` log."""


REQUEST_ID_HEADER = "X-Request-Id"

# Bound the request surface: reject an oversized body before it is parsed, and
# cap the question length. FastAPI/Starlette impose no default body-size limit.
_MAX_BODY_BYTES = 64 * 1024
_MAX_QUESTION_CHARS = 4000

_SYSTEM_PROMPT = (
    "You are the Module 07b reference assistant. Answer the user's question clearly and concisely."
)


class AskRequest(BaseModel):
    """Body for ``POST /ask``.

    ``extra="forbid"`` rejects unknown keys (parity with the TypeScript Fastify
    schema's ``additionalProperties: false``). Note the empty/oversized-question
    case returns 422 here vs 400 on the TS side — each is its framework's
    idiomatic validation-failure status.
    """

    model_config = {"extra": "forbid"}

    question: str = Field(min_length=1, max_length=_MAX_QUESTION_CHARS)


class AskResponse(BaseModel):
    answer: str
    request_id: str


class CreateDocumentRequest(BaseModel):
    """Body for the operator-only ``POST /documents``."""

    model_config = {"extra": "forbid"}

    title: str = Field(min_length=1, max_length=200)


class CreateDocumentResponse(BaseModel):
    id: str
    request_id: str


class EnqueueJobRequest(BaseModel):
    """Body for the operator-only ``POST /jobs`` (enqueue an ingestion job)."""

    model_config = {"extra": "forbid"}

    document_id: str = Field(min_length=1, max_length=200)


class EnqueueJobResponse(BaseModel):
    job_id: str
    status: str
    request_id: str


class JobStatusResponse(BaseModel):
    id: str
    document_id: str | None
    status: str
    retries: int
    max_retries: int
    request_id: str


# The optional idempotency header on ``POST /jobs``: repeating a request with the
# same value enqueues the work once (see :func:`m07b_service.jobs.enqueue`).
_IDEMPOTENCY_HEADER = "Idempotency-Key"


# Dependencies live at module scope (not inside create_app) so FastAPI can
# resolve them when evaluating the ``Annotated[..., Depends(...)]`` hints under
# ``from __future__ import annotations``. They read everything they need from
# ``request.app.state``, so no closure is required.
def get_service_provider(request: Request) -> LLMProvider:
    prov = request.app.state.provider
    if prov is None:
        prov = build_default_provider(request.app.state.settings)
        request.app.state.provider = prov
    return prov


def _audit_action(request: Request) -> str:
    """A stable action label for the audit trail — the method + path, never the body."""
    return f"{request.method} {request.url.path}"


def _request_id_of(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def authenticate(request: Request) -> Principal:
    """Resolve the bearer token to a Principal, or reject with 401.

    A missing/invalid token is audited (as an unauthenticated deny) and returns
    401 — BEFORE any retrieval or tool execution runs.
    """
    settings = request.app.state.settings
    token = parse_bearer_token(request.headers.get("authorization"))
    principal = lookup_principal(settings.db_path, token) if token else None
    if principal is None:
        record_audit(
            settings.db_path,
            actor=None,
            tenant_id=None,
            action=_audit_action(request),
            decision="deny",
            request_id=_request_id_of(request),
        )
        raise HTTPException(status_code=401)
    return principal


def require_operator(
    request: Request, principal: Annotated[Principal, Depends(authenticate)]
) -> Principal:
    """Require the ``operator`` role, else audit the deny and return 403."""
    if not has_role(principal, "operator"):
        settings = request.app.state.settings
        record_audit(
            settings.db_path,
            actor=principal.user_id,
            tenant_id=principal.tenant_id,
            action=_audit_action(request),
            decision="deny",
            request_id=_request_id_of(request),
        )
        raise HTTPException(status_code=403)
    return principal


class BodySizeLimitMiddleware:
    """Reject a request whose body exceeds ``max_bytes`` with 413.

    Unlike a ``Content-Length`` header check, this counts bytes as it consumes
    the ASGI ``receive`` stream, so a chunked / HTTP-2 request that omits
    ``Content-Length`` cannot bypass the cap. The (bounded) body is buffered and
    replayed to the downstream app.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        buffered: list[Message] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    await self._reject(send)
                    return
                buffered.append(message)
                if not message.get("more_body", False):
                    break
            else:  # e.g. http.disconnect — stop buffering, hand it downstream
                buffered.append(message)
                break

        replay = iter(buffered)

        async def replay_receive() -> Message:
            try:
                return next(replay)
            except StopIteration:
                return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": "request body too large"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _public_reason(status: int) -> str:
    """The status code's canonical reason phrase — never a custom detail."""
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def _install_exception_handlers(app: FastAPI, logger: logging.Logger) -> None:
    """Return generic public errors that never echo raw input or a raw detail.

    * FastAPI's default 422 body includes the offending input (which may contain
      a secret); we log only the field LOCATIONS and return a generic message.
    * An ``HTTPException`` raised by a provider/adapter carries a custom
      ``detail`` that FastAPI would return verbatim; we replace it with the
      status's canonical reason phrase and never log the raw detail.
    * Other unhandled exceptions are sanitised in the correlation middleware, so
      a provider error message never reaches uvicorn's raw (unredacted) logger.
    """

    def _request_id(request: Request) -> str | None:
        return getattr(request.state, "request_id", None) or request_id_var.get()

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(request: Request, exc: RequestValidationError):
        locations = [".".join(str(part) for part in err["loc"]) for err in exc.errors()]
        request_id = _request_id(request)
        log_event(
            logger,
            logging.WARNING,
            "request_validation_failed",
            request_id=request_id,
            locations=locations,
        )
        return JSONResponse(
            status_code=422,
            content={"detail": "invalid request", "request_id": request_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _on_http_exception(request: Request, exc: StarletteHTTPException):
        request_id = _request_id(request)
        # Log ONLY the status (never the raw detail — it may carry a secret), and
        # drop any exception headers (also a potential leak vector).
        log_event(
            logger,
            logging.WARNING,
            "http_error",
            request_id=request_id,
            status=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _public_reason(exc.status_code), "request_id": request_id},
        )


def create_app(
    settings: Settings,
    *,
    provider: LLMProvider | None = None,
    reliability: ReliabilityEnvelope | None = None,
    log_stream: TextIO | None = None,
) -> FastAPI:
    logger = configure_logging(settings.log_level, stream=log_stream)

    app = FastAPI(title="Module 07b — reference AI service")
    app.state.settings = settings
    app.state.logger = logger
    # In production `bootstrap` injects an eagerly-built provider; None here means
    # a test did not inject one (only the default-provider dev path builds lazily).
    app.state.provider = provider
    # The reliability envelope (deadline, concurrency, rate limit, retry, circuit
    # breaker) wraps every model call. Tests may inject one with small limits or a
    # fake clock; otherwise it is built from Settings. Its worker pool is closed on
    # shutdown so a served process (and each TestClient) does not leak threads.
    app.state.reliability = reliability or build_envelope(settings)
    app.router.add_event_handler("shutdown", app.state.reliability.close)

    # Register secrets so they are scrubbed from every log line: the service's own
    # configured secret AND the provider credentials llm_core reads directly from
    # the environment. Then log the redacted config — which never extracts them.
    register_secret(settings.provider_api_key)
    register_provider_credentials()
    log_event(logger, logging.INFO, "service_configured", **settings.redacted_summary())

    # Enforce the body-size cap by counting ASGI bytes (chunked-safe). Added
    # before the correlation middleware so the latter stays OUTERMOST and can
    # stamp the request id / log even on a 413.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=_MAX_BODY_BYTES)

    _install_exception_handlers(app, logger)

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        # Accept an inbound correlation id, else mint one; propagate it into the
        # log context and echo it back on the response.
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        token = request_id_var.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Catch unhandled errors HERE (before Starlette's ServerError
                # middleware re-raises to uvicorn's raw logger). Log the traceback
                # via the scrubbing logger; return a generic public 500.
                logger.error(
                    "request_failed",
                    exc_info=exc,
                    extra={"extra_fields": {"request_id": request_id}},
                )
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "internal server error", "request_id": request_id},
                )
        finally:
            request_id_var.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        log_event(
            logger,
            logging.INFO,
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        # Liveness only: if the process can answer, it is alive. No dependencies.
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(request: Request):
        # Readiness reflects the real, MIGRATED, WRITABLE database (versions +
        # column fingerprint + write probe). It does blocking I/O, so run it off
        # the event loop.
        settings = request.app.state.settings
        db_ok = await run_in_threadpool(check_ready, settings.db_path, settings.migrations_dir)
        checks = {"db": "ok" if db_ok else "error"}
        if db_ok:
            return {"status": "ready", "checks": checks}
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})

    @app.post("/ask", response_model=AskResponse)
    def ask(
        payload: AskRequest,
        request: Request,
        provider: Annotated[LLMProvider, Depends(get_service_provider)],
        principal: Annotated[Principal, Depends(authenticate)],
    ) -> AskResponse:
        # A sync endpoint: FastAPI runs it in a threadpool, so the blocking
        # provider.chat call never stalls the event loop. Auth (401) already ran
        # via the dependency, BEFORE this body executes.
        settings = request.app.state.settings
        request_id = request.state.request_id

        # Tenant-scoped retrieval: the `tenant_id = ?` filter is IN THE QUERY, so
        # only the caller's tenant's chunks are ever fetched — never after.
        chunks = retrieve(settings.db_path, principal.tenant_id, payload.question)
        context = "\n\n".join(chunk.content for chunk in chunks)
        system_prompt = (
            _SYSTEM_PROMPT if not context else f"{_SYSTEM_PROMPT}\n\nContext:\n{context}"
        )

        messages = [
            ChatMessage("system", system_prompt),
            ChatMessage("user", payload.question),
        ]
        options = ChatOptions(temperature=0, max_tokens=512, model=settings.chat_model)
        # The model call runs inside the reliability envelope, keyed per identity.
        # A bounded failure (rate/circuit/concurrency/deadline/provider) is mapped
        # to its HTTP status; the exception handler returns the canonical reason
        # (never a raw provider detail), so the response stays safe and bounded.
        reliability: ReliabilityEnvelope = request.app.state.reliability
        try:
            result = reliability.call(
                lambda: provider.chat(messages, options), key=principal.user_id
            )
        except ReliabilityError as exc:
            # Log the failure MODE (rate/circuit/concurrency/deadline/upstream) for
            # observability — never the raw provider cause, which could carry a
            # credential. Then return the bounded status; the exception handler
            # renders only the canonical reason phrase.
            log_event(
                request.app.state.logger,
                logging.WARNING,
                "provider_call_failed",
                request_id=request_id,
                reason=type(exc).__name__,
            )
            raise HTTPException(status_code=exc.status) from exc

        record_audit(
            settings.db_path,
            actor=principal.user_id,
            tenant_id=principal.tenant_id,
            action=_audit_action(request),
            decision="allow",
            request_id=request_id,
        )
        return AskResponse(answer=result.text, request_id=request_id)

    @app.post("/documents", status_code=201, response_model=CreateDocumentResponse)
    def create_document_endpoint(
        payload: CreateDocumentRequest,
        request: Request,
        principal: Annotated[Principal, Depends(require_operator)],
    ) -> CreateDocumentResponse:
        # Operator-only (require_operator already returned 403 for a viewer, and
        # 401 for an unauthenticated caller — BEFORE this write runs). The document
        # is created in the CALLER'S tenant, never an arbitrary one.
        settings = request.app.state.settings
        request_id = request.state.request_id
        doc_id = create_document(
            settings.db_path, tenant_id=principal.tenant_id, title=payload.title
        )
        record_audit(
            settings.db_path,
            actor=principal.user_id,
            tenant_id=principal.tenant_id,
            action=_audit_action(request),
            decision="allow",
            request_id=request_id,
        )
        return CreateDocumentResponse(id=doc_id, request_id=request_id)

    @app.post("/jobs", response_model=EnqueueJobResponse)
    def enqueue_job_endpoint(
        payload: EnqueueJobRequest,
        request: Request,
        response: Response,
        principal: Annotated[Principal, Depends(require_operator)],
    ) -> EnqueueJobResponse:
        # Operator-only: enqueue a DURABLE indexing job for a document in the
        # caller's tenant. The slow work runs in the background worker, not here,
        # so the request returns at once. An `Idempotency-Key` header makes the
        # enqueue idempotent — a retried client request produces one job / one
        # effect (201/202 first, 200 on replay).
        settings = request.app.state.settings
        request_id = request.state.request_id
        if not document_exists(settings.db_path, principal.tenant_id, payload.document_id):
            # Missing OR another tenant's document — a clean 404, not an FK 500.
            raise HTTPException(status_code=404)
        idem = request.headers.get(_IDEMPOTENCY_HEADER)
        result = enqueue(
            settings.db_path,
            tenant_id=principal.tenant_id,
            document_id=payload.document_id,
            idempotency_key=idem or None,
        )
        response.status_code = 202 if result.created else 200
        record_audit(
            settings.db_path,
            actor=principal.user_id,
            tenant_id=principal.tenant_id,
            action=_audit_action(request),
            decision="allow",
            request_id=request_id,
        )
        # Report the job's CURRENT status (an idempotent replay may already have
        # been processed), so the response never claims a stale 'pending'.
        job = get_job(settings.db_path, principal.tenant_id, result.job_id)
        return EnqueueJobResponse(
            job_id=result.job_id,
            status=job.status if job is not None else "pending",
            request_id=request_id,
        )

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def job_status_endpoint(
        job_id: str,
        request: Request,
        principal: Annotated[Principal, Depends(authenticate)],
    ) -> JobStatusResponse:
        # Any authenticated caller may inspect a job — but only IN THEIR tenant:
        # get_job filters by tenant_id, so another tenant's job id is a 404, never
        # a cross-tenant status leak.
        settings = request.app.state.settings
        request_id = request.state.request_id
        job = get_job(settings.db_path, principal.tenant_id, job_id)
        if job is None:
            raise HTTPException(status_code=404)
        return JobStatusResponse(
            id=job.id,
            document_id=job.document_id,
            status=job.status,
            retries=job.retries,
            max_retries=job.max_retries,
            request_id=request_id,
        )

    return app


def bootstrap(
    settings: Settings,
    *,
    provider: LLMProvider | None = None,
    provider_factory: Callable[[Settings], LLMProvider] = build_default_provider,
    log_stream: TextIO | None = None,
) -> FastAPI:
    """Build the app for production, eagerly resolving the provider.

    Building the provider now means a missing or invalid provider credential
    (e.g. ``OPENAI_API_KEY``) fails fast at startup — before the port is bound —
    rather than 500-ing on the first ``/ask``. It also removes the lazy-singleton
    race in ``get_service_provider``. When a provider is injected (tests), the
    factory is skipped entirely.
    """
    resolved = provider if provider is not None else provider_factory(settings)
    return create_app(settings, provider=resolved, log_stream=log_stream)


def build_app_from_env() -> FastAPI:
    """Configure the redacting logger, then build the app from the environment.

    This is the single safe launcher for BOTH entrypoints (``__main__`` and
    ``asgi``). It installs the JSON logger + credential scrubber FIRST, so any
    failure in ``load_settings``/``bootstrap`` is logged SCRUBBED as
    ``startup_failed``. It then raises a generic :class:`StartupError` whose
    message contains no original detail (``from None`` also suppresses the
    original traceback), so an ASGI server that prints the propagated exception
    cannot leak a credential-bearing message.
    """
    logger = configure_logging()
    register_provider_credentials()
    try:
        settings = load_settings()
        register_secret(settings.provider_api_key)
        # Apply pending schema migrations at startup, so /readyz reflects a real,
        # migrated database. Idempotent — a no-op when already up to date.
        applied = apply_pending(settings.db_path, settings.migrations_dir)
        log_event(logger, logging.INFO, "migrations_applied", versions=applied)
        app = bootstrap(settings)
        # Start the durable-ingestion worker HERE (the production path only) — not
        # in create_app, so request tests stay deterministic and thread-free and
        # drive drain() themselves. Stop it on shutdown so no worker thread leaks.
        worker = JobWorker(settings.db_path, index_document(settings.db_path))
        app.state.job_worker = worker
        worker.start()
        app.router.add_event_handler("shutdown", worker.stop)
        return app
    except Exception:
        logger.exception("startup_failed")  # traceback scrubbed by the formatter
        raise StartupError("service startup failed; see the startup_failed log event") from None
