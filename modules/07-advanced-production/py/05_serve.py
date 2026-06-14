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

# TODO 1: Import FastAPI and related types.
#   from fastapi import FastAPI, HTTPException
#   from fastapi.responses import StreamingResponse
#   from pydantic import BaseModel
#   import uvicorn

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# TODO 2: Create the FastAPI app.
#   app = FastAPI(title="learn-ai LLM service", version="0.1.0")

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

# TODO 3: Define the request model with Pydantic.
#   class ChatRequest(BaseModel):
#       message: str
#       system_prompt: str = "You are a helpful assistant."

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# TODO 4: Implement GET /health.
#   @app.get("/health")
#   def health():
#       provider = get_provider()
#       return {
#           "status": "ok",
#           "timestamp": datetime.utcnow().isoformat() + "Z",
#           "provider": provider.name,
#           "model": provider.chat_model,
#       }


# TODO 5: Implement POST /chat (synchronous — returns full response at once).
#   @app.post("/chat")
#   async def chat(req: ChatRequest):
#       provider = get_provider()
#       t0 = time.perf_counter()
#       try:
#           result = provider.chat([
#               ChatMessage("system", req.system_prompt),
#               ChatMessage("user", req.message),
#           ])
#       except Exception as e:
#           raise HTTPException(status_code=500, detail=str(e))
#       latency_ms = (time.perf_counter() - t0) * 1000
#       return {
#           "text": result.text,
#           "model": result.model,
#           "input_tokens": result.usage.input_tokens,
#           "output_tokens": result.usage.output_tokens,
#           "latency_ms": round(latency_ms, 1),
#       }


# TODO 6: Implement POST /chat/stream (streaming — tokens arrive as generated).
#   Use StreamingResponse with media_type="text/plain" (or text/event-stream).
#   The generator calls provider.chat_stream() and yields each chunk.
#
#   @app.post("/chat/stream")
#   async def chat_stream(req: ChatRequest):
#       provider = get_provider()
#       def generate():
#           for chunk in provider.chat_stream([
#               ChatMessage("system", req.system_prompt),
#               ChatMessage("user", req.message),
#           ]):
#               yield chunk
#       return StreamingResponse(generate(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Entry point — run with: uv run python modules/07-advanced-production/py/05_serve.py
# ---------------------------------------------------------------------------

def main() -> None:
    # TODO 7: Uncomment the uvicorn.run call once the app is implemented.
    #   import uvicorn
    #   uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
    print("TODO: implement the FastAPI app above (TODOs 2-6), then uncomment the uvicorn.run call.")


if __name__ == "__main__":
    main()
