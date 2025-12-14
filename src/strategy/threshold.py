# src/strategy/threshold.py
from math import floor
from datetime import datetime
from src.models.schemas import Snapshot, TradeDecision

def implied_prob_from_price(price: float) -> float:
    # For Kalshi binaries, price ~ probability (fees ignored here)
    return price

def expected_value_yes(price: float, p_hat: float) -> float:
    return p_hat - price  # $EV per contract

def size_by_risk(bankroll: float, risk_pct: float, price: float) -> int:
    max_risk = bankroll * risk_pct
    return max(0, floor(max_risk / price))

def threshold_decision(
    snap: Snapshot,
    bankroll: float,
    risk_pct: float = 0.01,
    edge_threshold: float = 0.03,
    max_positions_open: int = 5,
    positions_open: int = 0
):
    if positions_open >= max_positions_open:
        return None

    p_hat = simple_baseline_p_hat(snap)  # stub you implement
    edge = expected_value_yes(snap.last, p_hat)

    if edge >= edge_threshold:
        size = size_by_risk(bankroll, risk_pct, snap.last)
        if size == 0:
            return None
        return TradeDecision(
            market_id=snap.market_id,
            ts=datetime.utcnow(),
            side="YES",
            price=snap.last,
            size=size,
            reason=f"edge={edge:.3f} >= {edge_threshold:.3f}; p_hat={p_hat:.3f}; price={snap.last:.2f}"
        )
    return None

def simple_baseline_p_hat(snap: Snapshot) -> float:
    # Dumb on purpose: treat mid as a stabilizer, nudge toward last.
    mid = (snap.bid + snap.ask) / 2
    return 0.7 * snap.last + 0.3 * mid
