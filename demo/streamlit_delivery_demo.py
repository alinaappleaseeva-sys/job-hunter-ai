"""Minimal Streamlit demo for Phase 9 Delivery UX.

Run with:
    pip install -e '.[demo]'
    streamlit run demo/streamlit_delivery_demo.py

Shows ranked jobs with explanations and allows structured feedback
(relevant / not_relevant / duplicate / ghost_likely / applied).

All feedback is recorded via apply_action and kept in session state.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime

from job_hunter_ai.common.models import (
    CandidateProfile,
    CanonicalJob,
    JobScoreBreakdown,
    RankedJob,
    ScoreExplanation,
)
from job_hunter_ai.delivery import apply_action

ACTIONS = ["relevant", "not_relevant", "duplicate", "ghost_likely", "applied"]


def _make_sample_ranked_jobs() -> list[RankedJob]:
    """Create a few realistic sample RankedJobs for the demo."""
    profile = st.session_state.get("profile")
    if profile is None:
        profile = CandidateProfile(profile_id="demo-profile")
        st.session_state.profile = profile

    samples = [
        {
            "id": "cj-001",
            "title": "Senior Backend Engineer",
            "company": "Acme AI",
            "score": 0.91,
            "ghost": 0.08,
            "explanations": [
                ("role_fit", 0.95, ["Strong title match to target role"]),
                ("seniority_fit", 0.90, ["Senior level matches profile"]),
            ],
        },
        {
            "id": "cj-002",
            "title": "Staff Software Engineer - Platform",
            "company": "Vanguard Labs",
            "score": 0.84,
            "ghost": 0.12,
            "explanations": [
                ("role_fit", 0.88, ["Platform work aligns with experience"]),
                ("location_remote_fit", 0.85, ["Fully remote option"]),
            ],
        },
        {
            "id": "cj-003",
            "title": "Backend Engineer (Python)",
            "company": "ScaleOps",
            "score": 0.72,
            "ghost": 0.35,
            "explanations": [
                ("seniority_fit", 0.65, ["More mid-level than target"]),
                ("salary_fit", 0.70, ["Compensation range slightly below preference"]),
            ],
        },
    ]

    ranked_jobs = []
    for s in samples:
        cj = CanonicalJob(
            canonical_job_id=s["id"],
            primary_posting_id=s["id"] + "-post",
            company_name=s["company"],
            company_domain=None,
            title_normalized=s["title"],
            role_family="engineering",
            seniority="senior",
            market="saas",
            remote_mode="remote",
            employment_type="full-time",
            location_country="US",
            location_region=None,
            location_city=None,
            compensation_min=160000 if s["id"] != "cj-003" else 120000,
            compensation_max=None,
            compensation_currency="USD",
            canonical_posted_at=datetime.now(),
            first_seen_at=datetime.now(),
            last_seen_at=datetime.now(),
            active_posting_count=1,
            source_count=1,
            ghost_score=s["ghost"],
            canonical_status="active",
            merge_confidence=None,
            merge_reasons=[],
        )

        explanations = [
            ScoreExplanation(component=comp, score=sc, reasons=reasons)
            for comp, sc, reasons in s["explanations"]
        ]
        breakdown = JobScoreBreakdown(
            total_score=s["score"],
            explanations=explanations,
        )
        rj = RankedJob(canonical_job=cj, score_breakdown=breakdown, rank=len(ranked_jobs) + 1)
        ranked_jobs.append(rj)

    return ranked_jobs


def main() -> None:
    st.set_page_config(page_title="Job Hunter AI - Delivery Demo", layout="wide")
    st.title("Job Hunter AI — Delivery Demo (Phase 9)")
    st.caption("Minimal local UI for viewing ranked jobs and submitting structured feedback")

    if "ranked_jobs" not in st.session_state:
        st.session_state.ranked_jobs = _make_sample_ranked_jobs()
    if "feedback_events" not in st.session_state:
        st.session_state.feedback_events = []
    if "profile" not in st.session_state:
        st.session_state.profile = CandidateProfile(profile_id="demo-profile")

    profile = st.session_state.profile
    ranked_jobs = st.session_state.ranked_jobs
    feedback_events = st.session_state.feedback_events

    # Sidebar info
    with st.sidebar:
        st.header("Profile")
        st.write(f"**Profile ID:** {profile.profile_id}")
        st.divider()
        st.markdown("**Actions**")
        st.markdown("- `relevant` — good match\n- `not_relevant` — skip\n- `duplicate`\n- `ghost_likely`\n- `applied`")
        st.divider()
        if st.button("Reset demo data"):
            st.session_state.clear()
            st.rerun()

    # Main content: Jobs
    st.subheader(f"Ranked Jobs ({len(ranked_jobs)})")

    for idx, rj in enumerate(ranked_jobs):
        cj = rj.canonical_job
        bd = rj.score_breakdown

        with st.expander(f"#{idx+1} {cj.title_normalized} @ {cj.company_name} — Score: {bd.total_score:.2f}", expanded=(idx == 0)):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Company:** {cj.company_name}")
                st.markdown(f"**Ghost score:** {cj.ghost_score:.2f}")
                if bd.explanations:
                    st.markdown("**Explanations:**")
                    for exp in bd.explanations:
                        st.markdown(f"- **{exp.component}** ({exp.score:.2f}): {', '.join(exp.reasons)}")

            with col2:
                st.markdown("**Submit feedback**")
                action = st.selectbox(
                    "Action",
                    ACTIONS,
                    key=f"action_{idx}",
                    label_visibility="collapsed",
                )
                reason = st.text_input(
                    "Reason (optional)",
                    key=f"reason_{idx}",
                    placeholder="Why this action?",
                )

                if st.button("Submit feedback", key=f"submit_{idx}"):
                    event = apply_action(
                        ranked_job=rj,
                        profile_id=profile.profile_id,
                        action=action,
                        reason=reason or None,
                    )
                    feedback_events.append(event)
                    st.success(f"Feedback recorded: {action} (event_id: {event.event_id[:8]}...)")
                    st.rerun()

    # Submitted feedback section
    st.divider()
    st.subheader(f"Submitted Feedback ({len(feedback_events)})")

    if not feedback_events:
        st.info("No feedback submitted yet. Use the buttons above.")
    else:
        for ev in reversed(feedback_events):
            st.markdown(
                f"**{ev.action}** on `{ev.canonical_job_id}` — "
                f"reason: {ev.reason or '(none)'}"
            )
            with st.expander("Trace details"):
                st.json({
                    "event_id": ev.event_id,
                    "score_breakdown": {
                        "total_score": ev.score_breakdown.total_score if ev.score_breakdown else None,
                        "explanations": [
                            {"component": e.component, "score": e.score, "reasons": e.reasons}
                            for e in (ev.explanations or [])
                        ],
                    },
                    "ghost_score": ev.ghost_score,
                    "timestamp": str(ev.timestamp),
                })

    st.caption("This demo uses the real `apply_action` from Phase 9 delivery layer. All events are fully traceable.")


if __name__ == "__main__":
    main()
