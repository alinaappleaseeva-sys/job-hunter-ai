"""Pydantic v2 models for CV Tailoring spike."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import hashlib


class Bullet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str
    index: int
    tags: List[str] = Field(default_factory=list)  # e.g. ["dao", "operations", "governance"]


class Experience(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    company: str
    title: str
    start: str
    end: str
    location: Optional[str] = None
    bullets: List[Bullet]


class Education(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    institution: str
    degree: str
    year: Optional[str] = None


class MasterCV(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: str
    name: str
    headline: str
    summary: str
    experiences: List[Experience]
    education: List[Education]
    skills: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    raw_hash: str

    @classmethod
    def compute_version(cls, raw_markdown: str) -> str:
        h = hashlib.sha256(raw_markdown.encode("utf-8")).hexdigest()[:8]
        date = datetime.now().strftime("%Y-%m-%d")
        return f"{date}-{h}"


class JobRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    job_id: str
    title: str
    company: str
    url: Optional[str] = None
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    level: str = "senior"  # or head, manager, etc.
    raw_description: str


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category: str  # e.g. "dao_governance", "treasury", "cross_functional_leadership"
    description: str
    evidence_in_master: List[str] = Field(default_factory=list)
    missing_signals: List[str] = Field(default_factory=list)


class Enrichment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    master_cv_version: str
    job_id: str
    question: str
    user_answer: str
    added_facts: List[str] = Field(default_factory=list)
    timestamp: str


class TailoredBullet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_text: str
    tailored_text: str
    rationale: str
    emphasis: List[str] = Field(default_factory=list)  # words/phrases to bold


class TailoredExperience(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    company: str
    title: str
    bullets: List[TailoredBullet]


class TailoredCV(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    master_cv_version: str
    job_id: str
    tailored_summary: str
    experiences: List[TailoredExperience]
    vanilla_baseline_summary: str
    vanilla_baseline_experiences: List[TailoredExperience]
    metrics: Dict[str, Any] = Field(default_factory=dict)
