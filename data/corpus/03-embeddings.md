# Embeddings

An embedding is a dense, low-dimensional vector representation of a discrete object —
a word, a sentence, an image, or a user ID. The core idea is that similar objects
should map to nearby points in vector space. This geometric property makes embeddings
the foundation of modern search, recommendation, and retrieval-augmented generation
(RAG).

## Word embeddings

Early embedding models like **Word2Vec** (2013) and **GloVe** (2014) assign each word
a fixed vector, learned by training a shallow network to predict surrounding words in
a large text corpus. The result is a vector space where `king - man + woman ≈ queen`
— arithmetic on vectors captures semantic relationships.

The limitation is that every word has only one vector regardless of context.
"Bank" has the same representation whether it means a riverbank or a financial
institution.

## Contextual embeddings

Transformer-based models like BERT and its descendants produce **contextual
embeddings**: the vector for a word depends on the entire surrounding sentence. This
resolves ambiguity and captures much richer semantics.

Modern **sentence embedding** models (e.g., `text-embedding-3-small` from OpenAI,
`nomic-embed-text` for local use) encode a whole sentence or passage into a single
fixed-size vector, optimised for semantic similarity tasks.

## Similarity and retrieval

The most common similarity metric for embeddings is **cosine similarity**: the cosine
of the angle between two vectors. It ranges from –1 (opposite) to 1 (identical) and
is insensitive to vector magnitude, which matters because sentence length affects
magnitude.

To retrieve the most relevant documents for a query, embed the query and all documents,
then return the documents whose vectors have the highest cosine similarity to the
query vector. This is the retrieval step in a RAG pipeline.
