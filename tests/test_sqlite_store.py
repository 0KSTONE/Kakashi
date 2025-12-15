from datetime import datetime

from src.data.sqlite_store import SQLiteStore
from src.models.schemas import Market, Snapshot, TradeDecision


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
    assert store.insert_snapshot(snap) is True

    latest = store.fetch_latest_snapshots(limit=1)
    assert latest
    assert latest[0].market_id == "M1"
    assert latest[0].bid == 0.1

    # invalid snapshot skipped
    bad_snap = {
        "market_id": "M1",
        "ts": datetime(2024, 1, 1, 0, 0, 2),
        "bid": 0.2,
        "ask": 0.1,
        "last": 0.15,
        "volume": 5,
    }
    assert store.insert_snapshot(bad_snap) is False

    store.close()


def test_bankroll_and_trades(tmp_path):
    db_path = tmp_path / "k.db"
    store = SQLiteStore(str(db_path))

    bankroll = store.get_latest_bankroll()
    assert bankroll == 1000.0

    decision = TradeDecision(
        market_id="M2",
        ts=datetime(2024, 1, 1, 0, 0, 1),
        side="YES",
        price=0.25,
        size=4,
        reason="edge positive",
    )
    store.record_trade(decision, pnl=0.0, size=4)
    updated_bankroll = bankroll - (decision.price * decision.size)
    store.record_bankroll(updated_bankroll, ts_ms=int(datetime.utcnow().timestamp() * 1000) + 1)

    trades = store.fetch_trades()
    assert len(trades) == 1
    assert trades[0][2] == "YES"

    assert store.get_latest_bankroll() == updated_bankroll
