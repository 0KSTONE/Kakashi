from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests


class KalshiHTTPError(Exception):
    """Raised when a Kalshi HTTP request cannot be satisfied."""


class KalshiClient:
    """Minimal read-only Kalshi client with simple retry/backoff."""

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0, retries: int = 3):
        self.base_url = base_url or os.getenv("KALSHI_BASE_URL", "https://api.elephant.kalshi.com/v1")
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        backoff = 1.0

        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:  # pragma: no cover - network instability
                if attempt == self.retries:
                    raise KalshiHTTPError(f"Request failed after {self.retries} attempts: {exc}") from exc
                time.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code in self.RETRY_STATUS:
                if attempt == self.retries:
                    raise KalshiHTTPError(
                        f"Kalshi request failed after retries ({response.status_code}): {response.text}"
                    )
                time.sleep(backoff)
                backoff *= 2
                continue

            if 400 <= response.status_code:
                raise KalshiHTTPError(
                    f"Kalshi request failed with status {response.status_code}: {response.text}"
                )

            try:
                return response.json()
            except ValueError as exc:  # pragma: no cover - unexpected payloads
                raise KalshiHTTPError("Kalshi response was not valid JSON") from exc

        raise KalshiHTTPError("Kalshi request unexpectedly exhausted retries")

    def get_markets_paginated(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all markets with naive pagination support."""
        markets: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"limit": limit}
            if page_token:
                params["page_token"] = page_token

            payload = self._request("GET", "/markets", params=params)
            markets.extend(payload.get("markets", []))
            page_token = payload.get("next_page_token")

            if not page_token:
                break

        return markets

    def get_market_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Fetch the orderbook for a specific market ticker."""
        return self._request("GET", f"/markets/{ticker}/orderbook")
