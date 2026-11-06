"""Talking to the AI model, and reading JSON out of its replies."""

from __future__ import annotations

import json
import re


class LLMError(RuntimeError):
    pass


class AnthropicLLM:
    """Calls Claude through the Anthropic API. The key stays on the server."""

    def __init__(self, api_key: str | None, model: str, timeout: float = 150.0):
        if not api_key:
            raise LLMError("The resume agent is not set up yet: ANTHROPIC_API_KEY is missing on the server.")
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1)
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        import anthropic

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMError(f"The AI model could not be reached ({type(exc).__name__}). Try again in a minute.") from exc
        usage = getattr(response, "usage", None)
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        return "".join(getattr(block, "text", "") for block in response.content)


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in the model reply.")
    return json.loads(cleaned[start : end + 1])


def complete_json(llm, system: str, user: str, max_tokens: int = 4000) -> dict:
    """Ask for JSON, and retry once with a reminder if the reply is not valid JSON."""
    try:
        return parse_json(llm.complete(system, user, max_tokens))
    except (ValueError, json.JSONDecodeError):
        retry = user + "\n\nYour last reply was not valid JSON. Reply with only the JSON object."
        try:
            return parse_json(llm.complete(system, retry, max_tokens))
        except (ValueError, json.JSONDecodeError) as exc:
            raise LLMError("The model did not return valid JSON. Try again.") from exc
