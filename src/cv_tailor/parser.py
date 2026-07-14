"""Quick parser for Master CV (Phase 0 spike)."""

import re
import hashlib
from datetime import datetime
from typing import List
from pathlib import Path
import sys

# Allow both package import and direct script execution
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).parent))
    from models import MasterCV, Experience, Bullet, Education
else:
    from .models import MasterCV, Experience, Bullet, Education


def parse_master_cv(raw_markdown: str) -> MasterCV:
    """Very basic parser for the current CV format. Good enough for spike."""
    version = MasterCV.compute_version(raw_markdown)
    raw_hash = hashlib.sha256(raw_markdown.encode("utf-8")).hexdigest()

    lines = raw_markdown.strip().split("\n")

    name = "ALINA ASEEVA"
    headline = "Head of Operations"
    summary_lines = []
    in_summary = False
    experiences: List[Experience] = []
    education: List[Education] = []
    skills: List[str] = []
    languages: List[str] = []

    current_exp = None
    current_bullets: List[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("# ALINA ASEEVA"):
            continue
        if "**Head of Operations**" in line and not current_exp:
            headline = line.replace("**", "").strip()
            continue

        if line.startswith("## Summary"):
            in_summary = True
            continue
        if line.startswith("## ") and in_summary:
            in_summary = False

        if in_summary:
            summary_lines.append(line)

        # Rough experience header parsing
        if line.startswith("**") and "|" in line and "–" in line:
            if current_exp:
                bullets = [Bullet(text=b.strip("- "), index=i) for i, b in enumerate(current_bullets)]
                experiences.append(current_exp.model_copy(update={"bullets": bullets}))

            match = re.match(r"\*\*(.+?) — (.+?) \| (.+?) \| (.+?)\*\*", line)
            if match:
                title = match.group(1).strip()
                company = match.group(2).strip()
                location = match.group(3).strip()
                dates = match.group(4).strip()
                if "–" in dates:
                    start, end = [x.strip() for x in dates.split("–", 1)]
                else:
                    start, end = dates, "Present"
                current_exp = Experience(
                    company=company,
                    title=title,
                    start=start,
                    end=end,
                    location=location,
                    bullets=[]
                )
                current_bullets = []
            continue

        if line.startswith("- ") and current_exp:
            current_bullets.append(line)

    # Save last experience
    if current_exp:
        bullets = [Bullet(text=b.strip("- "), index=i) for i, b in enumerate(current_bullets)]
        experiences.append(current_exp.model_copy(update={"bullets": bullets}))

    # Rough skills for the spike
    skills = [
        "Strategic Initiative Management", "OKR & Goal Setting", "Cross-Functional Alignment",
        "DAO Governance", "Treasury & Settlement", "Process Optimization",
        "AI Transformation", "Jira", "Notion", "SQL", "Python", "Tableau"
    ]

    summary = " ".join(summary_lines)

    return MasterCV(
        version=version,
        name=name,
        headline=headline,
        summary=summary,
        experiences=experiences,
        education=education,
        skills=skills,
        languages=["English — Fluent", "Russian — Native"],
        raw_hash=raw_hash,
    )
