from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import schedule

from src.api.kalshi_client import KalshiClient, KalshiHTTPError
from src.data.sqlite_store import SQLiteStore
from src.execution.paper_trader import PaperTrader
from src.models.schemas import Market, Snapshot
from src.strategy.threshold import threshold_decision

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


SAMPLE_MARKET_ID = "SAMPLE-YES-NO-1"


def _sample_market() -> Market:
    return Market(
        id=SAMPLE_MARKET_ID,
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


def _pull_live_market() -> tuple[list[Market], Snapshot]:
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
    return markets, snapshot


def run_one_cycle(store: SQLiteStore, trader: PaperTrader, use_sample: bool = True) -> None:
    if os.path.exists("data/stop.trading"):
        logger.warning("Kill switch engaged; stopping run")
        return

    markets: list[Market]
    snapshot: Snapshot
    if use_sample:
        markets = [_sample_market()]
        snapshot = _sample_snapshot(markets[0].id)
    else:
        markets, snapshot = _pull_live_market()

    store.upsert_markets(markets)
    inserted = store.insert_snapshot(snapshot)
    if not inserted:
        return

    latest = store.fetch_latest_snapshots(limit=1)
    if latest:
        snap = latest[0]
        bankroll = store.get_latest_bankroll()
        logger.info("Snapshot saved for %s at %s", snap.market_id, snap.ts.isoformat())

        decision = threshold_decision(
            snap,
            bankroll=bankroll,
            risk_pct=trader.risk_per_trade,
            max_positions_open=5,
            positions_open=0,
        )
        if decision:
            result = trader.execute_trade(decision)
            if result:
                logger.info(
                    "Decision executed for %s; bankroll %.2f -> %.2f",
                    decision.market_id,
                    result.bankroll_before,
                    result.bankroll_after,
                )
        else:
            logger.info("No trade decision for %s (edge below threshold or size zero)", snap.market_id)


def main() -> None:
    store = SQLiteStore()
    trader = PaperTrader(store)
    use_sample = os.getenv("KAKASHI_SAMPLE_DATA", "1") != "0"
    run_loop = os.getenv("KAKASHI_RUN_LOOP", "0") == "1"

    if run_loop:
        logger.info("Starting scheduled run (every 5 minutes)")
        schedule.every(5).minutes.do(run_one_cycle, store=store, trader=trader, use_sample=use_sample)
        run_one_cycle(store, trader, use_sample=use_sample)
        while True:  # pragma: no cover - runtime path
            schedule.run_pending()
            time.sleep(1)
    else:
        run_one_cycle(store, trader, use_sample=use_sample)


if __name__ == "__main__":
    main()
