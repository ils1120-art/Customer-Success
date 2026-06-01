"""Step 3: gather similar past cases from Gmail and Discord.

The retriever first asks the LLM for compact search terms describing the new
case, then uses those terms to query both stores. Keyword search keeps the MVP
dependency-free; swap in embeddings later for better recall.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .discord_bot import DiscordBot
from .gmail_client import GmailClient
from .llm import LLMClient
from .models import CaseReference, EmailMessage

logger = logging.getLogger(__name__)

_KEYWORDS_SYSTEM = """You extract search terms for finding similar past support
cases. Given a new customer email, return 3-6 short, high-signal keywords or
phrases (product names, error text, feature names, the core problem) that would
appear in earlier conversations about the same kind of issue.

Respond with ONLY JSON: {"keywords": ["...", "..."]}"""


def extract_keywords(llm: LLMClient, model: str, email: EmailMessage) -> List[str]:
    try:
        data = llm.complete_json(
            model=model,
            system=_KEYWORDS_SYSTEM,
            user=email.as_context(),
            max_tokens=200,
            temperature=0.0,
        )
        keywords = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
    except ValueError:
        keywords = []
    # Always include subject words as a fallback signal.
    if not keywords:
        keywords = [w for w in email.subject.split() if len(w) > 3][:5]
    logger.info("Retrieval keywords: %s", keywords)
    return keywords


def gather_similar_cases(
    llm: LLMClient,
    model: str,
    email: EmailMessage,
    gmail: GmailClient,
    discord_bot: Optional[DiscordBot],
    max_cases: int = 5,
) -> List[CaseReference]:
    keywords = extract_keywords(llm, model, email)

    cases: List[CaseReference] = []

    # Gmail: build an OR query over keywords, excluding the current thread.
    if keywords:
        gmail_query = " OR ".join(f'"{k}"' for k in keywords)
        try:
            cases.extend(gmail.search_cases(gmail_query, limit=max_cases))
        except Exception:  # pragma: no cover - network/credential issues
            logger.exception("Gmail case search failed")

    # Discord: keyword scan of configured channels.
    if discord_bot is not None:
        try:
            cases.extend(discord_bot.search_cases(keywords, limit=max_cases))
        except Exception:  # pragma: no cover
            logger.exception("Discord case search failed")

    # Drop the case that is literally the incoming thread, then cap.
    deduped = [c for c in cases if email.thread_id not in c.location]
    logger.info("Found %d similar case(s)", len(deduped))
    return deduped[: max_cases * 2]
