"""Telegram channels connector (Phase 10 - real path + Wave 1 expansion).

Supports:
- Real mode using Telethon (MTProto)
- Stub / sample mode via channel registry (for tests, offline, and quick Wave 1 coverage)

Wave 1 focus: easy multi-channel support for high-relevance Web3/DAO hiring channels.

Usage example (stub):
    from job_hunter_ai.connectors.telegram import TelegramConnector
    conn = TelegramConnector.from_channel("tonhunt")   # auto-loads Wave 1 samples
    result = conn.fetch(limit=20)

Usage example (real):
    from telethon import TelegramClient
    client = TelegramClient(...)
    conn = TelegramConnector("telegram:tonhunt", client=client)
    result = conn.fetch(limit=50)
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
from job_hunter_ai.connectors.telegram_channels import (
    get_channel_handle,
    load_sample_for_channel,
    get_wave1_channels,
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

    source_name format: "telegram:<channel_key>"  e.g. "telegram:tonhunt"
    """

    def __init__(
        self,
        source_name: str,
        messages: list[dict] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(source_name, "repost_channel")
        self.messages = messages or []
        self.client = client

    @classmethod
    def from_channel(
        cls,
        channel: str,
        client: Any | None = None,
    ) -> "TelegramConnector":
        """Convenience constructor for Wave 1.

        Uses the channels registry to load sample data when no real client.
        Example: TelegramConnector.from_channel("cryptohiring_1")
        """
        source_name = f"telegram:{channel}" if not channel.startswith("telegram:") else channel
        samples = load_sample_for_channel(channel)
        return cls(source_name=source_name, messages=samples, client=client)

    async def _fetch_real(
        self, *, limit: int | None = None, cursor_value: str | None = None
    ) -> list[RawSourceRecord]:
        if not TELETHON_AVAILABLE or self.client is None:
            raise RuntimeError(
                "Telethon not installed or no client provided. "
                "Install with pip install -e '.[telegram]' and pass client=TelegramClient(...)"
            )

        channel = self.source_name.split(":", 1)[-1]
        records: list[RawSourceRecord] = []
        now = utcnow()

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

        if self.client is not None:
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

        # Stub / sample path (enhanced for Wave 1)
        records: list[RawSourceRecord] = []
        channel_key = self.source_name.split(":", 1)[-1] if ":" in self.source_name else self.source_name

        for idx, msg in enumerate(self.messages):
            if not isinstance(msg, dict):
                continue
            text = msg.get("text") or msg.get("message", "")
            text_lower = text.lower()
            job_keywords = ["job", "hiring", "position", "opening", "role", "looking for", "we need", "open "]
            if not text or not any(k in text_lower for k in job_keywords):
                continue

            external_id = str(msg.get("id", idx))
            url = msg.get("url") or f"https://t.me/{channel_key}/{external_id}"

            payload = {
                "id": external_id,
                "text": text,
                "date": msg.get("date"),
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
                metadata={"provider": "stub", "channel": channel_key},
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


# Backwards-compatible helper (still works)
def load_sample_telegram_messages(channel: str = "tonhunt") -> list[dict]:
    """Legacy helper. Prefer TelegramConnector.from_channel(channel) for Wave 1."""
    return load_sample_for_channel(channel)


async def fetch_telegram_real(
    client: Any,
    channel: str,
    limit: int | None = 50,
) -> list[dict]:
    """Low-level helper for advanced real fetches."""
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


def get_wave1_telegram_channels() -> dict:
    """Return metadata for Wave 1 priority channels."""
    return get_wave1_channels()