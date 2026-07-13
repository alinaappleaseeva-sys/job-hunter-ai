#!/usr/bin/env python3
"""
HTML Report Generator for Job Hunter AI (Wave 1)

Generates a clean, self-contained HTML file with ranked jobs.
Job titles are directly clickable and link to the original posting.

Run:
    python demo/generate_html_report.py

This will create `job_results.html` and open it in your browser.
No server restarts needed — perfect for fast iteration.
"""

from __future__ import annotations

import webbrowser
from datetime import datetime
from pathlib import Path

# Ensure we can import the package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_hunter_ai.pipeline import run_full_pipeline


def escape_html(text: str) -> str:
    """Basic HTML escaping."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_job_card(idx: int, rj, url: str | None) -> str:
    """Render a single job card as HTML."""
    cj = rj.canonical_job
    bd = rj.score_breakdown

    # Source badge
    src = cj.canonical_job_id.split("-")[0]
    if ":" in src:
        src = src.split(":")[0]
    source_badge = f'<span class="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded">{escape_html(src)}</span>'

    # Title - clickable if URL exists
    title_text = f"{cj.title_normalized or 'Untitled'} @ {cj.company_name or 'Unknown'}"
    if url:
        title_html = f'<a href="{escape_html(url)}" target="_blank" class="text-xl font-semibold text-blue-700 hover:text-blue-800 hover:underline">{escape_html(title_text)}</a>'
    else:
        title_html = f'<span class="text-xl font-semibold text-gray-800">{escape_html(title_text)}</span>'

    # Score
    score = bd.total_score
    score_color = "emerald" if score >= 0.85 else ("amber" if score >= 0.7 else "gray")
    score_html = f'<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-{score_color}-100 text-{score_color}-800">Score: {score:.2f}</span>'

    # Metadata
    meta_parts = []
    if cj.role_family:
        meta_parts.append(f"<strong>Role:</strong> {escape_html(cj.role_family)}")
    if cj.seniority:
        meta_parts.append(f"<strong>Seniority:</strong> {escape_html(cj.seniority)}")
    if cj.market:
        meta_parts.append(f"<strong>Market:</strong> {escape_html(cj.market)}")
    if cj.remote_mode:
        meta_parts.append(f"<strong>Remote:</strong> {escape_html(cj.remote_mode)}")
    if cj.compensation_min:
        meta_parts.append(f"<strong>Min Comp:</strong> ${int(cj.compensation_min):,}")

    meta_html = " • ".join(meta_parts) if meta_parts else ""

    # Explanations
    explanations_html = ""
    if bd.explanations:
        explanations_html = "<div class='mt-3'><div class='text-sm font-medium text-gray-600 mb-1'>Why this score:</div><ul class='text-sm space-y-1'>"
        for exp in bd.explanations[:4]:
            reasons = ", ".join(exp.reasons) if exp.reasons else ""
            explanations_html += f"<li class='text-gray-700'>• <strong>{escape_html(exp.component)}</strong> ({exp.score:.2f}) — {escape_html(reasons)}</li>"
        explanations_html += "</ul></div>"

    # Optional direct link if no title link (fallback)
    link_html = ""
    if url and not True:  # title is already the link
        pass

    card = f"""
    <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start gap-4">
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    {source_badge}
                    {score_html}
                </div>
                <div class="mb-2">
                    {title_html}
                </div>
                <div class="text-sm text-gray-600 mb-3">
                    {meta_html}
                </div>
                {explanations_html}
            </div>
        </div>
    </div>
    """
    return card


def generate_html_report(limit_per_source: int = 8, output_path: Path | None = None) -> Path:
    print("Running pipeline...")
    results = run_full_pipeline(limit_per_source=limit_per_source)
    ranked = results["ranked_jobs"]
    profile = results["profile"]

    print(f"Got {len(ranked)} ranked jobs. Generating HTML...")

    if output_path is None:
        output_path = Path("job_results.html")

    # Prefer jobs with specific real URLs (from live connectors like WWR, RemoteOK, Workable)
    # Skip generic board links from sample/fallback data
    def is_specific_real_url(u: str) -> bool:
        if not u:
            return False
        ul = u.lower().rstrip("/")
        # Generic board pages - reject
        if ul.endswith(("/remote", "jobs?filter=remote", "/remote-jobs", "/jobs")):
            return False
        # Specific real job postings
        markers = [
            "weworkremotely.com/remote-jobs/",
            "remoteok.com/remote-jobs/",
            "apply.workable.com",
            "/j/",
        ]
        if any(m in u.lower() for m in markers):
            return True
        # Other specific job links
        return "/jobs/" in u.lower() and len(u) > 35

    good = [rj for rj in ranked if is_specific_real_url(getattr(rj.canonical_job, "url", "") or "")]
    print(f"Jobs with specific real URLs: {len(good)}")

    if not good:
        good = []

    # Build cards ONLY from good real specific jobs
    cards_html = ""
    for idx, rj in enumerate(good[:15], 1):
        cj = rj.canonical_job
        url = getattr(cj, "url", None) or None
        cards_html += render_job_card(idx, rj, url)

    # Profile summary
    profile_html = f"""
    <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 text-sm">
        <div class="font-semibold text-gray-700 mb-1">Profile: {escape_html(profile.profile_id)}</div>
        <div class="text-gray-600">
            Target roles: {", ".join(profile.target_role_families)}<br>
            Markets: {", ".join(profile.preferred_markets)}<br>
            Min compensation: ${int(profile.min_compensation):,}
        </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Hunter AI — Alina Aseeva Results</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .job-card {{ transition: all 0.1s ease; }}
        .job-card:hover {{ transform: translateY(-1px); }}
    </style>
</head>
<body class="bg-gray-100 py-8">
    <div class="max-w-3xl mx-auto px-4">
        <div class="flex justify-between items-center mb-6">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">Job Hunter AI — Real Results</h1>
                <p class="text-gray-600 mt-1">Alina Aseeva • Head of Operations (Web3/DAO)</p>
            </div>
            <div class="text-right text-sm text-gray-500">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}<br>
                Jobs fetched: {results.get("total_raw", len(ranked))}
            </div>
        </div>

        {profile_html}

        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-gray-800">Top Ranked Jobs</h2>
            <div class="text-sm text-gray-500">Sources: {", ".join(results.get("sources", []))}</div>
        </div>

        <div class="space-y-3">
            {cards_html}
        </div>

        <div class="mt-10 text-center text-xs text-gray-400">
            Click any job title to open the original posting.<br>
            Generated by <span class="font-medium">job_hunter_ai</span> pipeline.
        </div>
    </div>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")
    print(f"\n✅ HTML report generated: {output_path.resolve()}")

    # Try to open in browser
    try:
        webbrowser.open(f"file://{output_path.resolve()}")
        print("→ Opened in browser.")
    except Exception:
        print(f"→ Open manually: file://{output_path.resolve()}")

    return output_path


if __name__ == "__main__":
    generate_html_report()
