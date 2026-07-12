"""Connector package exports.

Exports shared connector contracts plus source-specific implementations.
Each source connector typically lands in its own PR to keep review scoped.
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
from .lever import LeverConnector
from .quality import average_field_coverage
from .quality import compute_quality
from .quality import field_coverage
from .quality import ghost_rate
from .quality import is_ghost_or_stale
from .quality import parse_rate

__all__ = [
    "GreenhouseConnector",
    "LeverConnector",
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