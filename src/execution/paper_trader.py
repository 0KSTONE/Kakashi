from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.models.schemas import Outcome, TradeDecision


@dataclass
class Position:
    market_id: str
    side: str  # "YES" or "NO"
    entry_price: float
    size: int
    opened_at: datetime

    def risk(self) -> float:
        """Worst-case loss for this position."""
        side = self.side.upper()
        if side == "YES":
            return self.entry_price * self.size
        if side == "NO":
            return (1 - self.entry_price) * self.size
        raise ValueError(f"Unsupported side: {self.side}")


DecisionLog = Tuple[TradeDecision, str]


class PaperTrader:
    """Simulate fills and bankroll changes for paper trades."""

    def __init__(self, starting_bankroll: float, max_risk_pct: float = 0.01, max_open_positions: int = 5) -> None:
        if starting_bankroll <= 0:
            raise ValueError("starting_bankroll must be positive")
        if max_risk_pct <= 0:
            raise ValueError("max_risk_pct must be positive")
        if max_open_positions <= 0:
            raise ValueError("max_open_positions must be positive")
        self.bankroll = starting_bankroll
        self.max_risk_pct = max_risk_pct
        self.max_open_positions = max_open_positions
        self.positions: Dict[str, Position] = {}
        self.decision_log: List[DecisionLog] = []
        self.outcomes: List[Outcome] = []

    def _position_risk(self, decision: TradeDecision) -> float:
        side = decision.side.upper()
        if side == "YES":
            return decision.price * decision.size
        if side == "NO":
            return (1 - decision.price) * decision.size
        raise ValueError(f"Unsupported side: {decision.side}")

    def can_execute(self, decision: TradeDecision) -> Tuple[bool, str]:
        if decision.market_id in self.positions:
            return False, "position already open"
        if len(self.positions) >= self.max_open_positions:
            return False, "max open positions reached"

        risk = self._position_risk(decision)
        max_allowed = self.bankroll * self.max_risk_pct
        if risk > max_allowed:
            return False, "risk per trade cap"
        return True, ""

    def execute(self, decision: TradeDecision) -> Optional[Position]:
        """Apply a decision to the paper portfolio if limits allow."""
        ok, reason = self.can_execute(decision)
        status = "filled" if ok else f"rejected:{reason}"
        self.decision_log.append((decision, status))

        if not ok:
            return None

        risk = self._position_risk(decision)
        self.bankroll -= risk
        position = Position(
            market_id=decision.market_id,
            side=decision.side.upper(),
            entry_price=decision.price,
            size=decision.size,
            opened_at=decision.ts,
        )
        self.positions[decision.market_id] = position
        return position

    def settle(self, outcome: Outcome) -> Outcome:
        """Resolve a position and update bankroll and realized PnL."""
        position = self.positions.pop(outcome.market_id, None)
        if position is None:
            raise ValueError(f"No open position for market {outcome.market_id}")

        side = position.side.upper()

        if side == "YES":
            payout_per_contract = outcome.resolved_value
        elif side == "NO":
            payout_per_contract = 1 - outcome.resolved_value
        else:
            raise ValueError(f"Unsupported side: {position.side}")

        payout = payout_per_contract * position.size
        pnl = payout - position.risk()
        self.bankroll += payout

        resolved = Outcome(market_id=position.market_id, resolved_value=outcome.resolved_value, pnl=pnl)
        self.outcomes.append(resolved)
        return resolved

    def open_position_count(self) -> int:
        return len(self.positions)
