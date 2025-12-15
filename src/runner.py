from itertools import islice
from src.api.kalshi_client import KalshiClient
from src.data.sqlite_store import upsert_markets, insert_snapshot_now

def main():
    client = KalshiClient()

    # 1) Pull a small page of markets and upsert into SQLite
    first_markets = list(islice(client.get_markets_paginated(limit=50), 0, 50))
    if not first_markets:
        print("No markets returned.")
        return
    upsert_markets(first_markets)
    print(f"Upserted {len(first_markets)} markets.")

    # 2) Take a single snapshot on the first market
    ticker = first_markets[0]["ticker"]
    ob = client.get_market_orderbook(ticker)
    yes = ob.get("orderbook", {}).get("yes", [])
    no  = ob.get("orderbook", {}).get("no", [])
    insert_snapshot_now(ticker, yes, no)
    print(f"Snapshot saved for {ticker}.")

if __name__ == "__main__":
    main()

