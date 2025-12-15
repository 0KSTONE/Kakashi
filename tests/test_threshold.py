# tests/test_threshold.py
from math import isclose

def expected_value_yes(price: float, p_hat: float) -> float:
    return p_hat - price

def size_by_risk(bankroll: float, risk_pct: float, price: float) -> int:
    max_risk = bankroll * risk_pct
    return int(max_risk // price)

def test_ev_yes():
    assert isclose(expected_value_yes(0.44, 0.49), 0.05, rel_tol=0, abs_tol=1e-12)

def test_size_by_risk():
    # $1,000 bankroll, 1% risk => $10 max risk. Price $0.44 => floor(10/0.44)=22
    assert size_by_risk(1000, 0.01, 0.44) == 22
