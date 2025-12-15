from datetime import datetime

import pytest

from src.execution.paper_trader import PaperTrader
from src.models.schemas import Outcome, TradeDecision


def make_decision(market_id: str = "M1", price: float = 0.2, size: int = 5) -> TradeDecision:
    return TradeDecision(
        market_id=market_id,
        ts=datetime(2024, 1, 1),
        side="YES",
        price=price,
        size=size,
        reason="test",
    )


def test_execute_enforces_risk_cap_and_logs_rejection():
    trader = PaperTrader(starting_bankroll=100, max_risk_pct=0.01)

    rejected = make_decision(price=0.5, size=3)  # risk 1.5 > 1% of 100
    assert trader.execute(rejected) is None
    assert trader.bankroll == 100
    assert trader.decision_log[-1][1].startswith("rejected:risk")

    filled = make_decision(price=0.2, size=5)  # risk = 1.0 (allowed)
    pos = trader.execute(filled)
    assert pos is not None
    assert trader.bankroll == pytest.approx(99.0)
    assert trader.open_position_count() == 1
    assert trader.decision_log[-1][1] == "filled"


def test_max_open_positions():
    trader = PaperTrader(starting_bankroll=50, max_open_positions=1)

    first = trader.execute(make_decision(market_id="M1", price=0.1, size=5))
    assert first is not None
    second = trader.execute(make_decision(market_id="M2", price=0.1, size=5))
    assert second is None
    assert trader.open_position_count() == 1


def test_settle_updates_bankroll_and_pnl():
    trader = PaperTrader(starting_bankroll=50, max_risk_pct=0.05)
    trader.execute(make_decision(price=0.2, size=5))  # bankroll 49 after risk taken

    outcome = trader.settle(Outcome(market_id="M1", resolved_value=1, pnl=0))
    assert outcome.pnl == pytest.approx(4.0)
    assert trader.bankroll == pytest.approx(54.0)
    assert trader.open_position_count() == 0
    assert trader.outcomes[-1].pnl == pytest.approx(4.0)
