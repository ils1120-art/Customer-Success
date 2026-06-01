"""Gmail integration: poll for new mail, read threads, apply the CS label.

Uses OAuth user credentials (Desktop client). On first run it opens a browser
to authorize and caches a token; subsequent runs refresh silently.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .models import CaseReference, EmailMessage

logger = logging.getLogger(__name__)

# Read mail + modify labels. We never send, in keeping with "no client replies".
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str, cs_label: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.cs_label = cs_label
        self._service = None
        self._label_cache: Dict[str, str] = {}

    # ----- auth -----------------------------------------------------------
    def connect(self) -> None:
        creds: Optional[Credentials] = None
        try:
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        except (FileNotFoundError, ValueError):
            creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        logger.info("Connected to Gmail API")

    # ----- polling --------------------------------------------------------
    def list_new_messages(self, query: str, max_results: int = 25) -> List[str]:
        """Return message IDs matching the polling query (newest first)."""
        resp = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        return [m["id"] for m in resp.get("messages", [])]

    def get_message(self, message_id: str) -> EmailMessage:
        msg = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return _parse_message(msg)

    # ----- labeling -------------------------------------------------------
    def ensure_label(self, name: str) -> str:
        """Return the label ID, creating the label if it does not exist."""
        if name in self._label_cache:
            return self._label_cache[name]

        labels = (
            self._service.users().labels().list(userId="me").execute().get("labels", [])
        )
        for label in labels:
            if label["name"].lower() == name.lower():
                self._label_cache[name] = label["id"]
                return label["id"]

        created = (
            self._service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        self._label_cache[name] = created["id"]
        logger.info("Created Gmail label %r", name)
        return created["id"]

    def flag_as_cs(self, thread_id: str) -> None:
        """Apply the configured CS label to an entire thread."""
        label_id = self.ensure_label(self.cs_label)
        self._service.users().threads().modify(
            userId="me",
            id=thread_id,
            body={"addLabelIds": [label_id]},
        ).execute()
        logger.info("Flagged thread %s as %s", thread_id, self.cs_label)

    # ----- retrieval ------------------------------------------------------
    def search_cases(self, query: str, limit: int = 5) -> List[CaseReference]:
        """Search past threads for similar cases, summarized for context.

        Returns lightweight references; the analyst LLM does the synthesis.
        """
        resp = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=limit)
            .execute()
        )
        cases: List[CaseReference] = []
        seen_threads = set()
        for entry in resp.get("messages", []):
            msg = self.get_message(entry["id"])
            if msg.thread_id in seen_threads:
                continue
            seen_threads.add(msg.thread_id)
            cases.append(
                CaseReference(
                    source="gmail",
                    location=f"thread {msg.thread_id} — {msg.subject}",
                    summary=msg.body[:1500],
                    participants=[msg.sender],
                )
            )
        return cases


def _header(headers: List[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_message(msg: dict) -> EmailMessage:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    received_at: Optional[datetime] = None
    date_header = _header(headers, "Date")
    if date_header:
        try:
            received_at = parsedate_to_datetime(date_header)
        except (TypeError, ValueError):
            received_at = None
    if received_at is None and msg.get("internalDate"):
        received_at = datetime.fromtimestamp(
            int(msg["internalDate"]) / 1000, tz=timezone.utc
        )

    return EmailMessage(
        id=msg["id"],
        thread_id=msg.get("threadId", msg["id"]),
        sender=_header(headers, "From"),
        subject=_header(headers, "Subject") or "(no subject)",
        body=_extract_body(payload) or msg.get("snippet", ""),
        received_at=received_at,
    )


def _extract_body(payload: dict) -> str:
    """Walk the MIME tree and return the best-effort plain-text body."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime == "text/plain" and body_data:
        return _decode(body_data)

    parts = payload.get("parts", [])
    # Prefer text/plain anywhere in the tree.
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode(part["body"]["data"])
    # Recurse into multipart containers.
    for part in parts:
        if part.get("parts"):
            found = _extract_body(part)
            if found:
                return found
    # Fall back to the top-level body even if not text/plain.
    if body_data:
        return _decode(body_data)
    return ""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
