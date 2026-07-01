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
  - OpenAI-style tools (shown in Part A) work identically for ollama,
    lmstudio, and nvidia because they implement the same API surface.
  - Anthropic uses a different wire format but the same conceptual loop
    (shown in Part B). The concept is the same; the JSON keys differ.

How to run:
  uv run python modules/02-llm-integration/py/05_tool_calling.py

Required env (pick one):
  LLM_PROVIDER=openai    + OPENAI_API_KEY
  LLM_PROVIDER=ollama    (local; model must support tools, e.g. llama3.2)
  LLM_PROVIDER=lmstudio  (local; load a tool-capable model + Start Server on :1234)
  ANTHROPIC_API_KEY for Part B

Local tool calling (Ollama / LM Studio):
  Part A talks the raw OpenAI wire format, and both local servers are
  OpenAI-compatible — so no code change is needed, only env vars:
    LM Studio:  LLM_PROVIDER=lmstudio  [LMSTUDIO_BASE_URL=http://localhost:1234/v1]
                [LMSTUDIO_CHAT_MODEL=qwen2.5-7b-instruct]
    Ollama:     LLM_PROVIDER=ollama    [OLLAMA_CHAT_MODEL=llama3.2]
  CAVEAT: tool calling depends on the *model*, not the server. Pick a
  tool-tuned instruct model (Qwen2.5-Instruct, Llama-3.1/3.2-Instruct,
  Mistral-Nemo). Small/quantized models often skip the tool call or emit
  malformed argument JSON — gate on `message.tool_calls` being truthy
  rather than trusting finish_reason if a local model misbehaves.
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

    # LLM_PROVIDER is the single source of truth: it selects the base_url, key,
    # and model together (mirrors llm_core's config). Part A uses the raw OpenAI
    # SDK on purpose, so we resolve that config here by hand.
    provider = os.getenv("LLM_PROVIDER", "ollama")
    provider_config: dict[str, dict[str, str | None]] = {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": None,
            "model": os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        },
        "ollama": {
            "api_key": "ollama",  # any non-empty string; local server ignores it
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            "model": os.getenv("OLLAMA_CHAT_MODEL", "llama3.2"),
        },
        "lmstudio": {
            "api_key": "lm-studio",
            "base_url": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            "model": os.getenv("LMSTUDIO_CHAT_MODEL", "qwen2.5-7b-instruct"),
        },
        "nvidia": {
            "api_key": os.getenv("NVIDIA_API_KEY", ""),
            "base_url": os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            "model": os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.1-8b-instruct"),
        },
    }
    if provider not in provider_config:
        raise SystemExit(
            f"Part A (OpenAI-style) supports: {', '.join(provider_config)}. "
            f'Got LLM_PROVIDER="{provider}". For anthropic, see Part B.'
        )
    config = provider_config[provider]
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    model = config["model"]
    print(f"Provider: {provider} / {model}")

    print(f"Question: {question}\n")

    # -------------------------------------------------------------------------
    # TODO 2: Send the initial request. Start a `messages` list with the user's
    #         question, then call client.chat.completions.create(...) passing
    #         model, messages, tools=[WEATHER_TOOL], and tool_choice="auto". Read
    #         the reply off response.choices[0].message and inspect
    #         response.choices[0].finish_reason.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # TODO 3: If finish_reason indicates a tool call ("tool_calls"):
    #         a) Append the assistant message to `messages` as-is (it holds the
    #            tool_calls the follow-up must answer).
    #         b) For each tool_call in message.tool_calls: json.loads its
    #            function.arguments, call get_weather(**args), and append a
    #            {"role": "tool", "tool_call_id": ..., "content": ...} message
    #            (tool_call_id must match the call's id so the model pairs them up).
    #         c) Call the API a second time with the extended `messages`.
    #         d) Print the final message.content.
    #         (A robust version would loop until finish_reason is no longer a tool
    #         call; one round-trip is enough for this exercise.)
    # -------------------------------------------------------------------------

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
    # TODO 4: Define the Anthropic tool dict. Same information as WEATHER_TOOL, but
    #         the fields are flatter: "name", "description", and "input_schema" (the
    #         JSON Schema object) — no nested "function" wrapper, and the schema key
    #         is "input_schema" rather than "parameters".
    # -------------------------------------------------------------------------

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
