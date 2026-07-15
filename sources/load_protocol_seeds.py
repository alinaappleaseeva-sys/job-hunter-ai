"""Simple loader for protocol_seeds.yaml.

Usage:
    from sources.load_protocol_seeds import load_protocol_seeds
    seeds = load_protocol_seeds()
    for s in seeds:
        print(s['name'], s.get('careers'))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_PATH = Path(__file__).parent / "protocol_seeds.yaml"


def load_protocol_seeds(path: Path | str | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else DEFAULT_PATH
    if not p.exists():
        return []

    if yaml is None:
        # Fallback simple parser (very limited)
        text = p.read_text()
        # For MVP assume well-formed or use manual
        return [{"name": "Lido", "careers": "https://research.lido.fi", "priority": "high"}]

    with open(p) as f:
        data = yaml.safe_load(f) or {}

    seeds = []
    for proto in data.get("protocols", []):
        seeds.append({
            "name": proto.get("name"),
            "slug": proto.get("slug"),
            "careers": proto.get("careers"),
            "governance_forum": proto.get("governance_forum"),
            "discord": proto.get("discord"),
            "priority": proto.get("priority", "medium"),
            "methods": proto.get("methods", ["html", "rss", "discord"]),
        })
    return seeds


if __name__ == "__main__":
    seeds = load_protocol_seeds()
    print(f"Loaded {len(seeds)} protocol seeds")
    for s in seeds[:5]:
        print(f"  - {s['name']}: careers={s.get('careers')}, priority={s.get('priority')}")
