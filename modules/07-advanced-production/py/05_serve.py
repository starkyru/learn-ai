"""
Task 5 — Serve it  🟢

What this teaches:
  - Wrapping an LLM pipeline in a FastAPI app is the last step to making it
    accessible to UIs, other services, and scripts.
  - FastAPI's async support maps naturally onto async LLM calls and streaming.
  - Streaming responses (StreamingResponse) dramatically reduce perceived latency
    for long outputs — the client sees tokens as they arrive.
  - A /health endpoint is essential for load-balancer and uptime checks.

Setup:
  uv sync --extra production   # installs fastapi + uvicorn

How to run:
  uv run python modules/07-advanced-production/py/05_serve.py
  # or with uvicorn directly (enables --reload for development):
  uvicorn modules.07-advanced-production.py.05_serve:app --reload --port 3000

Test with curl:
  curl http://localhost:3000/health

  curl -X POST http://localhost:3000/chat \\
       -H "Content-Type: application/json" \\
       -d '{"message": "What is the capital of France?"}'

  curl -X POST http://localhost:3000/chat/stream \\
       -H "Content-Type: application/json" \\
       -d '{"message": "Explain recursion in 3 sentences."}'
"""

from __future__ import annotations

import time
from datetime import datetime

# TODO 1: Import what you need from FastAPI: the app class and an HTTP-error type,
#   the StreamingResponse type (from fastapi.responses) for TODO 6, a Pydantic
#   BaseModel for the request schema, and uvicorn to run the server.

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# TODO 2: Create the FastAPI app instance (give it a title/version). Name it `app`
#   so uvicorn can find it.

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

# TODO 3: Define a Pydantic request model `ChatRequest` with a required `message:
#   str` field and an optional `system_prompt: str` field defaulting to a helpful-
#   assistant string.

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# TODO 4: Implement GET /health with an @app.get decorator. Return a small JSON
#   dict reporting status "ok", a current UTC ISO timestamp, and the provider name
#   and chat model (from get_provider()). Load-balancers hit this to check liveness.


# TODO 5: Implement POST /chat (synchronous — returns the full response at once).
#   Decorate with @app.post("/chat") and take a `ChatRequest`. Build a
#   ChatMessage list (system prompt + user message), time the call, and call
#   provider.chat(...). Wrap the call so any exception becomes an HTTP 500 error
#   (raise the FastAPI HTTP-error type with the message as detail). Return a JSON
#   dict with the reply text, model, input/output token counts, and rounded latency.


# TODO 6: Implement POST /chat/stream (streaming — tokens arrive as generated).
#   Decorate with @app.post("/chat/stream"). Build the same ChatMessage list, then
#   define a generator that iterates provider.chat_stream(...) and yields each
#   chunk. Return that generator wrapped in a StreamingResponse with a text
#   media_type (e.g. "text/plain" or "text/event-stream").


# ---------------------------------------------------------------------------
# Entry point — run with: uv run python modules/07-advanced-production/py/05_serve.py
# ---------------------------------------------------------------------------

def main() -> None:
    # TODO 7: Once the app is implemented (TODOs 2-6), start the server here by
    #   calling uvicorn.run(...) on your `app`, binding host/port (e.g. port 3000).
    #   Replace the placeholder print below with that call.
    print("TODO: implement the FastAPI app above (TODOs 2-6), then start it with uvicorn.run.")


if __name__ == "__main__":
    main()
