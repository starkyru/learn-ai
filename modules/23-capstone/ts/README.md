# Capstone — TypeScript starter

This folder is yours to build in. There is no scaffold; the structure below is a
suggestion for Option A (Documentation Q&A assistant). Adapt it freely.

## Suggested layout

```
ts/
├── README.md            ← this file; update it as you build
├── package.json
├── tsconfig.json
├── src/
│   ├── ingest.ts        ← parse formats (11), clean (11), chunk + embed + index (04/11)
│   ├── retriever.ts     ← dense + BM25 hybrid retrieval (04), RRF, reranking (05)
│   ├── generator.ts     ← RAG generate: passages + question → answer + citations (05)
│   ├── agent.ts         ← agent loop wrapping retriever + generator + tools (06/17)
│   ├── tools.ts         ← tool definitions (search, calculator, SQL, etc.) (06/12)
│   ├── eval.ts          ← versioned eval harness: load QA pairs, run, LLM-judge score (07/21)
│   └── server.ts        ← Hono or Express: POST /ask/stream → SSE, POST /ask → JSON (07/22)
├── data/
│   └── corpus/          ← your source documents
├── eval_set.jsonl       ← {question, referenceAnswer} per line
└── tests/
    └── retriever.test.ts
```

## Running (examples)

```bash
# ingest (parse → clean → chunk → embed → index)
pnpm tsx src/ingest.ts --corpus data/corpus/ --collection my_docs

# ask a question
pnpm tsx src/agent.ts --question "What does X say about Y?"

# eval harness
pnpm tsx src/eval.ts --evalSet eval_set.jsonl

# serve
pnpm tsx src/server.ts   # → http://localhost:3000/ask
```

## Key imports

```ts
import { getProvider } from "@learn-ai/llm-core";

const llm = getProvider();  // reads LLM_PROVIDER from .env — never hardcode a vendor
```

## Dependencies to add as needed

```jsonc
// for vectors (add to package.json dependencies):
"chromadb": "^1.x",
"qdrant-js": "^1.x",

// for document ingestion:
"pdf-parse": "^1.x",
"cheerio": "^1.x",

// for the API server:
"hono": "^4.x",
// or:
"express": "^4.x",
"@types/express": "^4.x",

// for MCP tools (module 17):
"@modelcontextprotocol/sdk": "^1.x",

// for testing:
"vitest": "^2.x"
```

Install with `pnpm install`.

## Where to start

1. Re-read `modules/05-rag/`, `modules/06-agents/`, and `modules/11-document-ingestion/` READMEs.
2. Pick a small corpus (10–50 documents) on a topic you care about — you'll know
   when answers are wrong.
3. Get `ingest.ts` + a simple `retriever.ts` query working before you touch the
   generator. Retrieval quality is the floor everything else rests on.
4. Write 5 test questions by hand before writing any eval code. They expose
   retrieval failures fast.
5. After M3, add security hardening (module 20) and a CI eval gate (module 21)
   before calling the project done.
