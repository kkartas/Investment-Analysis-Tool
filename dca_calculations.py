# dca_calculations.py

import numpy as np
import pandas as pd

def calculate_average_interest(data):
    data['Return'] = data['Close'].pct_change()
    return data['Return'].mean() * 252  # Annualized daily return

def dca_calculation(data, initial_investment, periodic_investment, period, years, average_interest=None, reinvest=True):
    if average_interest is None:
        average_interest = calculate_average_interest(data)
    
    periods_per_year = {'daily': 252, 'monthly': 12, 'yearly': 1}[period]
    total_periods = periods_per_year * years
    rate_per_period = average_interest / periods_per_year

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
    return total_invested, future_value, total_profit, profit_taken, reinvested_profit, future_values, invested_values
