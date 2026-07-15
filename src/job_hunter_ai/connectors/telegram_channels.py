"""Telegram channels registry for Wave 1 expansion.

Defines high-relevance channels for the target profile (Web3 / DAO / Ops).
Provides both sample data (for tests/offline) and metadata for real fetches.
"""

from __future__ import annotations

from typing import Any

# High-priority channels for Wave 1 (focused on Web3, crypto hiring, ops/program/DAO roles)
WAVE1_CHANNELS = {
    "tonhunt": {
        "handle": "@tonhunt",
        "description": "TON ecosystem roles (Wallet, Ston.FI, etc.)",
        "priority": "high",
        "tags": ["web3", "ton", "infrastructure"],
    },
    "cryptohiring_1": {
        "handle": "@cryptohiring_1",
        "description": "General crypto hiring (MEXC and others)",
        "priority": "high",
        "tags": ["web3", "crypto", "ops", "trading"],
    },
    "smerkisjobs": {
        "handle": "@smerkisjobs",
        "description": "Blum + partners (frequent ops/program/growth roles)",
        "priority": "high",
        "tags": ["web3", "defi", "ops", "program"],
    },
    "web3hiring": {
        "handle": "@web3hiring",
        "description": "Daily global Web3 jobs feed (strong remote ops/DAO signal)",
        "priority": "high",
        "tags": ["web3", "remote", "ops", "dao", "governance", "treasury"],
    },
    "dejob_global": {
        "handle": "@DeJob_Global",
        "description": "DAO jobs & decentralized teams (governance, ops, contributors)",
        "priority": "high",
        "tags": ["dao", "governance", "ops", "treasury", "contributors"],
    },
}

# Sample data per channel (used when no real client is available)
_SAMPLE_DATA: dict[str, list[dict]] = {
    "tonhunt": [
        {"id": 101, "text": "Hiring Senior TON Developer. Remote. Apply: https://example.com", "date": "2026-07-12"},
        {"id": 102, "text": "We are looking for Backend Engineer (Python) at Ston.FI", "date": "2026-07-11"},
        {"id": 103, "text": "Hiring: Operations Manager @ Wallet (TON). Remote.", "date": "2026-07-10"},
    ],
    "cryptohiring_1": [
        {"id": 201, "text": "Hiring: Head of Operations for MEXC. Remote, Web3 experience required.", "date": "2026-07-12"},
        {"id": 202, "text": "Looking for community manager. DM for details", "date": "2026-07-12"},
        {"id": 203, "text": "Hiring Senior Solidity Dev. Full remote.", "date": "2026-07-11"},
    ],
    "smerkisjobs": [
        {"id": 301, "text": "Open position: Program Manager (Blum + partners). DAO experience preferred.", "date": "2026-07-12"},
        {"id": 302, "text": "We need an Operations Lead for our new DeFi project. Treasury and governance experience required.", "date": "2026-07-11"},
    ],
    "web3hiring": [
        {"id": 401, "text": "Hiring DAO Ops Lead at [Protocol]. Remote. Treasury + governance focus. Apply: link", "date": "2026-07-15"},
        {"id": 402, "text": "Senior Operations Manager - Web3 DeFi. Full remote, competitive comp.", "date": "2026-07-14"},
        {"id": 403, "text": "Contributor Coordinator role at growing DAO. Governance experience needed.", "date": "2026-07-13"},
    ],
    "dejob_global": [
        {"id": 501, "text": "DAO-Ops Manager @ [DAO]. Remote. Strong on proposals and treasury.", "date": "2026-07-15"},
        {"id": 502, "text": "Governance Specialist - Lido ecosystem. Part-time / full remote.", "date": "2026-07-14"},
        {"id": 503, "text": "Treasury Operations Lead for new L2 project. $90-120k + tokens.", "date": "2026-07-12"},
    ],
}

def get_wave1_channels() -> dict[str, dict]:
    """Return the list of Wave 1 priority channels with metadata."""
    return WAVE1_CHANNELS.copy()

def load_sample_for_channel(channel: str) -> list[dict]:
    """Return sample messages for a specific channel (for tests and offline runs)."""
    return _SAMPLE_DATA.get(channel, [])

def get_all_wave1_samples() -> dict[str, list[dict]]:
    """Return samples for all Wave 1 channels."""
    return {ch: load_sample_for_channel(ch) for ch in WAVE1_CHANNELS}

def get_channel_handle(channel: str) -> str:
    meta = WAVE1_CHANNELS.get(channel)
    return meta["handle"] if meta else channel
