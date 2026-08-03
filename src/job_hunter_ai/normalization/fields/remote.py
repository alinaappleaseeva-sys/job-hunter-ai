"""Remote / hybrid / onsite mode normalization.

Three-layer defense (priority order):
1. Real signals from location/offices + description (called from _to_canonical)
2. Hard rules on specific office cities/countries
3. Visa/sponsorship signals → onsite when combined with office location
"""

from __future__ import annotations

_ALLOWED = frozenset({"remote", "hybrid", "onsite", "unknown"})

# Layer 2: Cities/countries that almost always mean physical office unless explicit remote is stated
OFFICE_CITIES = [
    "singapore", "dubai", "hong kong", "hongkong", "malta", "london", "new york",
    "san francisco", "tokyo", "seoul", "shanghai", "beijing", "mumbai", "bangalore",
    "amsterdam", "berlin", "paris", "zurich", "geneva", "tel aviv", "abu dhabi",
    # Additional common office hubs (Web3 / finance)
    "sydney", "australia", "taiwan", "taipei", "kuala lumpur", "malaysia", "sliema",
    "estonia", "tallinn", "lisbon", "portugal", "switzerland", "germany", "toronto",
    "vancouver", "usa", "united states", "uk", "united kingdom"
]

# Explicit remote trust signals (these override office heuristics)
EXPLICIT_REMOTE_PHRASES = [
    "remote roles – cis", "remote – emea", "ukraine (remote)", "remote only",
    "fully remote", "100% remote", "work from anywhere", "remote-first",
    "remote role", "distributed team", "remote position"
]
# === Geo priority for remote roles (Europe-preferring profile) ===
# Priority (1 = best, 5 = worst)

SAFE_REMOTE_REGIONS = {
    # countries/cities where remote work is usually possible without Swiss work permit issues
    "portugal", "lisbon", "estonia", "tallinn", "malta", "lithuania", "vilnius",
    "latvia", "georgia", "tbilisi", "armenia", "yerevan", "cyprus", "uae", "dubai",
    "abu dhabi", "bahrain", "serbia", "belgrade", "montenegro", "albania",
}

RESTRICTED_REMOTE_REGIONS = {
    "us", "usa", "united states", "america", "north america",
    "singapore", "hong kong", "hongkong", "australia", "canada",
    "uk", "united kingdom", "london",
}

EUROPE_CORE = {
    "europe", "emea", "cis", "eu", "european union",
    "switzerland", "zurich", "zürich", "geneva", "basel",
    "germany", "berlin", "france", "paris", "netherlands", "amsterdam",
    "spain", "barcelona", "madrid", "italy", "milan", "rome",
    "austria", "vienna", "belgium", "brussels", "ireland", "dublin",
    "sweden", "stockholm", "norway", "oslo", "denmark", "copenhagen",
    "finland", "helsinki", "poland", "warsaw", "czech", "prague",
}


