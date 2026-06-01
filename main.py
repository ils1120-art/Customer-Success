"""Entry point for the Customer Success agent.

Usage:
    python main.py            # continuous polling loop
    python main.py --once     # process one batch and exit (for cron)
    python main.py --dry-run  # classify + brief, but don't label or notify
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from cs_agent.config import load_config
from cs_agent.discord_bot import DiscordBot
from cs_agent.gmail_client import GmailClient
from cs_agent.llm import LLMClient
from cs_agent.pipeline import Pipeline
from cs_agent.state import ProcessedStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cs_agent.main")


def _summarize(results) -> None:
    cs = [r for r in results if r.is_cs]
    logger.info(
        "Batch complete: %d processed, %d flagged as CS", len(results), len(cs)
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Customer Success automation agent")
    parser.add_argument("--once", action="store_true", help="process one batch and exit")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="don't apply Gmail labels or send Discord briefings",
    )
    parser.add_argument(
        "--no-discord",
        action="store_true",
        help="skip Discord entirely (Gmail-only run; useful for debugging)",
    )
    args = parser.parse_args(argv)

    config = load_config()
    config.require_runtime_secrets()

    llm = LLMClient(config.anthropic_api_key)

    gmail = GmailClient(
        config.gmail_credentials_file,
        config.gmail_token_file,
        config.gmail_cs_label,
    )
    gmail.connect()

    discord_bot = None
    if not args.no_discord:
        discord_bot = DiscordBot(
            token=config.discord_bot_token,
            owner_id=config.discord_owner_id,
            search_channel_ids=config.discord_search_channel_ids,
            briefing_channel_id=config.discord_briefing_channel_id,
            history_limit=config.discord_history_limit,
        )
        discord_bot.start()

    state = ProcessedStore(config.state_file)
    pipeline = Pipeline(config, llm, gmail, discord_bot, state, dry_run=args.dry_run)

    try:
        if args.once:
            _summarize(pipeline.run_once())
        else:
            logger.info(
                "Starting polling loop (every %ss). Ctrl-C to stop.",
                config.poll_interval_seconds,
            )
            while True:
                _summarize(pipeline.run_once())
                time.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        if discord_bot is not None:
            discord_bot.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
