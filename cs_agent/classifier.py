"""Step 1: decide whether an inbound email is a Customer Success matter."""

from __future__ import annotations

import logging

from .llm import LLMClient
from .models import Classification, EmailMessage

logger = logging.getLogger(__name__)

_SYSTEM = """You are the triage stage of a Customer Success (CS) automation agent.

Decide whether a single inbound email is a CUSTOMER SUCCESS matter, meaning it
comes from (or concerns) a customer/client and is about their experience using
the product or service. This includes: support questions, bug reports, how-to
requests, complaints, billing or account issues, onboarding, feature requests,
churn/cancellation risk, and renewal or upsell conversations.

It is NOT a CS matter when the email is: internal team chatter, newsletters,
marketing or sales outreach TO us, automated notifications, recruiting,
vendor/billing for our own tools, personal mail, or obvious spam.

Respond with ONLY a JSON object, no prose:
{
  "is_cs": true | false,
  "confidence": 0.0-1.0,
  "reason": "one short sentence"
}"""


def classify_email(llm: LLMClient, model: str, email: EmailMessage) -> Classification:
    data = llm.complete_json(
        model=model,
        system=_SYSTEM,
        user=email.as_context(),
        max_tokens=256,
        temperature=0.0,
    )
    classification = Classification(
        is_cs=bool(data.get("is_cs", False)),
        confidence=float(data.get("confidence", 0.0)),
        reason=str(data.get("reason", "")),
    )
    logger.info(
        "Classified %r -> is_cs=%s (%.2f): %s",
        email.subject,
        classification.is_cs,
        classification.confidence,
        classification.reason,
    )
    return classification
