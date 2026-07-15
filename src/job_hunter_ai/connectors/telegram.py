"""Telegram channels connector (Phase 10 - real path + Wave 1 expansion).

Supports:
- Real mode using Telethon (MTProto)
- Stub / sample mode via channel registry (for tests, offline, and quick Wave 1 coverage)

Wave 1 focus: easy multi-channel support for high-relevance Web3/DAO hiring channels.
Improved noise filtering with segment keywords for Ops/DAO/Governance/Treasury/Contributor roles.

Usage example (stub):
    from job_hunter_ai.connectors.telegram import TelegramConnector
    conn = TelegramConnector.from_channel("web3hiring")
    result = conn.fetch(limit=20)

Usage example (real):
    from telethon import TelegramClient
    client = TelegramClient(...)
    conn = TelegramConnector("telegram:web3hiring", client=client)
    result = conn.fetch(limit=50)
"""

from __future__ import annotations

import re
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


# === Tuned segment-aware job signal filter (Wave 1 tuning) ===

_JOB_SIGNALS = {
    "job", "hiring", "position", "opening", "role", "looking for", "we need",
    "open ", "we're hiring", "join us", "vacancy", "now hiring",
    "head of", "senior ", "lead ", "manager "
}

# Strong positive keywords for the target segment (tuned per plan)
_SEGMENT_KEYWORDS = {
    # Exact high-value phrases
    "head of ops", "senior operations", "dao ops", "treasury ops",
    "governance lead", "contributor coordinator", "program manager",
    "on-chain operations", "dao finance",
    # Core terms
    "ops", "operations", "dao", "governance", "treasury", "contributor",
    "program", "head of ops", "ops lead", "operations lead",
    "governance lead", "treasury ops", "contributor coordinator",
    "program manager", "chief of staff", "opco", "dao coordination",
    "dao finance", "on-chain operations"
}

_NEGATIVE_PATTERNS = [
    r"\b(developer|engineer|solidity|rust|python backend|frontend|smart contract)\b.*\b(only|role|position)\b",
    r"\b(marketing|growth|content|community manager|designer)\b(?!.*(ops|operations|dao))",
    r"\b(intern|internship)\b",
    r"\b(airdrop|giveaway|crypto signal|trading signal)\b",
    r"^\s*(dm|pm) me for details\s*$",
    r"\b(solidity|smart contract|rust developer|frontend engineer)\b",
]


def is_telegram_job_signal(text: str) -> bool:
    """Core filter used in both real Telethon and stub paths."""
    if not text or not isinstance(text, str):
        return False
    text_lower = text.lower().strip()

    has_signal = any(sig in text_lower for sig in _JOB_SIGNALS)
    if not has_signal:
        return False

    for pat in _NEGATIVE_PATTERNS:
        if re.search(pat, text_lower):
            return False

    return True


def score_telegram_message(text: str) -> dict:
    """Detailed scoring for eval. Higher weight for Head/Senior/Lead + DAO/Treasury/Gov + remote."""
    if not text:
        return {"is_job": False, "has_segment": False, "is_noise": True, "score": 0.0}

    text_lower = text.lower()

    has_signal = any(sig in text_lower for sig in _JOB_SIGNALS)
    has_segment = any(kw in text_lower for kw in _SEGMENT_KEYWORDS)

    # Bonus for seniority + key domains
    seniority_boost = any(x in text_lower for x in ["head of", "senior", "lead", "manager"])
    domain_boost = any(x in text_lower for x in ["dao", "treasury", "governance", "ops"])
    remote_boost = any(x in text_lower for x in ["remote", "async", "full remote"])

    is_negative = any(re.search(p, text_lower) for p in _NEGATIVE_PATTERNS)

    is_job = has_signal and not is_negative

    score = 0.0
    if has_signal:
        score += 0.4
    if has_segment:
        score += 0.35
    if seniority_boost:
        score += 0.15
    if domain_boost:
        score += 0.05
    if remote_boost:
        score += 0.05

    if is_negative:
        score -= 0.3

    return {
        "is_job": is_job,
        "has_segment": has_segment,
        "is_noise": not is_job or is_negative,
        "score": round(max(0.0, min(1.0, score)), 2),
    }


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
        """Convenience constructor for Wave 1."""
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
            if not is_telegram_job_signal(text):
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

        # Stub / sample path — uses improved filter
        records: list[RawSourceRecord] = []
        channel_key = self.source_name.split(":", 1)[-1] if ":" in self.source_name else self.source_name

        for idx, msg in enumerate(self.messages):
            if not isinstance(msg, dict):
                continue
            text = msg.get("text") or msg.get("message", "")
            if not is_telegram_job_signal(text):
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


# Backwards helpers
def load_sample_telegram_messages(channel: str = "tonhunt") -> list[dict]:
    return load_sample_for_channel(channel)


def get_wave1_telegram_channels() -> dict:
    return get_wave1_channels()
