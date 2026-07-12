"""Location string parsing into structured fields."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CITY_STATE_RE = re.compile(r"^(.+?),\s*([A-Za-z]{2})$")
_CITY_STATE_NAME_RE = re.compile(r"^(.+?),\s*(.+)$")

_COUNTRY_ALIASES: dict[str, str] = {
    "japan": "JP",
    "singapore": "SG",
    "france": "FR",
    "united kingdom": "GB",
    "uk": "GB",
    "germany": "DE",
    "india": "IN",
    "european union": None,
}

_US_STATE_ABBREV: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "mh": "MH",
}

_CITY_ALIASES: dict[str, str] = {
    "bombay": "Mumbai",
}


@dataclass(slots=True)
class ParsedLocation:
    """Structured location fields for a normalized posting."""

    location_raw: str | None
    location_country: str | None
    location_region: str | None
    location_city: str | None


def parse_location_string(raw: str | None) -> ParsedLocation:
    """Parse a source location string into country / region / city."""
    if not raw or not str(raw).strip():
        return ParsedLocation(None, None, None, None)

    text = str(raw).strip()
    lower = text.lower()

    if lower.startswith("remote - "):
        region_token = text.split("-", 1)[1].strip()
        region_lower = region_token.lower()
        if region_lower in {"us", "united states"}:
            return ParsedLocation(text, "US", None, None)
        if region_lower in {"european union", "eu"}:
            return ParsedLocation(text, None, None, None)
        country = _COUNTRY_ALIASES.get(region_lower)
        return ParsedLocation(text, country, None, None)

    country_key = lower
    if country_key in _COUNTRY_ALIASES:
        code = _COUNTRY_ALIASES[country_key]
        city = text if code == "SG" else None
        return ParsedLocation(text, code, None, city)

    match = _CITY_STATE_RE.match(text)
    if match:
        city = match.group(1).strip()
        state = match.group(2).upper()
        city = _CITY_ALIASES.get(city.lower(), city)
        if state == "MH":
            return ParsedLocation(text, "IN", state, city)
        return ParsedLocation(text, "US", state, city)

    match = _CITY_STATE_NAME_RE.match(text)
    if match:
        city_part = match.group(1).strip()
        region_part = match.group(2).strip()
        region_lower = region_part.lower()

        if region_lower in _US_STATE_ABBREV:
            abbrev = _US_STATE_ABBREV[region_lower]
            if len(region_part) == 2 and region_part.isupper():
                abbrev = region_part
            city = _CITY_ALIASES.get(city_part.lower(), city_part)
            return ParsedLocation(text, "US", abbrev, city)

        if region_lower == "mh":
            city = _CITY_ALIASES.get(city_part.lower(), city_part)
            return ParsedLocation(text, "IN", "MH", city)

        if region_lower in {"georgia", "texas", "california"}:
            abbrev = _US_STATE_ABBREV.get(region_lower, region_part)
            city = _CITY_ALIASES.get(city_part.lower(), city_part)
            return ParsedLocation(text, "US", abbrev, city)

    if text == "Singapore":
        return ParsedLocation(text, "SG", None, "Singapore")

    return ParsedLocation(text, None, None, None)