"""End-to-end pipeline tests against in-memory fakes (no live credentials)."""

from __future__ import annotations

import os

import pytest

from cs_agent.config import Config
from cs_agent.models import EmailMessage
from cs_agent.pipeline import Pipeline
from cs_agent.state import ProcessedStore
from tests.fakes import FakeDiscord, FakeGmail, FakeLLM


def _config(tmp_path) -> Config:
    return Config(
        anthropic_api_key="test",
        classifier_model="m",
        analyst_model="m",
        gmail_credentials_file="creds.json",
        gmail_token_file="token.json",
        gmail_poll_query="is:unread",
        gmail_cs_label="CS",
        discord_bot_token="t",
        discord_owner_id=123,
        discord_briefing_channel_id=None,
        discord_search_channel_ids=[1],
        max_similar_cases=3,
        state_file=str(tmp_path / "processed.json"),
    )


def _email(msg_id="M1") -> EmailMessage:
    return EmailMessage(
        id=msg_id,
        thread_id="T1",
        sender="customer@acme.com",
        subject="Can't log in to my account",
        body="I keep getting an SSO error when I try to log in. Please help.",
    )


def _build(tmp_path, *, is_cs=True, dry_run=False):
    config = _config(tmp_path)
    gmail = FakeGmail({"M1": _email()})
    discord = FakeDiscord()
    llm = FakeLLM(is_cs=is_cs)
    state = ProcessedStore(config.state_file)
    pipeline = Pipeline(config, llm, gmail, discord, state, dry_run=dry_run)
    return pipeline, gmail, discord


def test_cs_email_is_flagged_and_briefed(tmp_path):
    pipeline, gmail, discord = _build(tmp_path)

    results = pipeline.run_once()

    assert len(results) == 1
    result = results[0]
    assert result.is_cs is True
    assert result.briefing is not None

    # Thread was flagged in Gmail.
    assert gmail.flagged == ["T1"]

    # A briefing was sent to Discord and contains all three sections.
    assert len(discord.sent) == 1
    msg = discord.sent[0]
    assert "1. The problem" in msg
    assert "2. The solution" in msg
    assert "3. Suggested message to the client" in msg
    # And it draws on retrieved people.
    assert "Bob" in msg


def test_non_cs_email_is_ignored(tmp_path):
    pipeline, gmail, discord = _build(tmp_path, is_cs=False)

    results = pipeline.run_once()

    assert results[0].is_cs is False
    assert gmail.flagged == []  # not labeled
    assert discord.sent == []  # not briefed


def test_dry_run_does_not_label_or_send(tmp_path):
    pipeline, gmail, discord = _build(tmp_path, dry_run=True)

    results = pipeline.run_once()

    assert results[0].is_cs is True
    assert results[0].briefing is not None
    assert gmail.flagged == []
    assert discord.sent == []


def test_already_processed_message_is_skipped(tmp_path):
    pipeline, gmail, discord = _build(tmp_path)

    pipeline.run_once()
    discord.sent.clear()
    gmail.flagged.clear()

    # Second poll returns the same message id; it must be skipped.
    results = pipeline.run_once()
    assert results == []
    assert discord.sent == []
    assert gmail.flagged == []


def test_briefing_markdown_marks_no_client_send(tmp_path):
    pipeline, _, discord = _build(tmp_path)
    pipeline.run_once()
    assert "I will not send this" in discord.sent[0]
