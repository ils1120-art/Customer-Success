"""Step 4: synthesize the three-part CS briefing from the email + past cases."""

from __future__ import annotations

import logging
from typing import List

from .llm import LLMClient
from .models import Briefing, CaseReference, EmailMessage

logger = logging.getLogger(__name__)

_SYSTEM = """You are the senior Customer Success analyst inside an automation
agent. You are given ONE new customer email and a set of SIMILAR PAST CASES
drawn from prior email threads and Discord discussions (including how those
cases were resolved and who was involved).

Produce a briefing for the human CS operator. Ground your "solution" and the
"involved" people in the past cases when they are relevant; if the past cases
don't cover it, say so and propose a reasonable next step. The operator — not
you — will send any reply, so write the client message as a ready-to-send draft
they can review and edit.

Respond with ONLY a JSON object:
{
  "problem": "1-3 sentences stating the customer's actual problem",
  "solution": "how this was/should be resolved, referencing similar cases",
  "involved": ["names or roles of people who helped resolve similar cases"],
  "client_message": "a polished draft reply to send to the client"
}"""


def _render_cases(cases: List[CaseReference]) -> str:
    if not cases:
        return "(No similar past cases were found.)"
    return "\n\n---\n\n".join(c.as_context() for c in cases)


def build_briefing(
    llm: LLMClient,
    model: str,
    email: EmailMessage,
    cases: List[CaseReference],
) -> Briefing:
    user = (
        "## NEW CUSTOMER EMAIL\n"
        f"{email.as_context()}\n\n"
        "## SIMILAR PAST CASES\n"
        f"{_render_cases(cases)}"
    )

    data = llm.complete_json(
        model=model,
        system=_SYSTEM,
        user=user,
        max_tokens=1500,
        temperature=0.3,
    )

    involved = data.get("involved", [])
    if isinstance(involved, str):
        involved = [involved]

    briefing = Briefing(
        problem=str(data.get("problem", "")).strip(),
        solution=str(data.get("solution", "")).strip(),
        involved=[str(p).strip() for p in involved if str(p).strip()],
        client_message=str(data.get("client_message", "")).strip(),
        source_email_subject=email.subject,
        source_email_sender=email.sender,
    )
    logger.info("Built briefing for %r", email.subject)
    return briefing
