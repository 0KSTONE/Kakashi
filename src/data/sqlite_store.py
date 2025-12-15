from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

from pydantic import ValidationError

from src.models.schemas import Market, Snapshot, TradeDecision

logger = logging.getLogger(__name__)


class SQLiteStore:
    """Lightweight SQLite persistence for markets, snapshots, and trades."""

    def __init__(self, db_path: str = "data/kakashi.db", initial_bankroll: float = 1000.0) -> None:
        self.db_path = db_path
        Path(os.path.dirname(self.db_path) or ".").mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self.ensure_bankroll_initialized(initial_bankroll)

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                close_time INTEGER NOT NULL,
                resolution_source TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                bid REAL,
                ask REAL,
                last REAL,
                volume INTEGER,
                FOREIGN KEY(market_id) REFERENCES markets(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bankroll (
                ts INTEGER PRIMARY KEY,
                bankroll REAL NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                market_ticker TEXT,
                side TEXT,
                price REAL,
                size INTEGER,
                pnl REAL,
                reason TEXT
            )
            """
        )
        self.conn.commit()

    def ensure_bankroll_initialized(self, initial_bankroll: float = 1000.0) -> None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT bankroll FROM bankroll ORDER BY ts DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            ts_ms = int(datetime.utcnow().timestamp() * 1000)
            cursor.execute(
                "INSERT INTO bankroll (ts, bankroll) VALUES (?, ?)",
                (ts_ms, initial_bankroll),
            )
            self.conn.commit()

    def get_latest_bankroll(self) -> float:
        cursor = self.conn.cursor()
        cursor.execute("SELECT bankroll FROM bankroll ORDER BY ts DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            self.ensure_bankroll_initialized()
            return self.get_latest_bankroll()
        (bankroll,) = row
        return float(bankroll)

    def record_bankroll(self, bankroll: float, ts_ms: int | None = None) -> None:
        cursor = self.conn.cursor()
        ts_ms = ts_ms or int(datetime.utcnow().timestamp() * 1000)
        cursor.execute("INSERT INTO bankroll (ts, bankroll) VALUES (?, ?)", (ts_ms, bankroll))
        self.conn.commit()

    def record_trade(self, decision: TradeDecision, pnl: float = 0.0, size: int | None = None, ts_ms: int | None = None) -> None:
        ts_ms = ts_ms or int(decision.ts.timestamp() * 1000)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO trades (ts, market_ticker, side, price, size, pnl, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts_ms,
                decision.market_id,
                decision.side,
                decision.price,
                size if size is not None else decision.size,
                pnl,
                decision.reason,
            ),
        )
        self.conn.commit()

    def upsert_market(self, market: Market) -> None:
        market = Market.model_validate(market)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO markets (id, question, close_time, resolution_source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question=excluded.question,
                close_time=excluded.close_time,
                resolution_source=excluded.resolution_source
            """,
            (
                market.id,
                market.question,
                int(market.close_time.timestamp() * 1000),
                market.resolution_source,
            ),
        )
        self.conn.commit()

    def insert_snapshot(self, snapshot: Snapshot) -> bool:
        try:
            snap = Snapshot.model_validate(snapshot)
        except ValidationError as err:
            logger.warning("Skipping snapshot insert due to validation error: %s", err)
            return False

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO snapshots (market_id, ts, bid, ask, last, volume)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snap.market_id,
                int(snap.ts.timestamp() * 1000),
                snap.bid,
                snap.ask,
                snap.last,
                snap.volume,
            ),
        )
        self.conn.commit()
        return True

    def fetch_latest_snapshots(self, limit: int = 10) -> List[Snapshot]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT market_id, ts, bid, ask, last, volume
            FROM snapshots
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def fetch_trades(self) -> List[Tuple]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT ts, market_ticker, side, price, size, pnl, reason FROM trades ORDER BY ts DESC"
        )
        return cursor.fetchall()

    def _row_to_snapshot(self, row: Tuple) -> Snapshot:
        market_id, ts, bid, ask, last, volume = row
        return Snapshot(
            market_id=market_id,
            ts=datetime.utcfromtimestamp(ts / 1000),
            bid=bid,
            ask=ask,
            last=last,
            volume=volume,
        )

    def upsert_markets(self, markets: Iterable[Market]) -> None:
        for market in markets:
            self.upsert_market(market)

    def close(self) -> None:
        self.conn.close()
