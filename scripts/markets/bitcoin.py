import requests
import csv
import re
from datetime import datetime, timedelta

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


# ----------------------------
# MATCHING FUNCTION
# ----------------------------
from datetime import datetime
import re
KEYWORD = "bitcoin"
def extract_number(text):
    if not text:
        return None
    match = re.search(r"\d+\.?\d*", str(text).replace(",", ""))
    return float(match.group()) if match else None

def match_bitcoin_markets(kalshi_markets, polymarket_markets, max_strike_diff=5):
    """
    Match Kalshi and Polymarket bitcoin markets 1-to-1 by closest strike and date.
    Only matches if the numeric strikes are within max_strike_diff.
    """
    matches = []
    print("Matching Kalshi markets to Polymarket markets by closest strike and date (1-to-1)...")

    # --------------------------
    # FILTER MARKETS
    # --------------------------
    kalshi_filtered = [k for k in kalshi_markets if "KXBTCD" in (k.get("ticker") or "")]
    polymarket_filtered = [
        p for p in polymarket_markets
        if p.get("question") and re.search(r"\b(above|greater than)\b", p["question"], re.IGNORECASE)
    ]

    # Parse Polymarket end dates and numeric strike
    for p in polymarket_filtered:
        try:
            p["end_date_obj"] = datetime.fromisoformat(
                p.get("iso_date") or p.get("endDateIso", "")
            ).date()
        except:
            p["end_date_obj"] = None
        p["poly_strike"] = extract_number(p.get("group_item_title") or p.get("question"))

    matched_poly_ids = set()
    matched_kalshi_tickers = set()

    # --------------------------
    # MATCHING LOOP
    # --------------------------
    for k in kalshi_filtered:
        if k.get("floor_strike") is None:
            continue
        k_strike = extract_number(k.get("floor_strike"))

        try:
            k_date = datetime.fromisoformat(k.get("expected_expiration_time").replace("Z", "+00:00")).date()
        except:
            continue

        if k.get("ticker") in matched_kalshi_tickers:
            continue  # skip if this Kalshi ticker already matched

        # Candidates: Polymarket markets with same date and unmatched
        poly_candidates = [
            p for p in polymarket_filtered
            if p["end_date_obj"] == k_date
            and p.get("id") not in matched_poly_ids
            and p.get("poly_strike") is not None
            and abs(k_strike - p["poly_strike"]) <= max_strike_diff  # <-- ensure within range
        ]

        if not poly_candidates:
            continue

        # Find closest strike among candidates
        best_poly = min(poly_candidates, key=lambda p: abs(k_strike - p["poly_strike"]))

        matched_poly_ids.add(best_poly["id"])
        matched_kalshi_tickers.add(k.get("ticker"))

        matches.append({
            "kalshi_ticker": k.get("ticker"),
            "kalshi_event_ticker": k.get("event_ticker"),
            "kalshi_market_type": k.get("market_type"),
            "kalshi_rules_primary": k.get("rules_primary"),
            "kalshi_floor_strike": k_strike,
            "kalshi_strike_type": k.get("strike_type"),
            "polymarket_id": best_poly.get("id"),
            "polymarket_question": best_poly.get("question"),
            "polymarket_end_date": best_poly.get("iso_date") or best_poly.get("endDateIso"),
            "polymarket_strike": best_poly.get("poly_strike")
        })

    print(f"Found {len(matches)} matches (1-to-1, filtered by ticker, date, question, strike, and max_diff={max_strike_diff}).\n")
    return matches




