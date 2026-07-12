"""Shared HTTP client for connector implementations."""

from __future__ import annotations

import json
from typing import Any

import httpx

from job_hunter_ai.connectors.base import ConnectorNetworkError
from job_hunter_ai.connectors.base import ConnectorRateLimitError
from job_hunter_ai.connectors.base import ConnectorSchemaError

DEFAULT_TIMEOUT = 30.0


class HttpxDirectClient:
    """Thin httpx wrapper implementing :class:`DirectClient`.

    Performs a single GET per call with no automatic retries — rate-limit
    backoff belongs in the ingestion scheduler, not in connector code.
    """

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._client = httpx.Client(timeout=timeout)

    def get(self, url: str, **kwargs: Any) -> Any:
        headers = kwargs.get("headers")
        try:
            response = self._client.get(url, headers=headers, follow_redirects=True)
        except httpx.NetworkError as exc:
            raise ConnectorNetworkError(f"Network error reaching {url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectorNetworkError(f"Timeout reaching {url}: {exc}") from exc

        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "unknown")
            raise ConnectorRateLimitError(
                f"Rate limited by {url} (retry-after={retry_after})"
            )

        response.raise_for_status()

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ConnectorSchemaError(f"Non-JSON response from {url}: {exc}") from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpxDirectClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()