"""Connector package exports.

Exports shared connector contracts plus source-specific implementations.
Each source connector typically lands in its own PR to keep review scoped.
"""

from .ashby import AshbyConnector
from .arcdev import ArcDevConnector, load_sample_arcdev_jobs
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
from .cryptojobslist import CryptoJobsListConnector
from .telegram_channels import get_wave1_channels, load_sample_for_channel, WAVE1_CHANNELS
from .weworkremotely import WeWorkRemotelyConnector, load_sample_weworkremotely_jobs
from .wellfound import WellfoundConnector, load_sample_wellfound_jobs
from .workable import WorkableConnector, load_sample_workable_jobs

__all__ = [
    "AshbyConnector",
    "ArcDevConnector",
    "GreenhouseConnector",
    "LeverConnector",
    "RemoteOKConnector",
    "WeWorkRemotelyConnector",
    "WorkableConnector",
    "WellfoundConnector",
    "SolanaJobsConnector",
    "HabrCareerConnector",
    "HhruConnector",
    "TelegramConnector",
    "CryptoJobsListConnector",
    "load_sample_telegram_messages",
    "load_sample_weworkremotely_jobs",
    "load_sample_workable_jobs",
    "load_sample_wellfound_jobs",
    "load_sample_solana_jobs",
    "load_sample_arcdev_jobs",
    "get_wave1_telegram_channels",
    "get_wave1_channels",
    "load_sample_for_channel",
    "WAVE1_CHANNELS",
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

# Web3 specific HTML boards (added in this iteration)
from .web3career import Web3CareerConnector
from .findweb3 import FindWeb3Connector
from .remote3 import Remote3Connector
