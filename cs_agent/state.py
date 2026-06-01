"""Tracks which Gmail messages have already been processed.

A tiny JSON file is plenty for an MVP and keeps the agent idempotent across
restarts so the same email is never briefed twice.
"""

from __future__ import annotations

import json
import os
from typing import Set


class ProcessedStore:
    def __init__(self, path: str):
        self.path = path
        self._seen: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._seen = set(json.load(fh))
            except (json.JSONDecodeError, ValueError):
                self._seen = set()

    def has(self, message_id: str) -> bool:
        return message_id in self._seen

    def add(self, message_id: str) -> None:
        self._seen.add(message_id)
        self._flush()

    def _flush(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(sorted(self._seen), fh, indent=2)
