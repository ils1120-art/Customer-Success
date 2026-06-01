"""Plain data structures shared across the pipeline.

Keeping these provider-agnostic means the Gmail, Discord, and Claude modules
all speak the same vocabulary without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class EmailMessage:
    """A single inbound email under consideration."""

    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: Optional[datetime] = None

    def as_context(self) -> str:
        """Render the email as text for an LLM prompt."""
        when = self.received_at.isoformat() if self.received_at else "unknown"
        return (
            f"From: {self.sender}\n"
            f"Subject: {self.subject}\n"
            f"Received: {when}\n\n"
            f"{self.body}"
        )


@dataclass
class Classification:
    """Result of the CS / not-CS decision."""

    is_cs: bool
    confidence: float
    reason: str


@dataclass
class CaseReference:
    """A past case surfaced by the retriever (from Gmail or Discord)."""

    source: str  # "gmail" or "discord"
    location: str  # thread id, channel name, link, etc.
    summary: str
    participants: List[str] = field(default_factory=list)

    def as_context(self) -> str:
        people = ", ".join(self.participants) if self.participants else "unknown"
        return (
            f"[{self.source}] {self.location}\n"
            f"Participants: {people}\n"
            f"{self.summary}"
        )


@dataclass
class Briefing:
    """The three-part CS briefing delivered to the operator on Discord."""

    problem: str
    solution: str
    involved: List[str]
    client_message: str
    source_email_subject: str = ""
    source_email_sender: str = ""

    def to_discord_markdown(self) -> str:
        """Format the briefing as a Discord message."""
        people = ", ".join(self.involved) if self.involved else "_to be determined_"
        header = "🎫 **New CS case flagged**"
        if self.source_email_subject:
            header += f"\n> **{self.source_email_subject}**"
        if self.source_email_sender:
            header += f"\n> from `{self.source_email_sender}`"
        return (
            f"{header}\n\n"
            f"**1. The problem**\n{self.problem}\n\n"
            f"**2. The solution & who's involved**\n{self.solution}\n"
            f"_Involved:_ {people}\n\n"
            f"**3. Suggested message to the client** _(review before sending — "
            f"I will not send this)_\n>>> {self.client_message}"
        )
