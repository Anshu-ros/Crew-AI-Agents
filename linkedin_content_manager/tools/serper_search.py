"""Retrying Serper.dev client and CrewAI search tool."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class SerperSearchError(RuntimeError):
    """Raised when a Serper request fails permanently or exhausts retries."""


class SerperSearchInput(BaseModel):
    query: str = Field(min_length=1, description="Web search query")


class SerperClient:
    """Small Serper API client with bounded retries and injectable HTTP session."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        max_attempts: int = 3,
        timeout_seconds: float = 20,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def search(self, query: str) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("Search query must not be empty")

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                    json={"q": query},
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Serper returned a non-object JSON response")
                return payload
            except requests.HTTPError as error:
                status_code = error.response.status_code if error.response else None
                if status_code is not None and status_code < 500 and status_code != 429:
                    raise SerperSearchError(
                        f"Serper rejected the search request (HTTP {status_code})"
                    ) from error
                failure: Exception = error
            except (requests.RequestException, ValueError) as error:
                failure = error

            if attempt == self.max_attempts:
                logger.error(
                    "Serper request failed after %d attempt(s)", self.max_attempts,
                    exc_info=(type(failure), failure, failure.__traceback__),
                )
                raise SerperSearchError(
                    f"Serper search failed after {self.max_attempts} attempt(s)"
                ) from failure

            delay = min(0.5 * (2 ** (attempt - 1)), 8.0)
            logger.warning(
                "Serper request failed on attempt %d/%d; retrying in %.1f seconds",
                attempt,
                self.max_attempts,
                delay,
            )
            time.sleep(delay)

        raise AssertionError("Unreachable retry loop")


class SerperSearchTool(BaseTool):
    name: str = "Serper web search"
    description: str = (
        "Search the web for current facts and sources relevant to a LinkedIn post topic."
    )
    args_schema: Type[BaseModel] = SerperSearchInput
    client: SerperClient

    def _run(self, query: str) -> str:
        result = self.client.search(query)
        return json.dumps(result, ensure_ascii=True)
