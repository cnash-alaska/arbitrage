import pandas as pd

markets = ['bitcoin']

def arbitrage_analysis(poly_yes, poly_volume, kalshi_yes, kalshi_volume, max_skew=0.75):
    epsilon = 1e-9  # small number to avoid division by zero

    # Determine lower/higher yes probability
    if poly_yes > kalshi_yes:
        buy_yes = 'Kalshi'
        buy_no = 'Poly'
        P_L, P_H = kalshi_yes, poly_yes
        P_Lvol, P_Hvol = kalshi_volume, poly_volume
    else:
        buy_yes = 'Poly'
        buy_no = 'Kalshi'
        P_L, P_H = poly_yes, kalshi_yes
        P_Lvol, P_Hvol = poly_volume, kalshi_volume

    # Safeguard probabilities
    P_H = max(P_H, epsilon)
    P_L = max(P_L, 0.0)
    P_H = min(P_H, 1 - epsilon)
    P_L = min(P_L, 1 - epsilon)

    # Arbitrage bounds
    lower_multiple = P_L / P_H
    upper_multiple = (1 - P_L) / (1 - P_H)

    # Volume fraction, safeguard zero total volume
    total_vol = P_Lvol + P_Hvol
    if total_vol == 0:
        vol_fraction = 0.5  # neutral
    else:
        vol_fraction = P_Lvol / total_vol

    # Skew
    skew = max_skew * (vol_fraction - 0.5) * 2  # capped
    mid = (lower_multiple + upper_multiple) / 2
    half_range = (upper_multiple - lower_multiple) / 2
    multiplier = mid + skew * half_range

    return buy_yes, buy_no, lower_multiple, upper_multiple, multiplier


results = []

for m in markets:
    csv_path = f'markets/{m}/current_market.csv'
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        buy_yes, buy_no, lower, upper,mult, = arbitrage_analysis(
            row['polymarket_last_price'],
            row['polymarket_dollars_invested'],
            row['kalshi_last_price'],
            row['kalshi_dollars_invested']
        )
        if upper > 5:
            continue
        results.append({
            'market': m,
            'kalshi_ticker': row['kalshi_ticker'],
            'kalshi_yes_price': row['kalshi_last_price'],
            'poly_ticker': row['polymarket_id'],
            'poly_yes_price': row['polymarket_last_price'],
            'buy_yes': buy_yes,
            'buy_no': buy_no,
            'lower_multiple': lower,
            'upper_multiple': upper,
            'multiplier': mult
        })

results_df = pd.DataFrame(results)
results_df.to_csv('trades/temp/arbitrage_formula_results.csv', index=False)
print("CSV saved as trades/temp/arbitrage_formula_results.csv")


