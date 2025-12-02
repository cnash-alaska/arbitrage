import pandas as pd

markets = ['bitcoin']
def arbitrage_analysis(poly_yes, poly_volume, kalshi_yes, kalshi_volume, max_skew=0.75):
    epsilon = 1e-12  # avoid div-by-zero

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
    P_L = min(max(P_L, epsilon), 1 - epsilon)
    P_H = min(max(P_H, epsilon), 1 - epsilon)

    # Arbitrage bounds
    lower_multiple = P_L / P_H
    upper_multiple = (1 - P_L) / (1 - P_H)

    # If no arbitrage exists (degenerate case)
    if lower_multiple >= upper_multiple:
        multiplier = None
        return buy_yes, buy_no, lower_multiple, upper_multiple, multiplier

    # -------- Guaranteed-profit multiplier (M_star) --------
    # This multiplier equalizes profits for both outcomes (max-min arbitrage).
    M_star = (P_H - P_L) / (1 - P_L - (P_H - P_L))

    # Clamp inside arbitrage interval for safety
    M_star = max(min(M_star, upper_multiple), lower_multiple)

    # Use M_star as your multiplier
    multiplier = M_star

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


