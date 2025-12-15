from pathlib import Path
from datetime import datetime, timezone
import sqlite3
from typing import Dict, List, Tuple

DB_PATH = Path("data/kalshi.db")

_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS markets (
        ticker TEXT PRIMARY KEY,
        title TEXT,
        event_ticker TEXT,
        series_ticker TEXT,
        status TEXT,
        close_ts INTEGER,
        created_ts INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,             -- collection timestamp (UTC epoch ms)
        market_ticker TEXT NOT NULL,
        best_yes_price REAL,             -- cents -> convert to dollars later if you want
        best_yes_qty INTEGER,
        best_no_price REAL,
        best_no_qty INTEGER,
        FOREIGN KEY (market_ticker) REFERENCES markets(ticker)
    );
    """
]

def _epoch_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def ensure_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for stmt in _SCHEMA:
            cur.execute(stmt)
        con.commit()

def upsert_markets(markets: List[Dict]):
    ensure_schema()
    rows: List[Tuple] = []
    for m in markets:
        rows.append((
            m.get("ticker"),
            m.get("title"),
            m.get("event_ticker"),
            m.get("series_ticker"),
            m.get("status"),
            m.get("close_time"),   # docs: fields like 'close_time' are epoch ms or ISO; we store raw value
            m.get("created_time"),
        ))
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.executemany("""
            INSERT INTO markets (ticker, title, event_ticker, series_ticker, status, close_ts, created_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
              title=excluded.title,
              event_ticker=excluded.event_ticker,
              series_ticker=excluded.series_ticker,
              status=excluded.status,
              close_ts=excluded.close_ts,
              created_ts=excluded.created_ts;
        """, rows)
        con.commit()

def insert_snapshot_now(market_ticker: str, yes_book: List[List[int]], no_book: List[List[int]]):
    """
    yes_book/no_book are lists like [[price_cents, qty], ...] sorted best-first.
    """
    ensure_schema()
    ts = _epoch_ms(datetime.now(timezone.utc))
    best_yes_price, best_yes_qty = (yes_book[0][0], yes_book[0][1]) if yes_book else (None, None)
    best_no_price,  best_no_qty  = (no_book[0][0],  no_book[0][1])  if no_book  else (None, None)

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO snapshots (ts, market_ticker, best_yes_price, best_yes_qty, best_no_price, best_no_qty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, market_ticker, best_yes_price, best_yes_qty, best_no_price, best_no_qty))
        con.commit()
