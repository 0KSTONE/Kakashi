from datetime import datetime

from src.data.sqlite_store import SQLiteStore
from src.models.schemas import Market, Snapshot


def test_upsert_and_snapshot(tmp_path):
    db_path = tmp_path / "k.db"
    store = SQLiteStore(str(db_path))

    market = Market(
        id="M1",
        question="Test?",
        close_time=datetime(2024, 1, 1),
        resolution_source="unit-test",
    )
    store.upsert_market(market)

    snap = Snapshot(
        market_id="M1",
        ts=datetime(2024, 1, 1, 0, 0, 1),
        bid=0.1,
        ask=0.2,
        last=0.15,
        volume=5,
    )
    store.insert_snapshot(snap)

    latest = store.fetch_latest_snapshots(limit=1)
    assert latest
    assert latest[0].market_id == "M1"
    assert latest[0].bid == 0.1
    store.close()
