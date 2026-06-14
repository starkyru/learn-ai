# Sample Corpus — Foundations of Machine Learning

This directory contains a small sample corpus used by **modules 04 and 05** for
embedding and retrieval exercises, and by the course tutor.

## Theme

Six self-contained Markdown documents on the **foundations of machine learning**,
progressing from basic concepts to the techniques that power modern LLMs and RAG
systems:

| File | Topic |
| --- | --- |
| `corpus/01-what-is-machine-learning.md` | ML paradigms, loss functions, overfitting |
| `corpus/02-neural-networks.md` | Layers, backpropagation, CNNs / RNNs / Transformers |
| `corpus/03-embeddings.md` | Word2Vec, contextual embeddings, cosine similarity |
| `corpus/04-transformers-and-attention.md` | Attention mechanism, multi-head attention, decoder-only LLMs |
| `corpus/05-training-and-fine-tuning.md` | Pre-training, SFT, RLHF, LoRA |
| `corpus/06-retrieval-augmented-generation.md` | The RAG pipeline, failure modes, evaluation |

Each document is roughly 200–300 words — short enough to fit comfortably in a single
chunk during the module 04 exercises, yet long enough to carry distinct semantic
content that makes retrieval meaningful.

## How modules 04 and 05 use it

- **Module 04** embeds all six documents into an in-memory vector index, then runs
  nearest-neighbour queries to demonstrate semantic search. The documents are short
  enough that you can inspect every retrieved vector by hand.
- **Module 05** builds a full RAG pipeline over the same corpus: chunk → embed →
  retrieve → (optionally rerank) → generate. The small size means you can run
  complete evals cheaply.

## Suggested test questions

These questions are good smoke tests for your retrieval pipeline because each answer
lives clearly in one specific document:

| Question | Expected source document |
| --- | --- |
| What is the difference between supervised and unsupervised learning? | `01-what-is-machine-learning.md` |
| How does backpropagation compute gradients in a neural network? | `02-neural-networks.md` |
| Why does Word2Vec produce a single vector per word regardless of context? | `03-embeddings.md` |
| What is the mathematical formula for scaled dot-product attention? | `04-transformers-and-attention.md` |
| What is LoRA and why is it used for fine-tuning? | `05-training-and-fine-tuning.md` |
| What are the two main failure modes of a RAG pipeline? | `06-retrieval-augmented-generation.md` |

A well-tuned system should retrieve the correct document as the top-1 result for each
of these questions. If it doesn't, experiment with chunk overlap, re-ranking, or a
stronger embedding model.

## Extending the corpus

Add more `.md` files to `corpus/` and re-index. The modules are designed to pick up
any files matching `corpus/*.md`, so no code changes are needed.
