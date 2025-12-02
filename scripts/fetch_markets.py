import requests
import csv
import re
from datetime import datetime, timedelta

# ----------------------------
# CONFIG
# ----------------------------


# ----------------------------
# KALSHI API
# ----------------------------
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2/markets"
KALSHI_HEADERS = {"Accept": "application/json"}

def fetch_kalshi_markets_next_7_days():
    all_markets = []
    cursor = None
    now = datetime.utcnow()
    max_close_ts = int((now + timedelta(days=10)).timestamp())

    print("Fetching Kalshi markets (closing within 7 days)...")
    while True:
        params = {
            "status": "open",
            "market_type": "binary",
            "limit": 500,
            "max_close_ts": max_close_ts
        }
        if cursor:
            params["cursor"] = cursor

        response = requests.get(KALSHI_API, headers=KALSHI_HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

        markets = data.get("markets", [])
        all_markets.extend(markets)

        print(f"  fetched {len(markets)} new markets, total so far: {len(all_markets)}")

        cursor = data.get("cursor")
        if not cursor:
            break

    print(f"Total Kalshi markets returned by API: {len(all_markets)}\n")
    return all_markets

# ----------------------------
# POLYMARKET API
# ----------------------------
POLY_BASE = "https://gamma-api.polymarket.com"
POLY_MARKETS_ENDPOINT = POLY_BASE + "/markets"

def fetch_polymarket_markets_next_7_days(limit=500):
    markets = []
    offset = 0
    now = datetime.utcnow()
    max_close = now + timedelta(days=10)

    print("Fetching Polymarket markets (closing within 7 days)...")
    while True:
        params = {"limit": limit, "offset": offset, "closed": False}
        resp = requests.get(POLY_MARKETS_ENDPOINT, params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            break

        markets.extend(data)
        offset += limit
        print(f"  fetched {len(data)} new markets, total so far: {len(markets)}", end="\r")

        if len(data) < limit:
            break

    # Filter by markets closing in next 7 days
    filtered = []
    for m in markets:
        try:
            end = datetime.fromisoformat(m["endDateIso"].replace("Z", "+00:00"))
            if now <= end <= max_close:
                filtered.append(m)
        except:
            filtered.append(m)

    print(f"\nTotal Polymarket markets closing in next 7 days: {len(filtered)}\n")
    return filtered

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def extract_number(text):
    if text is None:
        return None
    text = str(text).replace(",", "")  # convert to string first
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if match:
        return float(match.group())
    return None
if __name__ == "__main__":
    kalshi = fetch_kalshi_markets_next_7_days()
    poly = fetch_polymarket_markets_next_7_days(limit=500)
