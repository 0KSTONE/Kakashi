import time
from typing import Dict, Iterable, Optional
import requests

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

class KalshiHTTPError(RuntimeError):
    pass

class KalshiClient:
    """
    Minimal, read-only client.
    Public endpoints require no auth. Keep this simple and robust.
    Docs: https://docs.kalshi.com (public market data quick start)
    """

    def __init__(self, base_url: str = API_BASE, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries

        # Be a good citizen
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "KakashiBot/0.1 (+https://github.com/0KSTONE/Kakashi)"
        })

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if 200 <= resp.status_code < 300:
                    return resp.json()
                # Basic backoff for transient 429/5xx
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise KalshiHTTPError(f"GET {url} failed: {resp.status_code} {resp.text[:200]}")
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise KalshiHTTPError(f"GET {url} error after retries: {e}") from e
                time.sleep(min(2 ** attempt, 10))
        raise KalshiHTTPError(f"GET {url} exhausted retries")

    def get_markets_paginated(self, limit: int = 100) -> Iterable[Dict]:
        """
        Yield markets across pages. The response uses a 'cursor' for pagination.
        """
        cursor = None
        while True:
            params = {"limit": limit}
            if cursor:
                params["cursor"] = cursor
            data = self._get("/markets", params=params)
            markets = data.get("markets", [])
            for m in markets:
                yield m
            cursor = data.get("cursor")
            if not cursor:
                break

    def get_market_orderbook(self, ticker: str) -> Dict:
        """
        Orderbook structure is 'orderbook': {'yes': [[price, qty], ...], 'no': [[price, qty], ...]}
        Docs note it only returns bids due to binary reciprocity.
        """
        return self._get(f"/markets/{ticker}/orderbook")
