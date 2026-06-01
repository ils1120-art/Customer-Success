"""Configuration loaded from environment variables.

All knobs the agent needs live here so the rest of the code never touches
``os.environ`` directly. Call :func:`load_config` once at startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


def _split_ids(raw: str) -> List[int]:
    """Parse a comma-separated list of Discord snowflake IDs into ints."""
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.append(int(part))
    return ids


@dataclass
class Config:
    # Anthropic / Claude
    anthropic_api_key: str
    classifier_model: str
    analyst_model: str

    # Gmail
    gmail_credentials_file: str
    gmail_token_file: str
    gmail_poll_query: str
    gmail_cs_label: str

    # Discord
    discord_bot_token: str
    discord_owner_id: int
    discord_briefing_channel_id: int | None
    discord_search_channel_ids: List[int] = field(default_factory=list)
    discord_history_limit: int = 500

    # Agent behavior
    poll_interval_seconds: int = 60
    max_similar_cases: int = 5
    state_file: str = "state/processed.json"

    def require_runtime_secrets(self) -> None:
        """Validate that secrets needed for a live run are present.

        Raises a clear error rather than letting an SDK fail cryptically later.
        """
        missing = []
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if not self.discord_bot_token:
            missing.append("DISCORD_BOT_TOKEN")
        if not self.discord_owner_id:
            missing.append("DISCORD_OWNER_ID")
        if missing:
            raise RuntimeError(
                "Missing required configuration: " + ", ".join(missing)
            )


def load_config() -> Config:
    """Build a :class:`Config` from the environment (and a local ``.env``)."""
    load_dotenv()

    owner_id_raw = os.getenv("DISCORD_OWNER_ID", "").strip()
    briefing_channel_raw = os.getenv("DISCORD_BRIEFING_CHANNEL_ID", "").strip()

    return Config(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        classifier_model=os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001"),
        analyst_model=os.getenv("ANALYST_MODEL", "claude-sonnet-4-6"),
        gmail_credentials_file=os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
        gmail_token_file=os.getenv("GMAIL_TOKEN_FILE", "token.json"),
        gmail_poll_query=os.getenv("GMAIL_POLL_QUERY", "in:inbox is:unread newer_than:1d"),
        gmail_cs_label=os.getenv("GMAIL_CS_LABEL", "CS"),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
        discord_owner_id=int(owner_id_raw) if owner_id_raw else 0,
        discord_briefing_channel_id=int(briefing_channel_raw) if briefing_channel_raw else None,
        discord_search_channel_ids=_split_ids(os.getenv("DISCORD_SEARCH_CHANNEL_IDS", "")),
        discord_history_limit=int(os.getenv("DISCORD_HISTORY_LIMIT", "500")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        max_similar_cases=int(os.getenv("MAX_SIMILAR_CASES", "5")),
        state_file=os.getenv("STATE_FILE", "state/processed.json"),
    )
