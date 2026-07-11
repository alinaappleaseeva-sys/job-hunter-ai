"""Connector package exports.

This branch (feat/greenhouse-connector) ships the Greenhouse Tier-1 connector.
The Ashby connector lives on draft/ashby-connector and is intentionally NOT
imported here to keep this PR scoped to one source per the plan's PR strategy.
"""

from .base import Connector
from .base import ConnectorAuthError
from .base import ConnectorEmptyResponseError
from .base import ConnectorError
from .base import ConnectorNetworkError
from .base import ConnectorPartialFetchError
from .base import ConnectorRateLimitError
from .base import ConnectorSchemaError
from .base import DirectClient
from .base import FetchResult
from .base import make_content_hash
from .base import utcnow
from .greenhouse import GreenhouseConnector
from .quality import average_field_coverage
from .quality import compute_quality
from .quality import field_coverage
from .quality import ghost_rate
from .quality import is_ghost_or_stale
from .quality import parse_rate

__all__ = [
    "GreenhouseConnector",
    "Connector",
    "ConnectorAuthError",
    "ConnectorEmptyResponseError",
    "ConnectorError",
    "ConnectorNetworkError",
    "ConnectorPartialFetchError",
    "ConnectorRateLimitError",
    "ConnectorSchemaError",
    "DirectClient",
    "FetchResult",
    "make_content_hash",
    "utcnow",
    "average_field_coverage",
    "compute_quality",
    "field_coverage",
    "ghost_rate",
    "is_ghost_or_stale",
    "parse_rate",
]