"""
Task 4 — Structured output 🟢

What this teaches:
  - LLMs output text. Getting structured data (JSON, typed objects) out
    of them requires either JSON mode, schema-constrained decoding, or a
    careful prompt + parser — and validation to catch hallucinated fields.
  - Pydantic lets you declare a schema and parse/validate in one step.
    If the model's JSON doesn't match, you get a clear ValidationError.
  - Why schemas matter: without them you're doing json.loads() and hoping
    for the best. Pydantic validation catches errors at the boundary
    between the model and your application code.

Dependencies:
  pydantic is in the base deps (pyproject.toml).

How to run:
  uv run python modules/02-llm-integration/py/04_structured_output.py
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError

from llm_core import get_provider


# ---------------------------------------------------------------------------
# TODO 1: Define a Pydantic model for the data you want to extract.
#         Start with the recipe below, then try your own schema.
# ---------------------------------------------------------------------------
class Ingredient(BaseModel):
    item: str
    amount: str


class Recipe(BaseModel):
    name: str = Field(description="Name of the dish")
    ingredients: list[Ingredient] = Field(description="List of ingredients with amounts")
    steps: list[str] = Field(description="Ordered cooking steps")
    prep_time_minutes: int = Field(gt=0, description="Prep time in minutes")
    servings: int = Field(gt=0)


# ---------------------------------------------------------------------------
# TODO 2: Build a prompt that instructs the model to respond in JSON matching
#         the schema above. Embedding the schema (or a description of it)
#         in the system message is the most portable approach.
# ---------------------------------------------------------------------------
def build_prompt(request: str) -> str:
    return f"""You are a recipe assistant. When asked for a recipe, respond ONLY with
valid JSON matching this exact structure — no markdown, no prose, just JSON:
{{
  "name": "string",
  "ingredients": [{{"item": "string", "amount": "string"}}],
  "steps": ["string"],
  "prep_time_minutes": number,
  "servings": number
}}

User request: {request}"""


# ---------------------------------------------------------------------------
# TODO 3: Implement parse_recipe.
#         a) Strip markdown code fences if present (the model often wraps JSON
#            in ```json ... ```).  Use re.sub or str.replace.
#         b) Call json.loads() on the cleaned text — wrap in try/except json.JSONDecodeError.
#         c) Pass the parsed dict to Recipe.model_validate() for Pydantic validation.
#         d) Return the validated Recipe object.
#         Raise a descriptive ValueError if either step fails.
# ---------------------------------------------------------------------------
def parse_recipe(raw_text: str) -> Recipe:
    # TODO: implement
    # 1. Strip code fences:
    #    clean = re.sub(r"```json?\n?", "", raw_text).replace("```", "").strip()
    # 2. Parse JSON:
    #    data = json.loads(clean)
    # 3. Validate with Pydantic:
    #    return Recipe.model_validate(data)
    raise NotImplementedError("parse_recipe not implemented yet")


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")

    request = "a simple pasta carbonara for 2 people"
    print(f'Requesting recipe for: "{request}"\n')

    # -------------------------------------------------------------------------
    # TODO 4: Call llm.chat() with a single user message (build_prompt(request))
    #         and temperature=0.1 (via ChatOptions) to make output more deterministic.
    #         Then call parse_recipe(result.text) and pretty-print the result.
    # -------------------------------------------------------------------------

    # from llm_core import ChatOptions
    # result = llm.chat(
    #     [{"role": "user", "content": build_prompt(request)}],
    #     ChatOptions(temperature=0.1),
    # )
    # print("Raw response:\n", result.text, "\n")
    # recipe = parse_recipe(result.text)
    # print("Parsed recipe:")
    # print(json.dumps(recipe.model_dump(), indent=2))

    print("TODO: implement the chat call and parsing above.")

    # -------------------------------------------------------------------------
    # TODO 5: Add a retry loop — if parse_recipe raises, append an error message
    #         to the history and ask the model to fix its output. Try up to 3
    #         times before giving up.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # TODO 6 (stretch): Try a different schema — extract structured data from
    #         unstructured text. Give it a news article snippet and extract:
    #         { headline, date, people: list[str], summary }.
    #         Notice how Pydantic validation reveals when the model misses a field.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
