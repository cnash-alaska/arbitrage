import requests
import csv
import re
from datetime import datetime, timedelta

# ----------------------------
# CONFIG
# ----------------------------
KEYWORD = "unemployment"

# ----------------------------
# KALSHI API
# ----------------------------
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2/markets"
KALSHI_HEADERS = {"Accept": "application/json"}

def fetch_kalshi_markets_next_7_days():
    all_markets = []
    cursor = None
    now = datetime.utcnow()
    max_close_ts = int((now + timedelta(days=7)).timestamp())

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
    max_close = now + timedelta(days=7)

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
    text = str(text).replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if match:
        return float(match.group())
    return None

def extract_range(market):
    """Return floor, ceiling, and midpoint for a Kalshi market."""
    floor = extract_number(market.get("floor_strike"))
    ceiling = extract_number(market.get("ceiling_strike"))
    if floor is None and ceiling is None:
        return None, None, None
    if floor is None:
        floor = ceiling
    if ceiling is None:
        ceiling = floor
    midpoint = (floor + ceiling) / 2
    return floor, ceiling, midpoint

def pick_best_strike(floor, ceiling, midpoint, target):
    """Return the Kalshi value closest to the Polymarket target."""
    options = [v for v in [floor, midpoint, ceiling] if v is not None]
    return min(options, key=lambda x: abs(x - target))

# ----------------------------
# MATCHING FUNCTION
# ----------------------------
def match_markets_by_best_strike(kalshi_markets, polymarket_markets):
    matches = []
    print("Matching Kalshi markets to Polymarket markets by closest strike...")

    for k in kalshi_markets:
        floor, ceiling, midpoint = extract_range(k)
        if floor is None and ceiling is None:
            continue

        for p in polymarket_markets:
            p_target = extract_number(p.get("question", "") or p.get("groupItemTitle", ""))
            if p_target is None:
                continue

            best_strike = pick_best_strike(floor, ceiling, midpoint, p_target)

            # Only include if Kalshi strike is close enough to Polymarket target
            if abs(best_strike - p_target) <= 0.5:  # adjust tolerance if needed
                matches.append({
                    "kalshi_ticker": k.get("ticker"),
                    "kalshi_strike": best_strike,
                    "kalshi_question": k.get("title"),
                    "kalshi_last_price": k.get("last_price") or 0,
                    "polymarket_id": p.get("id"),
                    "polymarket_target": p_target,
                    "polymarket_question": p.get("question"),
                    "polymarket_last_price": float(p.get("lastTradePrice", 0))
                })

    print(f"Found {len(matches)} matches.\n")
    return matches

# ----------------------------
# SAVE CSV
# ----------------------------
def save_matches_csv(matches, filename="unemployment_matches.csv"):
    matches = [m for m in matches if m["kalshi_ticker"] and "KXU3" in m["kalshi_ticker"]]

    if not matches:
        print("No matches to save after filtering by Kalshi ticker.")
        return

    fieldnames = [
        "kalshi_ticker",
        "kalshi_strike",
        "kalshi_question",
        "kalshi_last_price",
        "polymarket_id",
        "polymarket_target",
        "polymarket_question",
        "polymarket_last_price"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in matches:
            writer.writerow(m)

    print(f"Saved {len(matches)} matches to {filename}\n")

# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == "__main__":
    kalshi = fetch_kalshi_markets_next_7_days()
    poly = fetch_polymarket_markets_next_7_days(limit=500)

    kalshi_filtered = [k for k in kalshi if KEYWORD.lower() in (k.get("title") or "").lower()]
    poly_filtered = [p for p in poly if KEYWORD.lower() in (p.get("question") or "").lower()]

    print(f"Filtering markets by keyword...\n  Kalshi markets after keyword filter: {len(kalshi_filtered)}\n  Polymarket markets after keyword filter: {len(poly_filtered)}\n")

    matches = match_markets_by_best_strike(kalshi_filtered, poly_filtered)
    save_matches_csv(matches)
