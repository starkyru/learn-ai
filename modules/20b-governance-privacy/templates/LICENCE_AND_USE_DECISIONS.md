# Licence & use decisions — `<product name>`

> Owner: `<name / team>` · Last reviewed: `<YYYY-MM-DD>`

Every corpus source and model needs a **documented allowed-use decision, or is
excluded**. Record the decision here so "we're allowed to use this" is a fact with
an owner, not an assumption.

## Source licences

| Source                | Licence             | Attribution required | Commercial use | Allowed for this product? | Decision / notes         |
| --------------------- | ------------------- | -------------------- | -------------- | ------------------------- | ------------------------ |
| `<corpus / dataset>`  | `<MIT / CC-BY / …>` | `<yes/no; how>`      | `<yes/no>`     | `<yes / excluded>`        | `<why>`                  |
| `<scraped web pages>` | `<unknown / ToS>`   | `<…>`                | `<…>`          | `<…>`                     | `<robots/ToS reviewed?>` |

## Copyright & attribution

- How required attributions are surfaced to the user: `<citations / credits page>`.
- Third-party content whose copyright is unclear → `<excluded / legal review>`.

## Generated content

- **Ownership / rights** of model output under the provider's terms: `<summary>`.
- **Labelling:** generated content is disclosed as AI-generated where it matters:
  `<how>` (ties to the [model & data card](MODEL_AND_DATA_CARD.md) content types).

## Redistribution

- May outputs / derived data be redistributed, and under what terms? `<decision>`.
- May the corpus itself be redistributed (e.g. in an eval set)? `<decision>`.

## Provider terms

For each provider (LLM, embeddings, tools):

| Provider   | ToS constraints that bind us        | Trains on our data? / opt-out   | Output usage rights  |
| ---------- | ----------------------------------- | ------------------------------- | -------------------- |
| `<vendor>` | `<rate/use limits, prohibited use>` | `<yes/no; opt-out configured?>` | `<owned / licensed>` |

- Restricted or regulated data sent to a provider is covered by a DPA / contract:
  `<yes/no; link>`.
