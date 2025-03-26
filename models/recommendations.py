# models/recommendations.py

import pandas as pd
from datetime import datetime, timedelta

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
    Fetch the analyst recommendations from Yahoo Finance API.
    We'll use the most recent month's data from get_recommendations_summary.
    
    Returns:
        tuple: (recommendation_label, counts_dictionary)
        Where recommendation_label is a string like "Buy", "Hold", etc.
        And counts_dictionary has keys like "Strong Buy", "Buy", etc. with integer values.
    
    If no data is found, returns ("N/A", {}).
    """
    try:
        # Try to get recommendations data
        recommendations_df = ticker.get_recommendations_summary()
        if recommendations_df is None or recommendations_df.empty:
            recommendations_df = ticker.get_recommendations()
            
        if recommendations_df is None or recommendations_df.empty:
            print(f"No recommendations data found for {ticker.ticker}")
            return "N/A", {}
            
        # Get the most recent month's data (first row)
        recent_data = recommendations_df.iloc[0]
        
        # Extract the recommendation counts
        grouped = {
            "Strong Buy": int(recent_data.get("strongBuy", 0)),
            "Buy": int(recent_data.get("buy", 0)),
            "Hold": int(recent_data.get("hold", 0)),
            "Sell": int(recent_data.get("sell", 0)),
            "Strong Sell": int(recent_data.get("strongSell", 0)),
        }
        
        # Debug info
        print(f"Recommendations for {ticker.ticker}: {grouped}")
        
        # Calculate weighted average
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
        print(f"Error fetching recommendations for {ticker.ticker}: {e}")
        return "N/A", {}
