"""
Task 5 — Tool / function calling 🟢

What this teaches:
  - The llm_core abstraction only exposes chat/stream/embed. Tool calling
    requires richer request shapes (tool definitions, tool_choice, etc.)
    that live in the raw provider SDKs. This is WHERE YOU GO BEYOND the
    abstraction — and why it exists as a thin wrapper, not a thick one.
  - The manual tool loop:
      1. Send messages + tool definitions to the model.
      2. Model replies with a tool_call (name + arguments JSON).
      3. You execute the tool locally (in your Python code).
      4. Append a "tool" result message and call the model again.
      5. Model uses the result to produce a final text answer.
  - OpenAI-style tools (shown in Part A) work identically for ollama and
    nvidia because they implement the same API surface.
  - Anthropic uses a different wire format but the same conceptual loop
    (shown in Part B). The concept is the same; the JSON keys differ.

How to run:
  uv run python modules/02-llm-integration/py/05_tool_calling.py

Required env (pick one):
  LLM_PROVIDER=openai  + OPENAI_API_KEY
  LLM_PROVIDER=ollama  (with a model that supports tool calling, e.g. llama3.2)
  ANTHROPIC_API_KEY for Part B
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()

# ---------------------------------------------------------------------------
# Fake tool: get_weather
# In a real app this would call a weather API. Here we return hardcoded data
# so the exercise works without a real weather API key.
# ---------------------------------------------------------------------------
FAKE_WEATHER: dict[str, dict[str, object]] = {
    "london":    {"temp": 15, "condition": "cloudy"},
    "tokyo":     {"temp": 22, "condition": "sunny"},
    "new_york":  {"temp": 18, "condition": "partly cloudy"},
}


def get_weather(location: str, unit: str = "celsius") -> str:
    """Return fake weather JSON for a location.

    TODO: make the data more varied by city so the model's final answer
    reflects different conditions for different places it asks about.
    """
    key = location.lower().replace(" ", "_")
    weather = FAKE_WEATHER.get(key, {"temp": 20, "condition": "unknown"})
    temp = weather["temp"]
    if unit == "fahrenheit":
        temp = int(temp) * 9 // 5 + 32  # type: ignore[operator]
    return json.dumps({"location": location, "temperature": temp, "unit": unit, "condition": weather["condition"]})


# ---------------------------------------------------------------------------
# PART A: OpenAI-style tool calling
# This works for OpenAI, Ollama (if model supports tools), and NVIDIA.
# ---------------------------------------------------------------------------

# TODO 1: Define the tool schema in OpenAI format as a Python dict.
#         It needs: type "function", function.name, function.description,
#         function.parameters (JSON Schema object with required fields).
WEATHER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "TODO: write a description so the model knows when to call this",
        "parameters": {
            # TODO: fill in the JSON Schema for the parameters
            # properties: location (string), unit (string, enum celsius/fahrenheit)
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def run_openai_tool_loop(question: str) -> None:
    print("=== Part A: OpenAI-style tool calling ===\n")

    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        client = OpenAI(
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )
        model = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
    else:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    print(f"Question: {question}\n")

    # -------------------------------------------------------------------------
    # TODO 2: Send the initial request with the tool definition.
    #         Use client.chat.completions.create(model, messages, tools, tool_choice="auto")
    # -------------------------------------------------------------------------
    # messages = [{"role": "user", "content": question}]
    # response = client.chat.completions.create(
    #     model=model, messages=messages, tools=[WEATHER_TOOL], tool_choice="auto"
    # )
    # message = response.choices[0].message
    # print("First response finish_reason:", response.choices[0].finish_reason)

    # -------------------------------------------------------------------------
    # TODO 3: Check if finish_reason == "tool_calls". If so:
    #         a) Append the assistant message to messages.
    #         b) For each tool_call in message.tool_calls:
    #            - Parse the arguments JSON.
    #            - Call get_weather() with those args.
    #            - Append a {"role": "tool", "tool_call_id": ..., "content": ...} message.
    #         c) Call the API again with the updated messages.
    #         d) Print the final text response.
    # -------------------------------------------------------------------------
    # if response.choices[0].finish_reason == "tool_calls" and message.tool_calls:
    #     messages.append(message)
    #     for tool_call in message.tool_calls:
    #         args = json.loads(tool_call.function.arguments)
    #         result = get_weather(**args)
    #         print(f"Tool called: {tool_call.function.name}({tool_call.function.arguments})")
    #         print(f"Tool result: {result}\n")
    #         messages.append({
    #             "role": "tool",
    #             "tool_call_id": tool_call.id,
    #             "content": result,
    #         })
    #     response = client.chat.completions.create(model=model, messages=messages)
    #     message = response.choices[0].message
    # print("Final answer:", message.content)

    print("TODO: implement the tool loop above.")


# ---------------------------------------------------------------------------
# PART B: Anthropic-style tool calling
# Different wire format, same conceptual loop.
# ---------------------------------------------------------------------------

def run_anthropic_tool_loop(question: str) -> None:
    print("\n=== Part B: Anthropic-style tool calling ===\n")

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    print(f"Question: {question}\n")

    # -------------------------------------------------------------------------
    # TODO 4: Define the Anthropic tool. Format differs from OpenAI:
    #         {"name": ..., "description": ..., "input_schema": {"type": "object", ...}}
    # -------------------------------------------------------------------------
    # anthropic_tool = {
    #     "name": "get_weather",
    #     "description": "...",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": { ... },
    #         "required": [ ... ],
    #     },
    # }

    # -------------------------------------------------------------------------
    # TODO 5: Send the initial request.
    #         client.messages.create(model, max_tokens, tools=[anthropic_tool], messages)
    #         Check response.stop_reason == "tool_use".
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # TODO 6: For each content block with type "tool_use":
    #         - Execute the tool.
    #         - Append the assistant message (as-is) to messages.
    #         - Append a user message with:
    #             content=[{"type": "tool_result", "tool_use_id": ..., "content": ...}]
    #         - Call the API again and print the final text.
    #         KEY DIFFERENCE: Anthropic tool results go inside a *user* message,
    #         not a top-level "tool" role. This reflects different conversation
    #         structure conventions between providers.
    # -------------------------------------------------------------------------

    print("TODO: implement the Anthropic tool loop above.")
    print("(Skip this part if you don't have an ANTHROPIC_API_KEY)")


def main() -> None:
    question = "What's the weather like in London and Tokyo right now?"

    # Run OpenAI-compatible path (also works with ollama)
    run_openai_tool_loop(question)

    # Run Anthropic path (requires ANTHROPIC_API_KEY)
    if os.getenv("ANTHROPIC_API_KEY"):
        run_anthropic_tool_loop(question)
    else:
        print("\nSkipping Part B (no ANTHROPIC_API_KEY set).")


if __name__ == "__main__":
    main()
