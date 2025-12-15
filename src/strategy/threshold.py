from __future__ import annotations

from datetime import datetime
from math import floor

from src.models.schemas import Snapshot, TradeDecision


def expected_value_yes(price: float, p_hat: float) -> float:
    """EV per contract for buying YES on a $1 payout binary (fees ignored)."""
    return p_hat - price


def size_by_risk(bankroll: float, risk_pct: float, price: float) -> int:
    """Max contracts such that worst-case loss <= bankroll * risk_pct."""
    max_risk = bankroll * risk_pct
    return max(0, floor(max_risk / price))


def simple_baseline_p_hat(snap: Snapshot) -> float:
    """Dumb on purpose: stabilize last with mid price."""
    mid = (snap.bid + snap.ask) / 2
    return 0.7 * snap.last + 0.3 * mid


def threshold_decision(
    snap: Snapshot,
    bankroll: float,
    risk_pct: float = 0.01,
    edge_threshold: float = 0.03,
    max_positions_open: int = 5,
    positions_open: int = 0,
) -> TradeDecision | None:
    if positions_open >= max_positions_open:
        return None

    if snap.last is None or snap.bid is None or snap.ask is None:
        return None

    p_hat = simple_baseline_p_hat(snap)
    edge = expected_value_yes(snap.last, p_hat)

    if edge < edge_threshold:
        return None

    size = size_by_risk(bankroll, risk_pct, snap.last)
    if size == 0:
        return None

    return TradeDecision(
        market_id=snap.market_id,
        ts=datetime.utcnow(),
        side="YES",
        price=snap.last,
        size=size,
        reason=f"edge={edge:.3f} >= {edge_threshold:.3f}; p_hat={p_hat:.3f}; price={snap.last:.2f}",
    )
