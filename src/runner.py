from __future__ import annotations

import os
from datetime import datetime

from src.api.kalshi_client import KalshiClient, KalshiHTTPError
from src.data.sqlite_store import SQLiteStore
from src.models.schemas import Market, Snapshot


def _sample_market() -> Market:
    return Market(
        id="SAMPLE-YES-NO-1",
        question="Will the sample market resolve to YES?",
        close_time=datetime.utcnow(),
        resolution_source="sample",
    )


def _sample_snapshot(market_id: str) -> Snapshot:
    return Snapshot(
        market_id=market_id,
        ts=datetime.utcnow(),
        bid=0.45,
        ask=0.55,
        last=0.5,
        volume=10,
    )


def main() -> None:
    store = SQLiteStore()
    use_sample = os.getenv("KAKASHI_SAMPLE_DATA", "1") != "0"

    if use_sample:
        markets = [_sample_market()]
        snapshot = _sample_snapshot(markets[0].id)
    else:
        client = KalshiClient()
        try:
            market_payloads = client.get_markets_paginated(limit=50)
        except KalshiHTTPError as exc:  # pragma: no cover - live path
            raise SystemExit(f"Failed to pull markets: {exc}")

        markets = [
            Market(
                id=entry["id"],
                question=entry.get("question", ""),
                close_time=datetime.fromisoformat(entry["close_time"]),
                resolution_source=entry.get("resolution_source", "kalshi"),
            )
            for entry in market_payloads
        ]

        if not markets:
            raise SystemExit("No markets returned from Kalshi")

        first_market = markets[0]
        try:
            ob = client.get_market_orderbook(first_market.id)
        except KalshiHTTPError as exc:  # pragma: no cover - live path
            raise SystemExit(f"Failed to pull orderbook: {exc}")

        book = ob.get("orderbook", {})
        snapshot = Snapshot(
            market_id=first_market.id,
            ts=datetime.utcnow(),
            bid=float(book.get("yes_bid", 0) or 0),
            ask=float(book.get("yes_ask", 0) or 0),
            last=float(book.get("last_price", 0) or 0),
            volume=int(book.get("yes_bid_size", 0) or 0),
        )

    store.upsert_markets(markets)
    store.insert_snapshot(snapshot)

    latest = store.fetch_latest_snapshots(limit=1)
    if latest:
        print(f"Snapshot saved for {latest[0].market_id} at {latest[0].ts.isoformat()}Z")


if __name__ == "__main__":
    main()
