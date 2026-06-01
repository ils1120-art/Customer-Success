"""In-memory fakes for Gmail, Discord, and Claude used by the tests."""

from __future__ import annotations

import json
from typing import Dict, List

from cs_agent.models import CaseReference, EmailMessage


class FakeLLM:
    """Returns canned JSON keyed by which system prompt is in play.

    We sniff a distinctive phrase from each module's system prompt so a single
    fake can stand in for the classifier, keyword extraction, and the analyst.
    """

    def __init__(self, *, is_cs: bool = True):
        self.is_cs = is_cs
        self.calls: List[str] = []

    def complete(self, *, model, system, user, max_tokens=1024, temperature=0.2) -> str:
        self.calls.append(system)
        if "triage stage" in system:
            return json.dumps(
                {"is_cs": self.is_cs, "confidence": 0.95, "reason": "test"}
            )
        if "search terms" in system:
            return json.dumps({"keywords": ["login", "error", "billing"]})
        if "senior Customer Success analyst" in system:
            return json.dumps(
                {
                    "problem": "Customer cannot log in.",
                    "solution": "Reset their SSO token, as in the prior case.",
                    "involved": ["Alice (Support)", "Bob (Eng)"],
                    "client_message": "Hi! We've reset your access, please retry.",
                }
            )
        return "{}"

    def complete_json(self, *, model, system, user, max_tokens=1024, temperature=0.2):
        return json.loads(self.complete(
            model=model, system=system, user=user,
            max_tokens=max_tokens, temperature=temperature,
        ))


class FakeGmail:
    def __init__(self, messages: Dict[str, EmailMessage]):
        self._messages = messages
        self.flagged: List[str] = []

    def list_new_messages(self, query, max_results=25) -> List[str]:
        return list(self._messages.keys())

    def get_message(self, message_id) -> EmailMessage:
        return self._messages[message_id]

    def flag_as_cs(self, thread_id) -> None:
        self.flagged.append(thread_id)

    def search_cases(self, query, limit=5) -> List[CaseReference]:
        return [
            CaseReference(
                source="gmail",
                location="thread T-OLD — Login issue",
                summary="Previously fixed a login error by resetting SSO.",
                participants=["customer@old.com"],
            )
        ]


class FakeDiscord:
    def __init__(self):
        self.sent: List[str] = []

    def search_cases(self, keywords, limit=5) -> List[CaseReference]:
        return [
            CaseReference(
                source="discord",
                location="#cs-team (2026-05-01)",
                summary="Bob reset the SSO token to fix the same login error.",
                participants=["Bob"],
            )
        ]

    def send_briefing(self, markdown) -> None:
        self.sent.append(markdown)
