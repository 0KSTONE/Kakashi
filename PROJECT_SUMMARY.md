# Kakashi (money-first) handoff snapshot

A disciplined, test-first Kalshi trading bot focused on reliability and paper-trade validation before any live orders or modeling.

## TL;DR
- Goal: automate paper trades on one binary market, track PnL, and produce repeatable post-mortems.
- Approach: plumbing-first (data intake + schemas + simple strategy + risk controls + automation/reporting). No ML until clean logs prove repeatable edge.

## Current status (~45% to first paper deployment)
- [done] Threshold strategy and EV/risk tests.
- [done] Read-only Kalshi client with pagination/backoff and smoke tests.
- [done] SQLite persistence and runnable data loop (sample-only by default; falls back on API errors).
- [done] Paper trader simulator with decision logging and bankroll updates.
- [todo] Live paper-trade loop wiring, scheduler, reporting/post-mortems.

## Roadmap and deliverables
**Phase 0 - Guardrails (done)**
- `rules.md`, `risk_limits.md`: max loss 1%/trade, <=5 open positions, daily loss cap, paper trading required.

**Phase 1 - Data center (baseline in place)**
- `src/api/kalshi_client.py`: read-only resilient HTTP client with pagination/backoff.
- `src/data/sqlite_store.py`: `markets`, `snapshots` tables.
- `src/runner.py`: single-run snapshot + upsert flow (sample data by default, falls back on API errors).
- Smoke test: `tests/test_kalshi_client_smoke.py`.
- DS lessons: sampling cadence, timestamp integrity, schema separation.

**Phase 2 - Strategy + risk (in progress)**
- `src/strategy/threshold.py`: baseline EV strategy with caps and tests.
- `src/execution/paper_trader.py`: simulate fills, update bankroll, log decisions, enforce risk caps.
- Next: integrate decisions into runner, log trades to storage, and surface open risk/PNL.

**Phase 3 - Automation & safety (next)**
- Scheduler (APScheduler/cron), kill switch, daily hard-stop, retries/sanity checks.
- DS lessons: reproducible pipelines, runbooks.

**Phase 4 - Reporting & audit**
- `reports/bankroll.png`, drawdown, edge hist; weekly post-mortem template auto-filled.
- DS lessons: statistical significance, variance vs signal.

**Phase 5 - Later (modeling/scale)**
- Only after month+ of clean paper logs and stable positive EV: basic logistic/regression with careful backtests.

## Files that must exist (sanity checklist)
```
requirements.txt
rules.md
risk_limits.md
data_schema.md
src/__init__.py
src/api/__init__.py
src/api/kalshi_client.py
src/data/__init__.py
src/data/sqlite_store.py
src/models/schemas.py
src/strategy/threshold.py
src/execution/__init__.py
src/execution/paper_trader.py
src/runner.py
tests/test_threshold.py
tests/test_paper_trader.py
tests/test_sqlite_store.py
tests/test_kalshi_client_smoke.py
```

## Next commands to run
1. Ensure the above files exist and are current.
2. Create venv, install deps, and run tests:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # on Windows; use source .venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   pytest -q
   python -m src.runner
   ```
   Expect markets upserted and a snapshot saved; say "runner ran" when it prints `Snapshot saved for <TICKER>`.

## Teaching timeline (inline with code)
- Data collection: pagination, backoff, collector timestamp importance.
- Schema validation: strict types, reject corrupt rows, raw vs processed separation.
- Expected Value: EV = p_hat - price; positive EV is necessary but not guaranteed profit.
- Position sizing: max-risk-per-trade, discrete sizing, worst-case loss, risk-of-ruin intuition.
- Backtest & stats: variance, sampling error, confidence intervals, beware lucky streaks.
- Automation & ops: cron vs scheduler, logging standards, kill switch, alerts.
- When to add ML: only after sustained clean paper logs with stable EV above noise.

## Quick copy/paste prompts for Codex
**1) Create Kalshi client**
```
Create a read-only Kalshi HTTP client in Python at src/api/kalshi_client.py.
- Use requests.Session, 3 retry attempts, exponential backoff for 429/5xx.
- Methods: get_markets_paginated(limit), get_market_orderbook(ticker).
- Return parsed JSON; raise clear KalshiHTTPError for non-retryable failures.
- Add a simple smoke test tests/test_kalshi_client_smoke.py.
```

**2) Create SQLite store**
```
Create src/data/sqlite_store.py to:
- create tables markets and snapshots if missing,
- upsert markets (ON CONFLICT),
- insert snapshot with UTC epoch ms ts.
Include schema and helper to inspect latest snapshot rows.
```

**3) Add Pydantic validation**
```
Add src/models/schemas.py with Pydantic models for Market, Snapshot, Trade, Outcome.
Use validators to enforce 0<=price<=1 and ask>=bid. Integrate validation into sqlite_store insert.
```

**4) Add paper trader simulator**
```
Create src/execution/paper_trader.py to:
- simulate fills from TradeDecision objects,
- enforce risk caps and max open positions,
- update bankroll and log decisions/outcomes,
- provide settlement helper that returns Outcome with pnl.
Add tests in tests/test_paper_trader.py.
```

Keep this file close -- paste sections into Codex or PR descriptions to preserve the DS lessons while coding.
