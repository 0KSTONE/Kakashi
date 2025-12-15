from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

from src.models.schemas import Market, Snapshot


class SQLiteStore:
    """Lightweight SQLite persistence for markets and snapshots."""

    def __init__(self, db_path: str = "data/kakashi.db") -> None:
        self.db_path = db_path
        Path(os.path.dirname(self.db_path) or ".").mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

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
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                last REAL NOT NULL,
                volume INTEGER NOT NULL,
                FOREIGN KEY(market_id) REFERENCES markets(id)
            )
            """
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

    def insert_snapshot(self, snapshot: Snapshot) -> None:
        snap = Snapshot.model_validate(snapshot)
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
