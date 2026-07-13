"""Connector package exports.

Exports shared connector contracts plus source-specific implementations.
Each source connector typically lands in its own PR to keep review scoped.
"""

from .ashby import AshbyConnector
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
from .http_client import HttpxDirectClient
from .base import make_content_hash
from .base import utcnow
from .greenhouse import GreenhouseConnector
from .habr_career import HabrCareerConnector
from .hhru import HhruConnector
from .lever import LeverConnector
from .quality import average_field_coverage
from .quality import compute_quality
from .quality import field_coverage
from .quality import ghost_rate
from .quality import is_ghost_or_stale
from .quality import parse_rate
from .remoteok import RemoteOKConnector
from .solana import SolanaJobsConnector, load_sample_solana_jobs
from .telegram import TelegramConnector, load_sample_telegram_messages, get_wave1_telegram_channels
from .telegram_channels import get_wave1_channels, load_sample_for_channel, WAVE1_CHANNELS
from .wellfound import WellfoundConnector, load_sample_wellfound_jobs

__all__ = [
    "AshbyConnector",
    "GreenhouseConnector",
    "LeverConnector",
    "RemoteOKConnector",
    "WellfoundConnector",
    "SolanaJobsConnector",
    "HabrCareerConnector",
    "HhruConnector",
    "TelegramConnector",
    "load_sample_telegram_messages",
    "load_sample_wellfound_jobs",
    "load_sample_solana_jobs",
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
    "HttpxDirectClient",
    "make_content_hash",
    "utcnow",
    "average_field_coverage",
    "compute_quality",
    "field_coverage",
    "ghost_rate",
    "is_ghost_or_stale",
    "parse_rate",
]
