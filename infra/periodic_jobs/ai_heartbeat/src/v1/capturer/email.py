#!/usr/bin/env python3
"""
L0 Capturer: Gmail
Fetches today's emails (subject + sender only, no body).
Returns a list of raw signal dicts conforming to the raw signal schema.
"""
import os
import logging
import uuid
import base64
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_service(credentials_path: str, token_path: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _extract_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def capture(target_date: str, credentials_path: str, token_path: str) -> list[dict]:
    """
    Capture emails received on target_date (YYYY-MM-DD).
    Returns list of raw signal dicts (subject + sender only, no body).
    """
    try:
        service = _get_service(credentials_path, token_path)
    except Exception as e:
        logger.warning("Email: failed to initialize service: %s", e)
        return []

    # Gmail search query: messages on target_date
    query = f"after:{target_date} before:{_next_date(target_date)}"

    try:
        response = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
    except Exception as e:
        logger.warning("Email: API list call failed: %s", e)
        return []

    messages = response.get("messages", [])
    signals = []
    captured_at = datetime.now(timezone.utc).isoformat()

    for msg_ref in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata",
                     metadataHeaders=["Subject", "From"])
                .execute()
            )
        except Exception as e:
            logger.warning("Email: failed to fetch message %s: %s", msg_ref["id"], e)
            continue

        headers = msg.get("payload", {}).get("headers", [])
        subject = _extract_header(headers, "Subject") or "(no subject)"
        sender = _extract_header(headers, "From") or "(unknown sender)"

        # Truncate long subjects
        if len(subject) > 120:
            subject = subject[:117] + "..."

        content = f"[Email] {subject} | from: {sender}"

        signals.append(
            {
                "id": str(uuid.uuid4()),
                "source": "email",
                "captured_at": captured_at,
                "content": content,
                "triage": None,
            }
        )

    logger.info("Email: captured %d messages for %s", len(signals), target_date)
    return signals


def _next_date(date_str: str) -> str:
    from datetime import date, timedelta
    d = date.fromisoformat(date_str)
    return (d + timedelta(days=1)).isoformat()