def detect_remote_priority(
    location_raw: str | None,
    description: str | None = None,
) -> tuple[int, str]:
    """
    Returns (priority, reason)
    Priority (higher = better):
        1 = pure remote (no geo at all)
        2 = Remote Zürich / Switzerland
        3 = Remote Europe / EMEA / CIS
        4 = Remote in safe countries (low visa friction)
        5 = Restricted (US-only, Singapore, etc.)
        0 = not remote / unknown
    """
    loc = (location_raw or "").lower().strip()
    desc = (description or "").lower()
    text = f"{loc} {desc}"

    # --- Restricted first (worst) ---
    if any(r in text for r in RESTRICTED_REMOTE_REGIONS):
        # Rare exception: explicit "Remote Europe" wins over US mention
        if any(e in text for e in ("remote europe", "remote-emea", "remote – emea", "emea remote")):
            return 3, "remote Europe (despite restricted mention)"
        return 5, "restricted remote (US / Singapore / visa-heavy region)"

    # --- Priority 2: Zürich / Switzerland (your home base) ---
    if any(x in text for x in ("zurich", "zürich", "switzerland", "swiss")):
        if "remote" in text or "distributed" in text or "work from anywhere" in text:
            return 2, "remote Zürich / Switzerland"

    # --- Priority 3: Core Europe / EMEA ---
    if any(e in text for e in EUROPE_CORE):
        if "remote" in text or "distributed" in text:
            return 3, "remote Europe / EMEA"

    # --- Priority 1: Pure remote with no geo signals ---
    pure_signals = (
        "fully remote", "100% remote", "remote only", "remote-first",
        "work from anywhere", "wfa", "distributed team", "remote role",
        "remote position", "remote jobs", "remote opportunities"
    )
    has_geo = any(
        geo in text for geo in (RESTRICTED_REMOTE_REGIONS | SAFE_REMOTE_REGIONS | EUROPE_CORE)
    )
    if any(s in text for s in pure_signals) and not has_geo:
        return 1, "pure remote (no geo restriction)"

    if loc in ("remote", "fully remote", "remote only") or loc.startswith("remote "):
        if not has_geo:
            return 1, "pure remote (location label only)"

    # --- Priority 4: Safe countries ---
    if any(s in text for s in SAFE_REMOTE_REGIONS) and "remote" in text:
        return 4, "remote in safe country (low work permit friction)"

    # Fallback for plain remote
    if "remote" in text:
        return 4, "remote (unclassified geo)"

    return 0, "not remote / unknown"



# Layer 3: Visa / work authorization signals — strong indicator of onsite requirement
VISA_SPONSORSHIP_PHRASES = [
    "visa sponsorship", "eligible to work in", "work authorization required",
    "must be based in", "relocation to", "work permit", "sponsorship",
    "legally authorized to work", "no visa sponsorship"
]


def normalize_remote_mode(
    *,
    workplace_type: str | None = None,
    is_remote: bool | None = None,
    location_raw: str | None = None,
    categories_remote: str | bool | None = None,
    description: str | None = None,
) -> str:
    """Infer canonical remote_mode.

    Priority (highest first):
    1. Strong explicit remote phrases in description/location
    2. Workplace / is_remote from provider
    3. Description signals (strong remote/hybrid/onsite)
    4. Location signals + office city rules (Layer 2)
    5. Visa/sponsorship + office location → onsite (Layer 3)
    """
    # 0. Direct provider signals
    wt = (workplace_type or "").strip().lower().replace("_", "-")
    if wt == "remote":
        return "remote"
    if wt == "hybrid":
        return "hybrid"
    if wt in {"onsite", "on-site"}:
        return "onsite"

    if categories_remote is True or (
        isinstance(categories_remote, str) and categories_remote.strip().lower() == "remote"
    ):
        return "remote"

    if is_remote is True:
        return "remote"
    if is_remote is False:
        return "onsite"

    if wt == "unspecified":
        return "unknown"

    loc_lower = (location_raw or "").lower()
    desc_lower = (description or "").lower()
    combined = f"{loc_lower} {desc_lower}"

    # Layer 1 priority: explicit remote trust phrases
    for phrase in EXPLICIT_REMOTE_PHRASES:
        if phrase in combined:
            return "remote"

    # Location-based signal
    loc_signal = _remote_signal_from_location(location_raw)
    if loc_signal:
        return loc_signal

    # Description-based signal
    desc_signal = _remote_signal_from_description(description)
    if desc_signal:
        return desc_signal

    # === Layer 2: Specific office cities without explicit remote → onsite ===
    has_office_city = any(city in loc_lower for city in OFFICE_CITIES)
    has_explicit_remote = any(p in combined for p in EXPLICIT_REMOTE_PHRASES)

    if has_office_city and not has_explicit_remote:
        return "onsite"

    # === Layer 3: Visa/sponsorship + office location ===
    has_visa_signal = any(phrase in desc_lower for phrase in VISA_SPONSORSHIP_PHRASES)
    if has_visa_signal and has_office_city:
        return "onsite"

    # Fallbacks
    # Broad rule per plan: concrete city/country without remote-signal → onsite
    if location_raw and str(location_raw).strip() and not has_explicit_remote:
        l = str(location_raw).lower()
        has_remote_indicator = (
            "remote" in l or
            "remote" in desc_lower or
            any(p in combined for p in ["distributed", "work from anywhere", "anywhere"])
        )
        if not has_remote_indicator:
            if "," in l or any(c.isalpha() for c in l):
                return "onsite"
        if any(x in l for x in ["office", "hq", "headquarters"]):
            return "onsite"

    return "unknown"