# ----------------------------
# SAVE CSV
# ----------------------------
def save_matches_csv(matches, filename="markets/bitcoin/bitcoin_matches.csv"):
    if not matches:
        print("No matches to save.")
        return

    fieldnames = [
        "kalshi_ticker",
        "kalshi_strike",
        "kalshi_question",
        "kalshi_last_price",
        "kalshi_rules_primary",
        "kalshi_strike_type",
        "kalshi_market_type",
        "kalshi_event_ticker",
        "kalshi_floor_strike",
        "polymarket_id",
        "polymarket_strike",
        "polymarket_question",
        "polymarket_last_price",
        "polymarket_end_date"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in matches:
            writer.writerow(m)

    print(f"Saved {len(matches)} matches to {filename}\n")

# ----------------------------
# MAIN EXECUTION

import pandas as pd
import requests
import ast  # to parse Polymarket outcomePrices

# -----------------------------
# ENDPOINTS
# -----------------------------
KALSHI_MARKET_URL = "https://api.elections.kalshi.com/trade-api/v2/markets/{}"
POLY_MARKET_URL = "https://gamma-api.polymarket.com/markets/{}"


# -----------------------------
# Fetch Kalshi Yes Price and dollars invested
# -----------------------------
def fetch_kalshi_market_info(ticker):
    try:
        url = KALSHI_MARKET_URL.format(ticker)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("market", {})

        yes_ask_raw = data.get("yes_ask")
        notional = data.get("notional_value", 100)
        yes_price = yes_ask_raw / notional if yes_ask_raw is not None else None
        dollars_invested = yes_ask_raw * notional if yes_ask_raw is not None else None

        print(f"Kalshi: {ticker} yes price = {yes_price}, dollars invested = {dollars_invested}")
        return yes_price, dollars_invested

    except Exception as e:
        print(f"[Kalshi ERROR] {ticker}: {e}")
        return None, None


# -----------------------------
# Fetch Polymarket Yes Price and dollars invested
# -----------------------------
def fetch_polymarket_market_info(event_id):
    try:
        url = POLY_MARKET_URL.format(event_id)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        prices = ast.literal_eval(data.get("outcomePrices", "[]"))
        yes_price = float(prices[0]) if len(prices) > 0 else None

        volume_num = float(data.get("volumeNum", 0))
        dollars_invested = yes_price * volume_num if yes_price is not None else None

        print(f"Polymarket: {event_id} yes price = {yes_price}, dollars invested = {dollars_invested}")
        return yes_price, dollars_invested

    except Exception as e:
        print(f"[Polymarket ERROR] {event_id}: {e}")
        return None, None


# -----------------------------
# Build table with Yes price and dollars invested
# -----------------------------
def build_market_table(csv_path):
    df = pd.read_csv(csv_path)

    kalshi_prices = []
    kalshi_dollars = []
    poly_prices = []
    poly_dollars = []

    print("\nFetching Yes prices and dollars invested for all rows…\n")

    for i, row in df.iterrows():
        kalshi_ticker = row["kalshi_ticker"]
        polymarket_id = row["polymarket_id"]

        kalshi_yes, kalshi_dollar = fetch_kalshi_market_info(kalshi_ticker)
        poly_yes, poly_dollar = fetch_polymarket_market_info(polymarket_id)

        kalshi_prices.append(kalshi_yes)
        kalshi_dollars.append(kalshi_dollar)
        poly_prices.append(poly_yes)
        poly_dollars.append(poly_dollar)

        print(f"Row {i+1}/{len(df)} processed.\n")

    df["kalshi_yes_price"] = kalshi_prices
    df["kalshi_dollars_invested"] = kalshi_dollars
    df["polymarket_yes_price"] = poly_prices
    df["polymarket_dollars_invested"] = poly_dollars

    return df
def fetch_kalshi_polymarket_info(kalshi_ticker, polymarket_id):
    result = {}

    # --- Fetch Kalshi ---
    try:
        url = KALSHI_MARKET_URL.format(kalshi_ticker)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        k_data = resp.json().get("market", {})

        result["kalshi_event_ticker"] = k_data.get("event_ticker")
        result["kalshi_market_type"] = k_data.get("market_type")
        result["kalshi_rules_primary"] = k_data.get("rules_primary")

        # Grab any key containing 'strike'
        for key, val in k_data.items():
            if "strike" in key.lower():
                result[f"kalshi_{key}"] = val

    except Exception as e:
        print(f"[Kalshi ERROR] {kalshi_ticker}: {e}")

    # --- Fetch Polymarket ---
    try:
        url = POLY_MARKET_URL.format(polymarket_id)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        p_data = resp.json()

        result["polymarket_id"] = p_data.get("id")
        result["polymarket_question"] = p_data.get("question")
        result["polymarket_end_date"] = p_data.get("endDateIso") or p_data.get("end_date")

    except Exception as e:
        print(f"[Polymarket ERROR] {polymarket_id}: {e}")

    return result


# -----------------------------
# RUN SCRIPT
# -----------------------------
if __name__ == "__main__":
    # Filter by keyword "bitcoin"
    kalshi_filtered = [k for k in kalshi if KEYWORD.lower() in (k.get("title") or "").lower()]
    poly_filtered = [p for p in poly if KEYWORD.lower() in (p.get("question") or "").lower()]

    print(f"Filtering markets by keyword...\n  Kalshi markets after keyword filter: {len(kalshi_filtered)}\n  Polymarket markets after keyword filter: {len(poly_filtered)}\n")

    matches = match_bitcoin_markets(kalshi_filtered, poly_filtered)
    save_matches_csv(matches)

    df = build_market_table("markets/bitcoin/bitcoin_matches.csv")
    print("Done! Saved current_matches_info.csv with Yes prices and dollars invested from both markets.")

    df = df.rename(columns={
        "polymarket_yes_price": "polymarket_last_price",
        "kalshi_yes_price": "kalshi_last_price"
    })

    # Collect additional metadata from Kalshi/Polymarket without losing price columns
    info_list = []
    for _, row in df.iterrows():
        info = fetch_kalshi_polymarket_info(row['kalshi_ticker'], row['polymarket_id'])
        info_list.append(info)

    df_info = pd.DataFrame(info_list)
    df_info = df_info.rename(columns={
        "kalshi_last_price": "kalshi_last_price_meta",
        "polymarket_last_price": "poly_last_price_meta"
    })

    # Merge the metadata with the original table to preserve all price columns
    final = pd.concat([df.reset_index(drop=True), df_info.reset_index(drop=True)], axis=1)
    # Drop the first column named 'kalshi_last_price' if duplicates exist
    final = final.loc[:, ~final.columns.duplicated(keep='last')]

    # Save combined CSV
    final.to_csv('markets/bitcoin/bitcoin_validity_check.csv', index=False)

    df = df.loc[:, ~df.columns.duplicated(keep='last')]
    df.to_csv("markets/bitcoin/current_market.csv", index=False)



