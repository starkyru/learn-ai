# Glossary — abbreviations across the course

Every abbreviation used across the course, expanded on first use in each lesson and
collected here. Each row gives the expansion and a one-line "what it is" so you can
skim the whole vocabulary in one place. When a term has a dedicated lesson, the
module README is still the source of truth — this table is a quick lookup, not a
substitute for the reading.

| Abbreviation | Expansion                                               | What it is                                                                   |
| ------------ | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| ACL          | Access Control List                                     | Permission list controlling who can access a resource.                       |
| Adam         | Adaptive Moment Estimation                              | Adaptive per-parameter gradient optimizer.                                   |
| AI           | Artificial Intelligence                                 | Umbrella term for the systems this course builds and secures.                |
| ANN          | Approximate Nearest Neighbor                            | Class of fast, sublinear vector-search algorithms.                           |
| API          | Application Programming Interface                       | Interface for programmatic access to a service.                              |
| ARIA         | Accessible Rich Internet Applications                   | Attributes describing UI semantics for assistive tech.                       |
| ATX          | ATX heading                                             | Markdown heading syntax using leading `#` hash marks.                        |
| AUC          | Area Under the Curve                                    | Threshold-free ranking-quality score (area under the ROC curve).             |
| BatchNorm    | Batch Normalization                                     | Batch-wise activation normalization, contrasted with LayerNorm.              |
| BERT         | Bidirectional Encoder Representations from Transformers | Encoder-only masked-LM model family; contrast with GPT decoders.             |
| BFS          | Breadth-First Search                                    | Graph traversal used for multi-hop subgraph gathering.                       |
| BM25         | Best Matching 25                                        | Sparse lexical retrieval ranking function.                                   |
| BPE          | Byte-Pair Encoding                                      | Subword tokenization algorithm.                                              |
| BT           | Bradley–Terry                                           | Pairwise-preference probability model behind reward modeling and DPO.        |
| CART         | Classification and Regression Trees                     | Greedy recursive-splitting algorithm behind decision trees.                  |
| CI           | Continuous Integration                                  | Automated pipeline gating code changes, e.g. with a red-team harness.        |
| CLI          | Command-Line Interface                                  | Terminal interface, e.g. the interactive labelling loop.                     |
| CLIP         | Contrastive Language-Image Pre-training                 | Joint text/image embedding model enabling zero-shot image search.            |
| CNN          | Convolutional Neural Network                            | Neural net using convolutional layers for vision.                            |
| CoT          | Chain-of-Thought                                        | Prompting that elicits step-by-step reasoning before an answer.              |
| CV           | Cross-Validation                                        | Held-out estimation of test error by rotating folds.                         |
| DB           | Database                                                | Structured data store; here often a vector database.                         |
| DCT          | Discrete Cosine Transform                               | Frequency domain used for invisible watermark embedding.                     |
| DDPM         | Denoising Diffusion Probabilistic Model                 | Diffusion training objective and reverse-denoising sampler.                  |
| DETR         | Detection Transformer                                   | Transformer-based object-detection model.                                    |
| DLP          | Data Loss Prevention                                    | Output filter that catches leaked secrets as a last resort.                  |
| DOM          | Document Object Model                                   | Structured tree representation of a web page.                                |
| DPO          | Direct Preference Optimization                          | Preference tuning on pairs directly — no explicit reward model or RL.        |
| Embedding    | Vector Embedding                                        | Dense numeric vector representing text/image meaning for similarity search.  |
| F1           | F1 Score                                                | Harmonic mean of precision and recall.                                       |
| FFN          | Feed-Forward Network                                    | Position-wise two-layer sublayer in a transformer block.                     |
| FPR          | False Positive Rate                                     | Fraction of negatives wrongly flagged; the ROC curve's x-axis.               |
| GD           | Gradient Descent                                        | Iterative optimizer that steps against the loss gradient.                    |
| GDPR         | General Data Protection Regulation                      | EU law governing personal-data handling.                                     |
| GELU         | Gaussian Error Linear Unit                              | Smooth activation used in GPT-family feed-forward networks.                  |
| GPT          | Generative Pre-trained Transformer                      | Decoder-only language-model family this course reconstructs.                 |
| GPU          | Graphics Processing Unit                                | Parallel-compute processor needed to train and run large models.             |
| GQA          | Grouped-Query Attention                                 | Query heads share K/V heads to shrink the KV cache.                          |
| GraphRAG     | Graph-based Retrieval-Augmented Generation              | Builds a knowledge graph for multi-hop and global retrieval.                 |
| GRPO         | Group Relative Policy Optimization                      | Critic-free RLHF variant normalizing rewards within a sampled group.         |
| GRU          | Gated Recurrent Unit                                    | Simpler gated recurrent cell.                                                |
| HD           | High Definition                                         | Standard-resolution image size reference.                                    |
| HITL         | Human-in-the-Loop                                       | Human approval/intervention pattern in agent runs.                           |
| HNSW         | Hierarchical Navigable Small World                      | Graph-based approximate-nearest-neighbor index.                              |
| HOG          | Histogram of Oriented Gradients                         | Hand-crafted image feature descriptor.                                       |
| HTML         | HyperText Markup Language                               | Markup language for web pages.                                               |
| HTTP         | HyperText Transfer Protocol                             | Request/response protocol of the web.                                        |
| HyDE         | Hypothetical Document Embeddings                        | Query expansion that embeds a hypothetical answer.                           |
| ISO          | International Organization for Standardization          | Standards body; here the ISO 8601 timestamp format.                          |
| JSON         | JavaScript Object Notation                              | Structured data format returned by native tool calling.                      |
| JSON Schema  | JavaScript Object Notation Schema                       | Schema format describing tool arguments.                                     |
| JSON-RPC     | JSON Remote Procedure Call                              | Wire protocol MCP uses over stdio.                                           |
| JSONL        | JSON Lines                                              | One-JSON-object-per-line format used for batch requests.                     |
| KL           | Kullback–Leibler Divergence                             | Distribution-mismatch measure; the leash keeping RLHF near the reference.    |
| kNN          | k-Nearest Neighbors                                     | Classify by majority label of the nearest embeddings.                        |
| KS           | Kolmogorov–Smirnov test                                 | Nonparametric two-sample distribution-drift test.                            |
| KTO          | Kahneman–Tversky Optimization                           | Preference tuning from per-response good/bad labels instead of pairs.        |
| KV cache     | Key-Value Cache                                         | Cached attention keys/values that avoid recomputation during generation.     |
| LayerNorm    | Layer Normalization                                     | Per-token feature normalization.                                             |
| LCEL         | LangChain Expression Language                           | LangChain's pipe (`\|`) syntax for chaining Runnables.                       |
| LLM          | Large Language Model                                    | The core model type used for generation and judging throughout.              |
| LoRA         | Low-Rank Adaptation                                     | Parameter-efficient fine-tuning via low-rank weight updates.                 |
| LR           | Logistic Regression                                     | Linear classifier trained on embedding vectors.                              |
| LSH          | Locality-Sensitive Hashing                              | Finds near-duplicates in sublinear time.                                     |
| LSTM         | Long Short-Term Memory                                  | Gated recurrent cell that mitigates vanishing gradients.                     |
| MCP          | Model Context Protocol                                  | Open standard for exposing tools/resources/prompts to LLM apps.              |
| MHA          | Multi-Head Attention                                    | Parallel attention heads operating in independent subspaces.                 |
| ML           | Machine Learning                                        | Field of models that learn from data; here often pure-numpy by design.       |
| MLE          | Maximum Likelihood Estimation                           | Pick parameters maximizing data likelihood; CE/MSE minimization in disguise. |
| MLM          | Masked Language Modeling                                | BERT pretraining objective: predict masked tokens from both sides.           |
| MLP          | Multi-Layer Perceptron                                  | Two-layer net applied per position inside the FFN.                           |
| MMLU         | Massive Multitask Language Understanding                | Common multiple-choice LLM knowledge benchmark.                              |
| MoE          | Mixture of Experts                                      | Router activates top-k expert FFNs per token; capacity without FLOPs.        |
| MQA          | Multi-Query Attention                                   | All query heads share one K/V head; GQA's extreme case.                      |
| MRR          | Mean Reciprocal Rank                                    | Retrieval-quality metric (e.g. MRR@5).                                       |
| MSE          | Mean Squared Error                                      | Loss function used to train the toy denoiser.                                |
| NDCG         | Normalized Discounted Cumulative Gain                   | Graded, rank-discounted retrieval-quality metric.                            |
| NIM          | NVIDIA Inference Microservices                          | NVIDIA's hosted OpenAI-compatible inference service.                         |
| NL           | Natural Language                                        | Plain-English user input, the source side of NL→SQL.                         |
| NLL          | Negative Log-Likelihood                                 | Loss form of maximum likelihood; cross-entropy is one.                       |
| NLP          | Natural Language Processing                             | The field of computational language understanding.                           |
| NSFW         | Not Safe For Work                                       | Post-generation classifier that blocks unsafe image outputs.                 |
| OAuth        | Open Authorization                                      | Delegated-access authorization framework.                                    |
| OCR          | Optical Character Recognition                           | Extracts text from images and scanned pages.                                 |
| OS           | Operating System                                        | Software managing hardware and processes.                                    |
| OWASP        | Open Worldwide Application Security Project             | Body publishing the LLM Top 10 risk list.                                    |
| PCA          | Principal Component Analysis                            | Projects data onto top variance directions (covariance eigenvectors).        |
| PCM          | Pulse-Code Modulation                                   | Raw audio sample encoding used in WAV.                                       |
| PDF          | Portable Document Format                                | Common fixed-layout document file format.                                    |
| PE           | Positional Encoding                                     | Position-dependent vector added to token embeddings.                         |
| PEFT         | Parameter-Efficient Fine-Tuning                         | Family of methods (and the HuggingFace library) that train few params.       |
| PII          | Personally Identifiable Information                     | Sensitive personal data to redact before indexing.                           |
| PKCE         | Proof Key for Code Exchange                             | OAuth extension securing the authorization-code exchange.                    |
| PNG          | Portable Network Graphics                               | Lossless image file format for saving outputs.                               |
| PPO          | Proximal Policy Optimization                            | Clipped policy-gradient algorithm used in production RLHF.                   |
| pre-LN       | Pre-Layer Normalization                                 | Block style that normalizes each sublayer's input before the residual.       |
| PSI          | Population Stability Index                              | Histogram-drift score; > 0.2 conventionally means investigate.               |
| QLoRA        | Quantized Low-Rank Adaptation                           | LoRA over 4-bit quantized frozen base weights.                               |
| RAG          | Retrieval-Augmented Generation                          | Grounds LLM output in fetched documents.                                     |
| ReAct        | Reasoning and Acting                                    | Agent pattern interleaving reasoning traces and tool actions.                |
| ReLU         | Rectified Linear Unit                                   | Activation with derivative 1 for positive inputs.                            |
| REST         | Representational State Transfer                         | HTTP API style, e.g. of the Replicate provider.                              |
| RLAIF        | Reinforcement Learning from AI Feedback                 | RLHF with AI-generated preference labels (Constitutional AI).                |
| RLHF         | Reinforcement Learning from Human Feedback              | Post-training stage aligning a model to human preferences.                   |
| RM           | Reward Model                                            | Scores responses; trained from pairwise preferences (Bradley–Terry).         |
| RMS          | Root Mean Square                                        | Per-frame energy measure used in voice activity detection.                   |
| RNN          | Recurrent Neural Network                                | Sequence model with hidden-state memory.                                     |
| ROC          | Receiver Operating Characteristic                       | Ranking curve of true-positive vs false-positive rate.                       |
| RoPE         | Rotary Positional Embedding                             | Modern replacement for sinusoidal positional encoding.                       |
| RRF          | Reciprocal Rank Fusion                                  | Fuses multiple ranked result lists into one.                                 |
| RSS          | Really Simple Syndication                               | Feed format for news and research retrieval.                                 |
| SDK          | Software Development Kit                                | Toolkit/library for building against a platform.                             |
| SDPA         | Scaled Dot-Product Attention                            | Core attention kernel run per head.                                          |
| Self-RAG     | Self-Reflective Retrieval-Augmented Generation          | RAG where the model gates retrieval and critiques itself.                    |
| SFT          | Supervised Fine-Tuning                                  | Training on labeled (prompt, completion) pairs.                              |
| SGD          | Stochastic Gradient Descent                             | Baseline mini-batch gradient optimizer.                                      |
| SHA-256      | Secure Hash Algorithm 256-bit                           | Cryptographic hash used here for content hashing.                            |
| SMOTE        | Synthetic Minority Oversampling Technique               | Balances classes by interpolating synthetic minority samples.                |
| SOTA         | State of the Art                                        | Best current performance on a benchmark.                                     |
| SPA          | Single-Page Application                                 | Web app that updates content without full reloads.                           |
| SQL          | Structured Query Language                               | Query language for structured-data tools.                                    |
| SSE          | Server-Sent Events                                      | One-way streaming transport for token-by-token responses.                    |
| STT          | Speech-to-Text                                          | Transcribing audio into text.                                                |
| ToS          | Terms of Service                                        | Legal terms governing use of a site or service.                              |
| TPR          | True Positive Rate                                      | Recall / sensitivity; the ROC curve's y-axis.                                |
| TTL          | Time To Live                                            | Expiry duration, e.g. for approval tokens.                                   |
| TTS          | Text-to-Speech                                          | Synthesizing a speech waveform from text.                                    |
| UI           | User Interface                                          | Client surface that must handle refusals gracefully.                         |
| URI          | Uniform Resource Identifier                             | Identifier for a resource, e.g. an MCP resource.                             |
| URL          | Uniform Resource Locator                                | Web address of a resource.                                                   |
| UX           | User Experience                                         | The product-experience design concern of the module.                         |
| VAD          | Voice Activity Detection                                | Detects speech vs silence in an audio stream.                                |
| VPC          | Virtual Private Cloud                                   | Private network endpoints that mitigate model theft.                         |
| WAV          | Waveform Audio File Format                              | Uncompressed PCM audio container format.                                     |
| WebRTC       | Web Real-Time Communication                             | Browser real-time audio/video transport.                                     |
| XML          | Extensible Markup Language                              | Tag syntax used for delimiter-wrapping user input.                           |

See also: each module's `README.md` under `modules/` is the source of truth — this
glossary just collects the abbreviations they expand on first use.
