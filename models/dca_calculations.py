import pandas as pd

def calculate_average_annual_return(data: pd.DataFrame) -> float:
    """
    Calculate the annualized average return based on daily percentage changes.
    """
    df = data.copy()
    df['Return'] = df['Close'].pct_change()
    return df['Return'].mean() * 252  # Approximate annualization

def dca_calculation(data: pd.DataFrame, initial_investment: float, periodic_investment: float,
                    frequency: str, years: int, annual_return: float, reinvest: bool = True):
    """
    Simulate a Dollar-Cost Averaging investment strategy.
    """
    freq_map = {'daily': 252, 'weekly': 52, 'monthly': 12, 'quarterly': 4, 'yearly': 1}
    periods_per_year = freq_map.get(frequency.lower(), 12)  # Default to monthly if not found
    total_periods = periods_per_year * years
    rate_per_period = annual_return / periods_per_year

    total_invested = initial_investment
    portfolio_value = initial_investment
    invested_history = [total_invested]
    value_history = [portfolio_value]
    reinvested_profit = 0
    profit_taken = 0

    if len(data) < total_periods:
        total_periods = len(data)
    
    for _ in range(1, total_periods + 1):
        interest = portfolio_value * rate_per_period
        if reinvest:
            portfolio_value += interest
            reinvested_profit += interest
        else:
            profit_taken += interest
        portfolio_value += periodic_investment
        total_invested += periodic_investment
        invested_history.append(total_invested)
        value_history.append(portfolio_value)

    total_profit = reinvested_profit + profit_taken

    # Create a timeline based on the data (using a default monthly frequency)
    dates = pd.date_range(start=data.index.min(), periods=total_periods, freq='M')
    data_points = {
        'dates': dates,
        'invested': invested_history,
        'value': value_history
    }
    return total_invested, portfolio_value, total_profit, data_points
