"""Discord integration.

Two jobs:
  1. Search recent history of configured channels for similar past cases.
  2. Deliver the finished briefing to the operator (DM or a channel).

discord.py is async and login is relatively slow, so we log the client in once
and reuse it for the lifetime of the agent. The pipeline (sync) talks to it
through :meth:`DiscordBot.run_coro`, which marshals coroutines onto the bot's
event loop from any thread.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import List, Optional

import discord

from .models import CaseReference

logger = logging.getLogger(__name__)


class DiscordBot:
    def __init__(
        self,
        token: str,
        owner_id: int,
        search_channel_ids: List[int],
        briefing_channel_id: Optional[int] = None,
        history_limit: int = 500,
    ):
        self.token = token
        self.owner_id = owner_id
        self.search_channel_ids = search_channel_ids
        self.briefing_channel_id = briefing_channel_id
        self.history_limit = history_limit

        intents = discord.Intents.default()
        intents.message_content = True  # requires the Message Content Intent
        self._client = discord.Client(intents=intents)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ----- lifecycle ------------------------------------------------------
    def start(self, timeout: float = 30.0) -> None:
        """Log the bot in on a background thread and block until ready."""

        def _runner() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            @self._client.event
            async def on_ready() -> None:  # noqa: D401 - discord callback
                logger.info("Discord bot ready as %s", self._client.user)
                self._ready.set()

            try:
                self._loop.run_until_complete(self._client.start(self.token))
            except Exception:  # pragma: no cover - surfaced via logs
                logger.exception("Discord client stopped unexpectedly")
                self._ready.set()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=timeout):
            raise RuntimeError("Discord bot did not become ready in time")

    def close(self) -> None:
        if self._loop and self._client:
            fut = asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
            try:
                fut.result(timeout=10)
            except Exception:  # pragma: no cover
                pass

    def run_coro(self, coro, timeout: float = 60.0):
        """Run a coroutine on the bot's event loop from a sync caller."""
        if not self._loop:
            raise RuntimeError("Discord bot is not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ----- public (sync) API ---------------------------------------------
    def search_cases(self, keywords: List[str], limit: int = 5) -> List[CaseReference]:
        return self.run_coro(self._search_cases(keywords, limit))

    def send_briefing(self, markdown: str) -> None:
        self.run_coro(self._send_briefing(markdown))

    # ----- async implementations ------------------------------------------
    async def _search_cases(self, keywords: List[str], limit: int) -> List[CaseReference]:
        terms = [k.lower() for k in keywords if k.strip()]
        results: List[CaseReference] = []

        for channel_id in self.search_channel_ids:
            channel = self._client.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self._client.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden):
                    logger.warning("Cannot access Discord channel %s", channel_id)
                    continue

            try:
                async for message in channel.history(limit=self.history_limit):
                    content = (message.content or "").lower()
                    if not content:
                        continue
                    if terms and not any(term in content for term in terms):
                        continue
                    results.append(
                        CaseReference(
                            source="discord",
                            location=f"#{getattr(channel, 'name', channel_id)} "
                            f"({message.created_at:%Y-%m-%d})",
                            summary=message.content[:1500],
                            participants=[message.author.display_name],
                        )
                    )
                    if len(results) >= limit:
                        return results
            except discord.Forbidden:
                logger.warning("Missing read history permission on %s", channel_id)
        return results

    async def _send_briefing(self, markdown: str) -> None:
        target = None
        if self.briefing_channel_id:
            target = self._client.get_channel(self.briefing_channel_id)
            if target is None:
                target = await self._client.fetch_channel(self.briefing_channel_id)
        else:
            user = await self._client.fetch_user(self.owner_id)
            target = await user.create_dm()

        # Discord caps messages at 2000 chars; chunk if necessary.
        for chunk in _chunk(markdown, 1900):
            await target.send(chunk)
        logger.info("Sent CS briefing to Discord")


def _chunk(text: str, size: int) -> List[str]:
    if len(text) <= size:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > size:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks
