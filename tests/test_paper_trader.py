from datetime import datetime

from src.data.sqlite_store import SQLiteStore
from src.execution.paper_trader import PaperTrader
from src.models.schemas import Snapshot
from src.strategy.threshold import threshold_decision


def test_paper_trader_executes_and_updates_bankroll(tmp_path):
    store = SQLiteStore(db_path=str(tmp_path / "k.db"))
    trader = PaperTrader(store, initial_bankroll=1000.0, risk_per_trade=0.01)

    snap = Snapshot(
        market_id="M3",
        ts=datetime.utcnow(),
        bid=0.1,
        ask=0.12,
        last=0.11,
        volume=20,
    )

    decision = threshold_decision(snap, bankroll=store.get_latest_bankroll(), risk_pct=0.01, edge_threshold=0.0)
    assert decision is not None

    result = trader.execute_trade(decision)
    assert result is not None
    assert result.bankroll_after < result.bankroll_before

    trades = store.fetch_trades()
    assert len(trades) == 1
    assert trades[0][2] == "YES"
