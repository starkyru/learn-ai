# Training and Fine-Tuning Large Language Models

Training a large language model (LLM) from scratch is a massive undertaking: GPT-3
consumed roughly 3.14×10²³ floating-point operations and used 570 GB of text data.
Understanding the stages of training clarifies why fine-tuned models behave so
differently from their base counterparts.

## Pre-training

In **pre-training**, the model learns to predict the next token in a huge corpus of
text drawn from books, web pages, code repositories, and other sources. The objective
is simple — minimise the average negative log-likelihood of the next token — but at
scale it forces the model to learn grammar, facts, reasoning patterns, and world
knowledge.

The result is a **base model**: very knowledgeable, but raw. Ask it a question and it
may continue the text in an unhelpful direction (e.g., generating more questions)
because it was trained to complete text, not to answer helpfully.

## Supervised fine-tuning (SFT)

SFT adapts a base model to follow instructions. A small dataset of high-quality
(prompt, ideal response) pairs is curated by human contractors. The model is
fine-tuned on these examples with a standard language-modelling loss. This teaches
the model the format and style of helpful responses.

## Reinforcement learning from human feedback (RLHF)

RLHF further aligns the model with human preferences:
1. **Reward model**: human raters compare pairs of model responses and rank them.
   A separate model is trained to predict these preferences (the reward model).
2. **RL fine-tuning**: the LLM is updated using PPO (Proximal Policy Optimisation)
   to maximise the reward model's score, subject to a KL-divergence penalty that
   prevents the model from drifting too far from the SFT checkpoint.

## Parameter-efficient fine-tuning (PEFT)

Fine-tuning all parameters of a large model is expensive. **LoRA** (Low-Rank
Adaptation) instead inserts small trainable matrices into each attention layer and
freezes the original weights. This reduces the number of trainable parameters by
orders of magnitude while achieving performance close to full fine-tuning.
