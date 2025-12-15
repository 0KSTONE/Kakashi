from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List

from src.models.schemas import Market, Snapshot


class SQLiteStore:
    """Lightweight SQLite wrapper for markets and snapshots."""

    def __init__(self, db_path: str = "data/kalashi.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                close_time TEXT NOT NULL,
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
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
            """
        )
        self.conn.commit()

    def upsert_market(self, market: Market) -> None:
        """Insert or update a market record."""
        validated = market if isinstance(market, Market) else Market.model_validate(market)
        payload = validated.model_dump()
        close_time = payload["close_time"].isoformat()

        self.conn.execute(
            """
            INSERT INTO markets(id, question, close_time, resolution_source)
            VALUES (:id, :question, :close_time, :resolution_source)
            ON CONFLICT(id) DO UPDATE SET
                question=excluded.question,
                close_time=excluded.close_time,
                resolution_source=excluded.resolution_source
            """,
            {
                "id": payload["id"],
                "question": payload["question"],
                "close_time": close_time,
                "resolution_source": payload["resolution_source"],
            },
        )
        self.conn.commit()

    def insert_snapshot(self, snapshot: Snapshot) -> None:
        """Insert a validated snapshot row."""
        snap = snapshot if isinstance(snapshot, Snapshot) else Snapshot.model_validate(snapshot)
        ts = snap.ts
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        epoch_ms = int(ts.timestamp() * 1000)

        self.conn.execute(
            """
            INSERT INTO snapshots(market_id, ts, bid, ask, last, volume)
            VALUES (:market_id, :ts, :bid, :ask, :last, :volume)
            """,
            {
                "market_id": snap.market_id,
                "ts": epoch_ms,
                "bid": snap.bid,
                "ask": snap.ask,
                "last": snap.last,
                "volume": snap.volume,
            },
        )
        self.conn.commit()

    def fetch_latest_snapshots(self, limit: int = 10) -> List[Snapshot]:
        cursor = self.conn.execute(
            """
            SELECT market_id, ts, bid, ask, last, volume
            FROM snapshots
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        snapshots: List[Snapshot] = []
        for row in rows:
            ts = datetime.fromtimestamp(row["ts"] / 1000, tz=timezone.utc)
            snapshots.append(
                Snapshot(
                    market_id=row["market_id"],
                    ts=ts,
                    bid=row["bid"],
                    ask=row["ask"],
                    last=row["last"],
                    volume=row["volume"],
                )
            )
        return snapshots

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
