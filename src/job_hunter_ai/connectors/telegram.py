"""Telegram channels connector (Phase 8 stub).

For MVP: accepts pre-fetched messages or loads sample fixture.
Treats Telegram as repost_channel source_type.

Real implementation would use Telegram API / MTProto for channels like @tonhunt.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorEmptyResponseError,
    FetchResult,
    make_content_hash,
    utcnow,
)


class TelegramConnector(Connector):
    """Telegram repost channel connector (MVP version).

    source_name example: "telegram:tonhunt"
    """

    def __init__(self, source_name: str, messages: list[dict] | None = None) -> None:
        super().__init__(source_name, "repost_channel")
        self.messages = messages or []

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()
        records: list[RawSourceRecord] = []

        for idx, msg in enumerate(self.messages):
            if not isinstance(msg, dict):
                continue
            text = msg.get("text") or msg.get("message", "")
            if not text or "job" not in text.lower() and "hiring" not in text.lower():
                continue  # simplistic filter for jobs

            external_id = str(msg.get("id", idx))
            url = msg.get("url") or f"https://t.me/{self.source_name.split(':')[-1]}/{external_id}"

            payload = {
                "id": external_id,
                "text": text,
                "date": msg.get("date"),
                "from": msg.get("from"),
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=self._parse_date(msg.get("date")),
                payload=payload,
                content_hash=make_content_hash(text),
                cursor_value=cursor_value,
                metadata={"provider": "telegram", "channel": self.source_name},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records:
            # For MVP allow empty if no messages provided, but raise if explicitly empty in test
            if self.messages:
                raise ConnectorEmptyResponseError("No job-like messages in Telegram sample")

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


def load_sample_telegram_messages(channel: str = "tonhunt") -> list[dict]:
    """Sample messages for tests/fixtures (Phase 8)."""
    return [
        {"id": 101, "text": "Hiring: Senior TON Developer @ Wallet. Remote. Apply: https://example.com", "date": "2026-07-10"},
        {"id": 102, "text": "We are looking for a Backend Engineer (Python) at Ston.FI", "date": "2026-07-09"},
    ]
