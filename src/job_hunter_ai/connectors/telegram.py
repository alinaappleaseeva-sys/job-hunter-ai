"""Telegram channels connector (Phase 10 - real path).

Supports both:
- Stub / sample mode (for tests and offline)
- Real mode using Telethon (MTProto) for channel history

Real usage:
    from telethon import TelegramClient
    client = TelegramClient(session, api_id, api_hash)
    conn = TelegramConnector("telegram:tonhunt", client=client)
    result = conn.fetch(limit=50)

The connector returns RawSourceRecord with source_type="repost_channel".
Integrates with existing ghosting/dedup via content_hash and metadata.
"""

from __future__ import annotations

import os
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

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    TelegramClient = None  # type: ignore
    Message = None  # type: ignore


class TelegramConnector(Connector):
    """Telegram repost channel connector.

    source_name example: "telegram:tonhunt"
    """

    def __init__(
        self,
        source_name: str,
        messages: list[dict] | None = None,
        client: Any | None = None,  # TelegramClient when real
    ) -> None:
        super().__init__(source_name, "repost_channel")
        self.messages = messages or []
        self.client = client

    async def _fetch_real(
        self, *, limit: int | None = None, cursor_value: str | None = None
    ) -> list[RawSourceRecord]:
        """Real fetch using Telethon (requires authenticated client)."""
        if not TELETHON_AVAILABLE or self.client is None:
            raise RuntimeError(
                "Telethon not installed or no client provided. "
                "Install with pip install -e '.[telegram]' and pass client=TelegramClient(...)"
            )

        channel = self.source_name.split(":", 1)[-1]
        records: list[RawSourceRecord] = []
        now = utcnow()

        # Simple pagination using cursor as offset_id if provided
        offset_id = int(cursor_value) if cursor_value and cursor_value.isdigit() else 0

        async for msg in self.client.iter_messages(
            channel, limit=limit or 100, offset_id=offset_id, reverse=False
        ):
            if not isinstance(msg, Message) or not msg.message:
                continue

            text = msg.message
            if "job" not in text.lower() and "hiring" not in text.lower():
                continue

            external_id = str(msg.id)
            url = f"https://t.me/{channel}/{external_id}"

            payload = {
                "id": external_id,
                "text": text,
                "date": msg.date.isoformat() if msg.date else None,
                "sender_id": getattr(msg.sender_id, "user_id", None) if hasattr(msg, "sender_id") else None,
                "views": getattr(msg, "views", None),
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=msg.date,
                payload=payload,
                content_hash=make_content_hash(text),
                cursor_value=str(msg.id),
                metadata={
                    "provider": "telethon",
                    "channel": channel,
                    "views": getattr(msg, "views", 0),
                },
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        return records

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()

        # Real path (async inside sync for simplicity in MVP; real callers should await)
        if self.client is not None:
            # Note: for full async use, callers should use the async version
            # Here we provide sync wrapper for compatibility with existing pipeline
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            records = loop.run_until_complete(
                self._fetch_real(limit=limit, cursor_value=cursor_value)
            )
            return FetchResult(records=records, cursor_after=str(now))

        # Stub / sample path (backwards compatible)
        records: list[RawSourceRecord] = []

        for idx, msg in enumerate(self.messages):
            if not isinstance(msg, dict):
                continue
            text = msg.get("text") or msg.get("message", "")
            if not text or ("job" not in text.lower() and "hiring" not in text.lower()):
                continue

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
                metadata={"provider": "stub", "channel": self.source_name},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records and self.messages:
            raise ConnectorEmptyResponseError("No job-like messages in Telegram source")

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
    """Sample messages for tests (unchanged from Phase 8)."""
    return [
        {"id": 101, "text": "Hiring: Senior TON Developer @ Wallet. Remote. Apply: https://example.com", "date": "2026-07-10"},
        {"id": 102, "text": "We are looking for a Backend Engineer (Python) at Ston.FI", "date": "2026-07-09"},
    ]


# Convenience async fetcher for advanced callers
async def fetch_telegram_real(
    client: Any,
    channel: str,
    limit: int | None = 50,
) -> list[dict]:
    """Low-level helper to fetch raw messages using Telethon (for advanced use)."""
    if not TELETHON_AVAILABLE:
        raise RuntimeError("Telethon not installed")
    items = []
    async for msg in client.iter_messages(channel, limit=limit):
        if msg.message:
            items.append({
                "id": msg.id,
                "text": msg.message,
                "date": msg.date.isoformat() if msg.date else None,
                "views": getattr(msg, "views", 0),
            })
    return items
