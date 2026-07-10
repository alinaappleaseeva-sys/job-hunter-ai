"""Shared type definitions for the repository.

These are intentionally minimal placeholders so early documents and code can
agree on import locations before the implementation settles.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SourceRecord:
    source_name: str
    source_type: str
    fetched_at: datetime
    payload: dict[str, Any]

