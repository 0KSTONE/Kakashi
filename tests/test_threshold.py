from src.strategy.threshold import expected_value_yes, size_by_risk


def test_ev_yes():
    assert abs(expected_value_yes(0.44, 0.49) - 0.05) < 1e-9


def test_size_by_risk():
    # $1,000 bankroll, 1% risk, price $0.44 -> floor(10/0.44) = 22
    assert size_by_risk(1000, 0.01, 0.44) == 22
