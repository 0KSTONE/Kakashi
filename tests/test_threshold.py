from datetime import datetime

import pytest

from src.models.schemas import Snapshot
from src.strategy.threshold import (
    expected_value_yes,
    simple_baseline_p_hat,
    size_by_risk,
    threshold_decision,
)


def make_snapshot(price: float = 0.4) -> Snapshot:
    return Snapshot(
        market_id="M1",
        ts=datetime(2024, 1, 1),
        bid=price - 0.05,
        ask=price + 0.05,
        last=price,
        volume=10,
    )


def test_expected_value_yes():
    assert expected_value_yes(0.4, 0.55) == pytest.approx(0.15)


def test_size_by_risk_caps_loss():
    size = size_by_risk(bankroll=1000, risk_pct=0.01, price=0.2)
    assert size == 50


def test_threshold_decision_filters_by_edge():
    snap = Snapshot(
        market_id="M2",
        ts=datetime(2024, 1, 1),
        bid=0.05,
        ask=0.30,
        last=0.10,
        volume=25,
    )
    decision = threshold_decision(snap, bankroll=500, edge_threshold=0.01)
    assert decision is not None
    assert decision.side == "YES"

    blocked = threshold_decision(snap, bankroll=500, edge_threshold=0.5)
    assert blocked is None


def test_threshold_respects_open_position_cap():
    snap = make_snapshot(price=0.2)
    decision = threshold_decision(snap, bankroll=500, positions_open=5)
    assert decision is None
