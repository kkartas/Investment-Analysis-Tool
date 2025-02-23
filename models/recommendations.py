# models/recommendations.py

import pandas as pd

# Map each rating label to a numeric score for averaging
RECOMMENDATION_MAP = {
    "Strong Buy": 1.0,
    "Buy": 2.0,
    "Hold": 3.0,
    "Sell": 4.0,
    "Strong Sell": 5.0
}

def get_market_recommendation(ticker):
    """
    Fetch the analyst recommendations from ticker.get_recommendations(),
    which returns a DataFrame with columns: 'strongBuy', 'buy', 'hold',
    'sell', 'strongSell' and 'period'.

    We'll:
      1. Sum up each of these columns for all rows.
      2. Convert them to a dictionary of counts, e.g. {"Strong Buy": <count>, "Buy": <count>, ...}
      3. Compute an average numeric rating, then map it back to a label.
      4. Return (string_label, dict_of_counts).

    If no data is found, returns ("N/A", {}).
    """

    try:
        df = ticker.get_recommendations()
        if df is None or df.empty:
            return "N/A", {}

        # The DataFrame has columns: [period, strongBuy, buy, hold, sell, strongSell].
        # We'll sum each rating across all rows.
        total_strong_buy = df["strongBuy"].sum(skipna=True)
        total_buy = df["buy"].sum(skipna=True)
        total_hold = df["hold"].sum(skipna=True)
        total_sell = df["sell"].sum(skipna=True)
        total_strong_sell = df["strongSell"].sum(skipna=True)

        # Put them in a dictionary with user-friendly keys
        grouped = {
            "Strong Buy": int(total_strong_buy),
            "Buy":        int(total_buy),
            "Hold":       int(total_hold),
            "Sell":       int(total_sell),
            "Strong Sell":int(total_strong_sell),
        }

        # Now compute the weighted average rating
        # We'll skip keys with zero counts to avoid dividing by zero.
        total_weight = 0.0
        total_count = 0
        for label, count_val in grouped.items():
            if count_val > 0 and label in RECOMMENDATION_MAP:
                total_weight += RECOMMENDATION_MAP[label] * count_val
                total_count += count_val

        if total_count == 0:
            return "N/A", {}

        avg_score = total_weight / total_count

        # Convert numeric avg back to a label
        # E.g. 1.0 = Strong Buy, 2.0 = Buy, 3.0 = Hold, 4.0 = Sell, 5.0 = Strong Sell
        if avg_score < 1.5:
            final_label = "Strong Buy"
        elif avg_score < 2.5:
            final_label = "Buy"
        elif avg_score < 3.5:
            final_label = "Hold"
        elif avg_score < 4.5:
            final_label = "Sell"
        else:
            final_label = "Strong Sell"

        return final_label, grouped

    except Exception as e:
        print("Error fetching market recommendations (get_recommendations):", e)
        return "N/A", {}
