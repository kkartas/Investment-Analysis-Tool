import numpy as np
import pandas as pd

def calculate_average_interest(data):
    """
    Calculate the average annual return based on the historical closing prices in the data.
    
    Args:
        data (pd.DataFrame): A DataFrame containing historical stock data with a 'Close' column.
    
    Returns:
        float: The calculated average annual return.
    """
    data['Return'] = data['Close'].pct_change()
    return data['Return'].mean() * 252  # Annualized daily return

def dca_calculation(data, initial_investment, periodic_investment, period, years, average_interest=None, reinvest=True):
    if average_interest is None:
        average_interest = calculate_average_interest(data)
    
    # Update periods_per_year to include 'quarterly'
    periods_per_year = {'daily': 252, 'weekly': 52, 'monthly': 12, 'quarterly': 4, 'yearly': 1}
    total_periods = periods_per_year[period] * years
    rate_per_period = average_interest / periods_per_year[period]

    total_invested = initial_investment
    future_value = initial_investment
    future_values = [future_value]
    invested_values = [total_invested]
    profit_taken = 0
    reinvested_profit = 0

    for i in range(1, total_periods + 1):
        interest_earned = future_value * rate_per_period
        if reinvest:
            future_value += interest_earned
            reinvested_profit += interest_earned
        else:
            profit_taken += interest_earned
        future_value += periodic_investment
        total_invested += periodic_investment
        future_values.append(future_value)
        invested_values.append(total_invested)

    total_profit = reinvested_profit + profit_taken

    # Handle frequency for quarterly periods in dates
    freq_map = {
        'daily': 'B',
        'weekly': 'W',
        'monthly': 'M',
        'quarterly': 'Q',
        'yearly': 'A'
    }
    dates = pd.date_range(start=pd.Timestamp.today(), periods=total_periods, freq=freq_map[period])

    data_points = {
        'dates': dates,
        'invested': invested_values,
        'value': future_values
    }

    return total_invested, future_value, total_profit, data_points
