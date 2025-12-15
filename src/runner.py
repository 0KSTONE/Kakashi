from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple

from src.api.kalshi_client import KalshiClient, KalshiHTTPError
from src.data.sqlite_store import SQLiteStore
from src.models.schemas import Market, Snapshot

logger = logging.getLogger(__name__)


def _sample_data() -> Tuple[List[Market], List[Snapshot]]:
    """Provide deterministic sample market + snapshot rows for offline runs."""
    market = Market(
        id="SAMPLE-2024",
        question="Will the sample market close above 0.50?",
        close_time=datetime.now(tz=timezone.utc) + timedelta(days=1),
        resolution_source="sample",
    )
    snapshot = Snapshot(
        market_id=market.id,
        ts=datetime.now(tz=timezone.utc),
        bid=0.42,
        ask=0.46,
        last=0.44,
        volume=100,
    )
    return [market], [snapshot]


def _parse_market(raw: dict) -> Market:
    close_time = raw.get("close_time") or raw.get("close_time_str")
    if isinstance(close_time, str):
        close_dt = datetime.fromisoformat(close_time)
    elif isinstance(close_time, datetime):
        close_dt = close_time
    else:  # pragma: no cover - defensive fallback for unexpected payload
        close_dt = datetime.now(tz=timezone.utc)
    return Market(
        id=raw["id"],
        question=raw.get("question", raw.get("title", "")),
        close_time=close_dt,
        resolution_source=raw.get("resolution_source", "unknown"),
    )


def collect_from_api(client: KalshiClient, limit: int = 10) -> Tuple[List[Market], List[Snapshot]]:
    markets: List[Market] = []
    snapshots: List[Snapshot] = []

    for raw_market in client.get_markets_paginated(limit=limit):
        market = _parse_market(raw_market)
        markets.append(market)

        # Build a thin snapshot from the orderbook best bid/ask if available
        try:
            orderbook = client.get_market_orderbook(market.id)
            bids = orderbook.get("orderbook", {}).get("yes", [])
            asks = orderbook.get("orderbook", {}).get("no", [])
            best_bid = bids[0][0] if bids else 0.0
            best_ask = asks[0][0] if asks else max(best_bid, 0.01)
            last = orderbook.get("last_price", best_bid or best_ask)
        except KalshiHTTPError:
            # If the orderbook call fails for a specific market, skip its snapshot
            continue

        snapshots.append(
            Snapshot(
                market_id=market.id,
                ts=datetime.now(tz=timezone.utc),
                bid=best_bid,
                ask=max(best_ask, best_bid),
                last=last,
                volume=int(orderbook.get("volume", 0)),
            )
        )

    return markets, snapshots


def run(db_path: str = "data/kalashi.db", sample_only: bool = True, page_limit: int = 10) -> None:
    """Single-run snapshot + upsert flow.

    Defaults to offline sample data so the runner can be exercised without
    network access. Pass `sample_only=False` to attempt live collection.
    """

    store = SQLiteStore(db_path)
    markets: List[Market]
    snapshots: List[Snapshot]

    if sample_only:
        markets, snapshots = _sample_data()
    else:
        try:
            client = KalshiClient()
            markets, snapshots = collect_from_api(client, limit=page_limit)
        except KalshiHTTPError as exc:
            logger.warning("Falling back to sample data after API error: %s", exc)
            markets, snapshots = _sample_data()

    for market in markets:
        store.upsert_market(market)

    for snap in snapshots:
        store.insert_snapshot(snap)
        print(f"Snapshot saved for {snap.market_id}")

    store.close()


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a single Kakashi data collection loop")
    parser.add_argument("--db", dest="db_path", default="data/kalashi.db")
    parser.add_argument("--live", dest="sample_only", action="store_false", help="Use Kalshi API instead of sample data")
    parser.add_argument("--limit", dest="page_limit", type=int, default=10)
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=logging.INFO)
    run(db_path=args.db_path, sample_only=args.sample_only, page_limit=args.page_limit)


if __name__ == "__main__":
    main()