def _remote_signal_from_location(location_raw: str | None) -> str | None:
    if not location_raw:
        return None
    lower = location_raw.lower()

    # Explicit remote in location title (e.g. "Remote Roles – CIS")
    for phrase in EXPLICIT_REMOTE_PHRASES:
        if phrase in lower:
            return "remote"

    if "hybrid" in lower:
        return "hybrid"
    if "remote" not in lower:
        return None
    if ";" in location_raw:
        return "hybrid"
    return "remote"


def _remote_signal_from_description(desc: str | None) -> str | None:
    """Extract from description. Strong signals first."""
    if not desc:
        return None

    lower = desc.lower()

    # Explicit remote trust first (Layer 1)
    for phrase in EXPLICIT_REMOTE_PHRASES:
        if phrase in lower:
            return "remote"

    # Strong onsite (including visa-related)
    strong_onsite = [
        "on-site", "onsite", "in-office", "in office", "office-based",
        "must be in", "located in our office", "work from office",
        "mandatory in-office", "days per week in the office"
    ]
    if any(phrase in lower for phrase in strong_onsite):
        return "onsite"

    # Visa signals are strong onsite indicators when location is office
    if any(phrase in lower for phrase in VISA_SPONSORSHIP_PHRASES):
        # Only return onsite here if we also see office language; otherwise let caller decide
        if any(c in lower for c in OFFICE_CITIES + ["office", "based in"]):
            return "onsite"

    # Hybrid
    if "hybrid" in lower or "flexible location" in lower or "remote/hybrid" in lower:
        return "hybrid"

    # Weaker remote
    if any(p in lower for p in ["fully remote", "100% remote", "work from anywhere"]):
        return "remote"

    if "remote" in lower and ("work from home" in lower or "wfh" in lower):
        return "remote"

    return None

def detect_remote_region(location_raw: str | None, description: str | None = None) -> str:
    """Detect geo restriction for remote roles.

    Returns: "us-only" | "europe" | "global" | "unknown"

    Priority to location label ("Remote-US" in the job posting).
    Even if the application form mentions Europe, we downrank (weaker candidate for Europe-based profile).
    """
    if not location_raw and not description:
        return "unknown"

    loc = (location_raw or "").lower()
    desc = (description or "").lower()
    text = f"{loc} {desc}"

    # Explicit location "Remote-US" is treated as us-restricted (even if form allows Europe)
    if "remote-us" in loc or loc.strip() in ("us", "united states"):
        return "us-only"

    # Other US-only signals
    for sig in US_ONLY_REMOTE_SIGNALS:
        if sig in text:
            if "remote-us" not in loc and any(e in text for e in EUROPE_EMEA_SIGNALS):
                return "global"
            return "us-only"

    if any(e in text for e in EUROPE_EMEA_SIGNALS):
        return "europe"

    if ("united states" in text or " usa " in text) and "remote" in text:
        if "remote-us" not in loc and not any(e in text for e in EUROPE_EMEA_SIGNALS + ["europe", "emea"]):
            return "us-only"

    if "remote" in text:
        return "global"

    return "unknown"
