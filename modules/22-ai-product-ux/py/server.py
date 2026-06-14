"""
Module 22 — AI Product UX: Python backend (FastAPI + SSE)

What this teaches:
  - How to wire up streaming SSE responses from an LLM to a browser client.
  - Citations: the LLM is asked to return structured JSON with answer + sources;
    the server proxies that to the client as typed SSE events.
  - Feedback capture: thumbs-up/down + "looks wrong" reports stored to JSONL.
  - Confidence/failure states: the server sends explicit event types (token,
    citation, error, done) so the client can render each state correctly.
  - Approval flow: a /actions/approve endpoint that gates a simulated risky
    action behind a server-side confirmation token.

How to run:
  uv sync --extra production
  uv run python modules/22-ai-product-ux/py/server.py

  Then open: modules/22-ai-product-ux/web/index.html in a browser
  (use a local file server or just open file://... directly).

Deps (add --extra production): fastapi, uvicorn[standard]
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn
except ImportError as e:
    raise ImportError(
        "FastAPI and uvicorn are required for this module.\n"
        "Run: uv sync --extra production"
    ) from e

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PORT = 3100
FEEDBACK_LOG = Path(__file__).parent / "feedback.jsonl"
ACTIONS_LOG = Path(__file__).parent / "actions.jsonl"

# In-memory store for pending approval tokens (token → action_payload)
# In production, use Redis with a TTL.
_pending_approvals: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# RAG stub
# A real implementation would embed the question, retrieve chunks from a vector
# store (module 05 patterns), then generate. Here we use a fixed corpus for
# demo purposes so the server is immediately runnable with no extra setup.
# ---------------------------------------------------------------------------

CORPUS = [
    {
        "id": "doc1",
        "title": "learn-ai Course Overview",
        "url": "README.md",
        "content": (
            "learn-ai is a hands-on AI course monorepo covering LLMs, RAG, and agents "
            "in both TypeScript and Python. It has modules numbered 00–23."
        ),
    },
    {
        "id": "doc2",
        "title": "Module 05 — RAG",
        "url": "modules/05-rag/README.md",
        "content": (
            "Module 05 covers Retrieval-Augmented Generation: chunk, embed, retrieve, "
            "rerank, generate, cite, and evaluate. It builds a full RAG pipeline. "
            "The default vector store uses cosine similarity in numpy."
        ),
    },
    {
        "id": "doc3",
        "title": "LLM Providers",
        "url": "packages/py/llm_core/llm_core/__init__.py",
        "content": (
            "Supported providers: openai, anthropic, ollama, nvidia. "
            "Set LLM_PROVIDER env var to switch. Default is ollama. "
            "get_provider() reads the env var and returns an LLMProvider instance."
        ),
    },
    {
        "id": "doc4",
        "title": "Module 07 — Observability",
        "url": "modules/07-advanced-production/README.md",
        "content": (
            "Module 07 covers eval harnesses, JSONL observability logging, "
            "prompt caching, guardrails, and serving with FastAPI and Node.js."
        ),
    },
    {
        "id": "doc5",
        "title": "Module 21 — LLMOps & Eval",
        "url": "modules/21-llmops-eval/README.md",
        "content": (
            "Module 21 covers the full eval lifecycle: versioned eval sets, "
            "experiment comparison, regression gates in CI, human review queues, "
            "and production monitoring with alert thresholds."
        ),
    },
]


def retrieve_context(question: str) -> list[dict]:
    """Stub retriever: return all corpus docs (replace with real vector search).

    TODO (task 2 extension): embed the question with provider.embed() and
    compute cosine similarity against pre-embedded corpus chunks, returning
    the top-k most relevant docs. See module 05 for the full pattern.
    """
    # For demo: return all docs. A real implementation would rank by similarity.
    return CORPUS


def build_rag_prompt(question: str, docs: list[dict]) -> str:
    """Build a system prompt that includes context and asks for citations."""
    context_block = "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['content']}" for doc in docs
    )
    return (
        "You are a helpful assistant for the learn-ai course. "
        "Answer the question using ONLY the provided context documents. "
        "If the context does not contain the answer, say so clearly.\n\n"
        "IMPORTANT: After your answer, output a JSON block on its own line:\n"
        '{"citations": ["<doc_id>", ...]}\n'
        "Include only the doc IDs you actually used.\n\n"
        f"Context:\n{context_block}"
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="learn-ai Module 22 — AI Product UX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # fine for local dev; tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Task 1 — /ask/stream  (streaming SSE)
# ---------------------------------------------------------------------------

async def stream_rag_answer(question: str) -> AsyncIterator[str]:
    """Stream a RAG answer as Server-Sent Events.

    Event types:
      data: {"type": "token",    "text": "..."}     — one token/chunk
      data: {"type": "citation", "doc": {...}}       — a source document
      data: {"type": "done",     "confidence": 0-1}  — final event
      data: {"type": "error",    "message": "..."}   — on failure

    TODO (task 1): The core streaming loop is implemented here as a working
    example. Study it — then extend it in tasks 2–3.
    """
    provider = get_provider()
    docs = retrieve_context(question)
    system_prompt = build_rag_prompt(question, docs)

    accumulated = ""
    citation_ids: list[str] = []
    sent_citations = False

    try:
        async for chunk in _async_stream(provider, system_prompt, question):
            accumulated += chunk

            # Detect and extract the citations JSON block
            if not sent_citations and '{"citations"' in accumulated:
                # Split text from citation JSON
                parts = accumulated.split('{"citations"', 1)
                text_part = parts[0].strip()
                json_part = '{"citations"' + parts[1]
                try:
                    citation_data = json.loads(json_part)
                    citation_ids = citation_data.get("citations", [])
                    sent_citations = True
                    # Don't yield the JSON block as a token — it's metadata
                    continue
                except json.JSONDecodeError:
                    pass  # JSON not complete yet, keep accumulating

            # Only stream the text part (before citations JSON)
            if not sent_citations:
                yield _sse({"type": "token", "text": chunk})
            # If already sent citations, skip any further output (the JSON block tail)

        # After streaming, send citation events
        if sent_citations:
            doc_map = {d["id"]: d for d in docs}
            for cid in citation_ids:
                if cid in doc_map:
                    yield _sse({"type": "citation", "doc": doc_map[cid]})

        # Compute a simple confidence proxy: if citations were found, high confidence
        confidence = 0.85 if citation_ids else 0.40
        yield _sse({"type": "done", "confidence": confidence})

    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _async_stream(provider, system_prompt: str, question: str) -> AsyncIterator[str]:
    """Wrap the synchronous chat_stream iterator in an async generator."""
    loop = asyncio.get_event_loop()
    messages = [
        ChatMessage("system", system_prompt),
        ChatMessage("user", question),
    ]
    # Run the blocking iterator in a thread pool
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _collect_chunks():
        return list(provider.chat_stream(messages))

    chunks = await loop.run_in_executor(executor, _collect_chunks)
    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0)   # yield control to event loop


@app.post("/ask/stream")
async def ask_stream(request: Request):
    """Stream a RAG answer with citations over SSE.

    Request body: {"question": "..."}
    Response: text/event-stream
    """
    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    return StreamingResponse(
        stream_rag_answer(question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Task 3 — /ask  (synchronous, for confidence/failure state demo)
# ---------------------------------------------------------------------------

@app.post("/ask")
async def ask_sync(request: Request):
    """Synchronous RAG endpoint — returns full answer + citations + confidence.

    Response: {"answer": "...", "citations": [...], "confidence": 0-1, "model": "..."}

    TODO (task 3): The confidence field here is a stub (always 0.85 if citations
    exist). Extend it to use the LLM-judge faithfulness score from module 21.
    """
    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    provider = get_provider()
    docs = retrieve_context(question)
    system_prompt = build_rag_prompt(question, docs)

    messages = [
        ChatMessage("system", system_prompt),
        ChatMessage("user", question),
    ]

    try:
        result = provider.chat(messages)
    except Exception as exc:
        # Task 3: return a structured error so the client can render the error state
        return JSONResponse(
            status_code=200,   # 200 so the client reads the body
            content={"error": str(exc), "confidence": 0.0},
        )

    # Parse citations from the output
    answer_text = result.text
    citation_ids: list[str] = []
    if '{"citations"' in answer_text:
        parts = answer_text.split('{"citations"', 1)
        answer_text = parts[0].strip()
        try:
            citation_ids = json.loads('{"citations"' + parts[1]).get("citations", [])
        except json.JSONDecodeError:
            pass

    doc_map = {d["id"]: d for d in docs}
    cited_docs = [doc_map[cid] for cid in citation_ids if cid in doc_map]
    confidence = 0.85 if cited_docs else 0.35

    return {
        "answer": answer_text,
        "citations": cited_docs,
        "confidence": confidence,
        "model": result.model,
    }


# ---------------------------------------------------------------------------
# Task 4 — /feedback  (capture thumbs-up/down + "looks wrong")
# ---------------------------------------------------------------------------

@app.post("/feedback")
async def feedback(request: Request):
    """Store user feedback to JSONL.

    Request body:
      {"question": "...", "answer": "...", "rating": "up"|"down"|"wrong",
       "note": "optional freetext"}
    """
    body = await request.json()
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": body.get("question", ""),
        "answer": body.get("answer", ""),
        "rating": body.get("rating", ""),
        "note": body.get("note", ""),
    }

    # TODO (task 4): implement the write here
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"status": "ok", "id": entry["id"]}


# ---------------------------------------------------------------------------
# Task 5 — Approval flow for risky actions
# ---------------------------------------------------------------------------

@app.post("/actions/request")
async def request_action(request: Request):
    """Register a risky action and return a one-time approval token.

    Request body: {"action": "...", "payload": {...}}
    Response: {"token": "...", "expires_in_s": 120}

    The client shows an approval modal. The user clicks Approve → POST /actions/approve.
    """
    body = await request.json()
    action = body.get("action", "")
    payload = body.get("payload", {})

    if not action:
        raise HTTPException(status_code=400, detail="action is required")

    token = secrets.token_urlsafe(24)
    _pending_approvals[token] = {
        "action": action,
        "payload": payload,
        "requested_at": time.time(),
    }

    return {"token": token, "expires_in_s": 120}


@app.post("/actions/approve")
async def approve_action(request: Request):
    """Consume an approval token and execute the action.

    Request body: {"token": "...", "approved": true|false}
    Response: {"status": "executed"|"rejected"|"expired"}

    TODO (task 5): Extend this to execute real actions (e.g., send an email,
    delete a record). Right now it just validates and logs.
    """
    body = await request.json()
    token = body.get("token", "")
    approved = body.get("approved", False)

    pending = _pending_approvals.pop(token, None)
    if pending is None:
        return {"status": "expired"}

    # Check token age (120 s TTL)
    if time.time() - pending["requested_at"] > 120:
        return {"status": "expired"}

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": pending["action"],
        "payload": pending["payload"],
        "approved": approved,
    }
    ACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIONS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if approved:
        # In a real app, execute the action here.
        return {"status": "executed", "action": pending["action"]}
    else:
        return {"status": "rejected"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "module": "22-ai-product-ux"}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
