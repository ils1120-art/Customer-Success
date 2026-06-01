"""Orchestrates the end-to-end CS flow for a batch of new emails.

    poll → classify → (label + retrieve + brief + notify)

The pipeline holds references to the integration clients but contains no I/O
details of its own, which keeps it easy to unit-test against fakes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from . import analyst, classifier, retriever
from .config import Config
from .discord_bot import DiscordBot
from .gmail_client import GmailClient
from .llm import LLMClient
from .models import Briefing, EmailMessage
from .state import ProcessedStore

logger = logging.getLogger(__name__)

# Below this confidence we still treat as non-CS but log for review.
_CS_THRESHOLD = 0.5


@dataclass
class ProcessResult:
    email: EmailMessage
    is_cs: bool
    briefing: Optional[Briefing] = None


class Pipeline:
    def __init__(
        self,
        config: Config,
        llm: LLMClient,
        gmail: GmailClient,
        discord_bot: Optional[DiscordBot],
        state: ProcessedStore,
        dry_run: bool = False,
    ):
        self.config = config
        self.llm = llm
        self.gmail = gmail
        self.discord_bot = discord_bot
        self.state = state
        self.dry_run = dry_run

    def run_once(self) -> List[ProcessResult]:
        """Process every unseen email matching the polling query."""
        results: List[ProcessResult] = []
        message_ids = self.gmail.list_new_messages(self.config.gmail_poll_query)
        logger.info("Polled Gmail: %d candidate message(s)", len(message_ids))

        for message_id in message_ids:
            if self.state.has(message_id):
                continue
            try:
                results.append(self._process_message(message_id))
            except Exception:  # pragma: no cover - keep the loop alive
                logger.exception("Failed to process message %s", message_id)
                continue
            # Mark processed regardless of CS outcome so we don't re-handle it.
            self.state.add(message_id)

        return results

    def _process_message(self, message_id: str) -> ProcessResult:
        email = self.gmail.get_message(message_id)

        # Step 1: classify.
        classification = classifier.classify_email(
            self.llm, self.config.classifier_model, email
        )
        is_cs = classification.is_cs and classification.confidence >= _CS_THRESHOLD
        if not is_cs:
            return ProcessResult(email=email, is_cs=False)

        # Step 2: flag the thread as CS in Gmail.
        if not self.dry_run:
            self.gmail.flag_as_cs(email.thread_id)

        # Step 3: retrieve similar past cases (Gmail + Discord).
        cases = retriever.gather_similar_cases(
            self.llm,
            self.config.classifier_model,
            email,
            self.gmail,
            self.discord_bot,
            max_cases=self.config.max_similar_cases,
        )

        # Step 4: build the briefing.
        briefing = analyst.build_briefing(
            self.llm, self.config.analyst_model, email, cases
        )

        # Step 5: deliver to the operator on Discord (never to the client).
        if not self.dry_run and self.discord_bot is not None:
            self.discord_bot.send_briefing(briefing.to_discord_markdown())

        return ProcessResult(email=email, is_cs=True, briefing=briefing)
