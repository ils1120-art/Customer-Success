"""Thin wrapper around the Anthropic SDK.

Centralizes model selection, system-prompt caching, and JSON parsing so the
classifier and analyst modules stay focused on prompts, not plumbing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import anthropic

logger = logging.getLogger(__name__)

# Pull the first {...} JSON object out of a model response, even if it is
# wrapped in prose or a ```json fence.
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMClient:
    """Wraps :class:`anthropic.Anthropic` with helpers used by the agent."""

    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """Run a single-turn completion and return the text response.

        The system prompt is marked with ``cache_control`` so repeated calls
        with the same instructions (every email shares them) hit the prompt
        cache instead of re-billing the full system tokens.
        """
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

    def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Run a completion and parse the response as a JSON object."""
        raw = self.complete(
            model=model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _parse_json(raw)


def _parse_json(raw: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from a model response."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_RE.search(raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    logger.warning("Could not parse JSON from model response: %s", raw[:500])
    raise ValueError(f"Model did not return valid JSON: {raw[:200]}")
