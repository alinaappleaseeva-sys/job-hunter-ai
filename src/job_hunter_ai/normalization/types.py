"""Types for the normalization pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import StringList


@dataclass(slots=True)
class ParseDiagnostics:
    """Field-level diagnostics for one normalization attempt."""

    provider: str | None
    mapper_name: str | None
    warnings: StringList = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class NormalizationItemResult:
    """Outcome for a single raw record."""

    raw_record_id: str | None
    posting_id: str | None
    posting: NormalizedJobPosting
    diagnostics: ParseDiagnostics
    persisted: bool = False


@dataclass(slots=True)
class NormalizationRunResult:
    """Summary of a batch normalization run."""

    total: int
    parsed: int
    partial: int
    failed: int
    items: list[NormalizationItemResult] = field(default_factory=list)

    @property
    def parse_rate(self) -> float:
        if self.total <= 0:
            return 0.0
        successful = self.parsed + self.partial
        return successful / self.total