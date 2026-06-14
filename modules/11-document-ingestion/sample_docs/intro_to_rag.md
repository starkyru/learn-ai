# Introduction to RAG

Retrieval-Augmented Generation (RAG) is a technique that combines a retrieval
system with a large language model (LLM) to produce grounded, factual responses.

## Why RAG?

Large language models are trained on static snapshots of the internet. They do
not know about events after their training cut-off, and they cannot access your
private documents. Fine-tuning can address the knowledge gap, but it is slow,
expensive, and requires ML expertise.

RAG solves this differently: keep the knowledge outside the model, in a
retrieval store, and inject only the relevant passages into the prompt at
query time. The model's job shrinks from "know everything" to "read the
provided text and answer the question."

## The Pipeline

1. **Ingestion (offline):** Parse documents, clean text, split into chunks,
   embed each chunk, and store the embeddings in a vector database.
2. **Retrieval (online):** Embed the user's question, find the top-k most
   similar chunks, and pull them back.
3. **Generation:** Build a prompt that includes the retrieved chunks as context
   and ask the LLM to answer using only that context.

## Ingestion is 80% of the Work

A common misconception: RAG is just "give the LLM some documents." In practice,
the ingestion step is where most production projects spend most of their
engineering time.

- PDFs have headers, footers, multi-column layouts, and tables that break naive
  text extraction.
- HTML pages are surrounded by navigation, ads, and boilerplate that drown the
  signal.
- Markdown is clean but headings define semantic sections that should not be
  split across chunks.

Getting ingestion right — format detection, boilerplate stripping, section-aware
chunking — is what separates a toy RAG demo from a production system.

## Chunking Strategies

| Strategy | Best for |
| --- | --- |
| Fixed-size (by word/char) | Simple; good baseline |
| Sentence-based | Natural language queries |
| Section/heading-based | Structured documents (manuals, wikis) |
| Overlapping | Prevents lost context at boundaries |

The right chunk size depends on your embedding model's token limit (usually
256–512 tokens) and the nature of your queries.

## Metadata Matters

Every chunk should carry metadata so you can:
- Filter by source or date at retrieval time.
- Show users which document a fact came from (attribution).
- Track freshness and invalidate stale chunks during incremental re-indexing.

Minimum useful metadata: `source`, `page` (for PDFs), `section` (for headings),
`ingested_at`.
