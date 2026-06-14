# Capstone — Python starter

This folder is yours to build in. There is no scaffold; the structure below is a
suggestion for Option A (Documentation Q&A assistant). Adapt it freely.

## Suggested layout

```
py/
├── README.md          ← this file; update it as you build
├── ingest.py          ← parse formats (11), clean (11), chunk + embed + index (04/11)
├── retriever.py       ← dense + BM25 hybrid retrieval (04), RRF fusion, reranking (05)
├── generator.py       ← RAG generate: passages + question → answer + citations (05)
├── agent.py           ← agent loop wrapping retriever + generator + tools (06/17)
├── tools.py           ← tool definitions (search, calculator, SQL, etc.) (06/12)
├── eval.py            ← versioned eval harness: load QA pairs, run, LLM-judge score (07/21)
├── server.py          ← FastAPI app: POST /ask/stream → SSE, POST /ask → JSON (07/22)
├── data/
│   └── corpus/        ← your source documents (PDF, Markdown, HTML, plain text)
├── eval_set.jsonl     ← {question, reference_answer} pairs for automated eval
└── tests/
    └── test_retriever.py
```

## Running (examples)

```bash
# ingest your corpus (parse → clean → chunk → embed → index)
uv run python py/ingest.py --corpus py/data/corpus/ --collection my_docs

# ask a question interactively
uv run python py/agent.py --question "What does X say about Y?"

# run the eval harness
uv run python py/eval.py --eval-set py/eval_set.jsonl

# serve the API
uv run python py/server.py   # → http://localhost:8000/ask
```

## Key imports

```python
from llm_core import get_provider, ChatMessage

llm = get_provider()   # reads LLM_PROVIDER from .env — never hardcode a vendor
```

For vectors: `uv sync --extra vectors` (adds chromadb, qdrant-client, rank-bm25).

For document ingestion: `uv add pypdf beautifulsoup4 httpx` (or `uv sync --extra ingestion`).

For the API: `uv sync --extra production` (adds fastapi, uvicorn).

## Where to start

1. Re-read `modules/05-rag/`, `modules/06-agents/`, and `modules/11-document-ingestion/` READMEs.
2. Pick a small corpus (10–50 documents). Docs you actually want to query work
   best — you'll know when the answers are wrong.
3. Build M1 (ingest + query) first and make sure retrieval is good before
   building the generator. Bad retrieval cannot be fixed by a better prompt.
4. Write 5 test questions manually before you write any eval code — they will
   expose retrieval failures immediately.
5. After M3, add security hardening (module 20) and an eval gate (module 21)
   before calling the project done.
