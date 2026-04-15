#!/usr/bin/env python3
"""
L0 Capturer: Google Calendar
Fetches today's calendar events (title + duration only, no PII fields).
Returns a list of raw signal dicts conforming to the raw signal schema.
"""
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


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
    return build("calendar", "v3", credentials=creds)


def capture(target_date: str, credentials_path: str, token_path: str) -> list[dict]:
    """
    Capture calendar events for target_date (YYYY-MM-DD).
    Returns list of raw signal dicts.
    """
    try:
        service = _get_service(credentials_path, token_path)
    except Exception as e:
        logger.warning("Calendar: failed to initialize service: %s", e)
        return []

    # Build time range for target_date in local timezone
    date = datetime.strptime(target_date, "%Y-%m-%d").date()
    # Use UTC for API; Google Calendar API accepts RFC3339
    day_start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as e:
        logger.warning("Calendar: API call failed: %s", e)
        return []

    signals = []
    captured_at = datetime.now(timezone.utc).isoformat()

    for event in result.get("items", []):
        title = event.get("summary", "(no title)")
        start = event.get("start", {})
        end = event.get("end", {})

        # Calculate duration in minutes (skip all-day events without datetime)
        start_str = start.get("dateTime") or start.get("date", "")
        end_str = end.get("dateTime") or end.get("date", "")
        duration_min = None
        if start.get("dateTime") and end.get("dateTime"):
            try:
                s = datetime.fromisoformat(start["dateTime"])
                e = datetime.fromisoformat(end["dateTime"])
                duration_min = int((e - s).total_seconds() / 60)
            except Exception:
                pass

        if duration_min is not None:
            content = f"[Calendar] {title} ({duration_min}min)"
        else:
            content = f"[Calendar] {title}"

        signals.append(
            {
                "id": str(uuid.uuid4()),
                "source": "calendar",
                "captured_at": captured_at,
                "content": content,
                "triage": None,
            }
        )

    logger.info("Calendar: captured %d events for %s", len(signals), target_date)
    return signals
