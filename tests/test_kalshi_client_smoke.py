import time

import pytest

from src.api.kalshi_client import KalshiClient, KalshiHTTPError


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_get_markets_paginated_retries(monkeypatch):
    responses = [
        FakeResponse(429, {}),
        FakeResponse(200, {
            "markets": [
                {
                    "id": "TICKER1",
                    "question": "Q?",
                    "close_time": "2024-01-01T00:00:00",
                    "resolution_source": "kalshi",
                }
            ]
        }),
    ]

    call_count = {"n": 0}

    def fake_request(method, url, timeout=None, **kwargs):
        call_count["n"] += 1
        return responses.pop(0)

    client = KalshiClient(base_url="https://example.com")
    client.session = type("S", (), {})()
    client.session.request = fake_request
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: None)

    markets = client.get_markets_paginated(limit=1)
    assert len(markets) == 1
    assert call_count["n"] == 2


def test_request_error(monkeypatch):
    def fake_request(*_args, **_kwargs):
        return FakeResponse(500, {"error": "bad"})

    client = KalshiClient(base_url="https://example.com", retries=1)
    client.session = type("S", (), {})()
    client.session.request = fake_request

    with pytest.raises(KalshiHTTPError):
        client.get_market_orderbook("TICKER2")
