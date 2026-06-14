# Retrieval-Augmented Generation (RAG)

Large language models have a fixed knowledge cutoff and can hallucinate facts that are
not in their training data. **Retrieval-Augmented Generation (RAG)** solves this by
connecting the model to an external knowledge base at inference time. Instead of asking
the model to recall a fact, you retrieve the relevant document and put it directly in
the prompt.

## The RAG pipeline

A standard RAG pipeline has two phases:

### Indexing (offline)
1. **Chunk** the source documents into passages (typically 200–500 tokens with some
   overlap to preserve context across chunk boundaries).
2. **Embed** each chunk using an embedding model to get a dense vector.
3. **Store** the vectors and the original text in a vector database (e.g., Chroma,
   Qdrant, or an in-memory index for prototyping).

### Retrieval + generation (online)
1. **Embed** the user's query with the same embedding model.
2. **Retrieve** the top-k chunks whose vectors are most similar to the query vector
   (nearest-neighbour search).
3. **Rerank** (optional): a cross-encoder re-scores the top-k candidates for higher
   precision. BM25 keyword search can be combined with dense retrieval (**hybrid
   search**) to catch exact keyword matches that semantic search misses.
4. **Generate**: insert the retrieved chunks into the prompt as context and ask the
   LLM to answer the question, citing only what is in the context.

## Key failure modes

- **Retrieval miss**: the answer is in the corpus but the query embedding is too
  dissimilar to the chunk embedding — tuning chunk size and overlap helps.
- **Context too long**: stuffing too many retrieved chunks can push the relevant
  passage beyond the model's effective attention range.
- **Hallucination despite retrieval**: the model ignores the context and generates
  from memory. Explicit prompting ("answer only from the provided context") reduces
  but does not eliminate this.

## Evaluation

A faithful RAG system should be measured on two axes: **retrieval recall** (did the
right chunk get retrieved?) and **answer faithfulness** (does the generated answer
follow from the retrieved context?). LLM-as-judge metrics and frameworks like RAGAS
automate both.
