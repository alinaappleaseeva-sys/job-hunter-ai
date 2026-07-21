"""Alina Aseeva profile definition.

This is the single source of truth for the target candidate profile
(Head of Operations / Chief of Staff in Web3/DAO/DeFi and adjacent domains).

See:
- docs/research/target-segment.md
- docs/Alina_Aseeva_CV_14.07.2026.md
"""

from job_hunter_ai.common.models import CandidateProfile


def get_alina_profile() -> CandidateProfile:
    """Single source of truth for Alina's profile.

    Derived from CV Alina_Aseeva_CV_14.07.2026.md.
    Target segment: Head/Senior Operations + DAO/Governance/Treasury roles
    in Web3, DeFi, protocols and adjacent domains (see target-segment.md).
    """
    return CandidateProfile(
        profile_id="alina-aseeva-head-ops-web3",
        target_role_families=["operations", "program_management", "head_of_ops", "dao_ops", "chief_of_staff"],
        target_seniorities=["head", "lead", "senior", "chief"],
        target_title_keywords=[
            "operations",
            "program",
            "head of",
            "dao",
            "governance",
            "project management",
            "ops lead",
            "web3 ops",
            "program manager",
            "chief of staff",
            "head of operations",
            "chief of",
            "ops manager",
        ],
        remote_preference="remote",
        preferred_locations=["remote", "any"],
        min_compensation=120000,
        compensation_currency="USD",
        preferred_markets=["web3", "defi", "dao", "crypto", "blockchain", "fintech", "security", "ai-web3"],
        notes=(
            "Head of Operations. 10+ years building ops from scratch in Web3/DAO/DeFi. "
            "Strong on governance, treasury/settlement, cross-functional alignment, "
            "AI automation, and scaling operations. Returning to full-time in June 2026. "
            "CV: 14.07.2026"
        ),
    )
