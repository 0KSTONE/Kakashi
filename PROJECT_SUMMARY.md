# Kakashi (money-first) — handoff snapshot

A disciplined, test-first Kalshi trading bot focused on reliability and paper-trade validation before any live orders or modeling.

## TL;DR
- Goal: automate paper trades on one binary market, track PnL, and produce repeatable post-mortems.
- Approach: plumbing-first (data intake → schemas → simple strategy → risk controls → automation/reporting). No ML until clean logs prove repeatable edge.

## Current status (~30% to first paper deployment)
- ✅ Threshold strategy and tests in place.
- ✅ Skeleton + requirements committed.
- ⚙️ Kalshi read-only client drafted (needs hardening and pagination checks).
- ⚙️ SQLite persistence + runner drafted; package stubs/push in progress.
- ⏳ Paper-trade loop & scheduler: not started.
- ⏳ Reporting/post-mortems: not started.

## Roadmap and deliverables
**Phase 0 — Guardrails (done)**
- `rules.md`, `risk_limits.md`: max loss 1%/trade, ≤5 open positions, daily loss cap, paper trading required.

**Phase 1 — Data center (in progress)**
- `src/api/kalshi_client.py`: read-only resilient HTTP client with pagination/backoff.
- `src/data/sqlite_store.py`: `markets`, `snapshots` tables.
- `src/runner.py`: single-run snapshot + upsert flow.
- Smoke test: `tests/test_kalshi_client_smoke.py`.
- DS lessons: sampling cadence, timestamp integrity, schema separation.

**Phase 2 — Strategy + risk (next)**
- `src/strategy/threshold.py` (done), decision logging, `src/execution/paper_trader.py` (simulate fills, update bankroll).
- DS lessons: EV math, position sizing, risk of ruin.

**Phase 3 — Automation & safety**
- Scheduler (APScheduler/cron), kill switch, daily hard-stop, retries/sanity checks.
- DS lessons: reproducible pipelines, runbooks.

**Phase 4 — Reporting & audit**
- `reports/bankroll.png`, drawdown, edge hist; weekly post-mortem template auto-filled.
- DS lessons: statistical significance, variance vs signal.

**Phase 5 — Later (modeling/scale)**
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
src/runner.py
tests/test_threshold.py
tests/test_kalshi_client_smoke.py
```

## Next commands to run
1. Ensure the above files exist and are current.
2. Create venv, install deps, and run tests:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pytest -q
   python -m src.runner
   ```
   Expect markets upserted and a snapshot saved; say **"runner ran"** when it prints `Snapshot saved for <TICKER>`.

## Teaching timeline (inline with code)
- Data collection: pagination, backoff, collector timestamp importance.
- Schema validation: strict types, reject corrupt rows, raw vs processed separation.
- Expected Value: EV = \hat{p} - price; positive EV ≠ guaranteed profit.
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

Keep this file close — paste sections into Codex or PR descriptions to preserve the DS lessons while coding.
