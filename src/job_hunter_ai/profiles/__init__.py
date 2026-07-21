"""Candidate profiles.

Single source of truth for profiles lives in submodules (e.g. alina.py).
"""

from job_hunter_ai.common.models import CandidateProfile
from job_hunter_ai.profiles.alina import get_alina_profile

__all__ = ["CandidateProfile", "get_alina_profile"]
