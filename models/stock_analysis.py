# models/stock_analysis.py
import pandas as pd

def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators:
      - 50-day and 200-day SMA
      - RSI (14-day)
      - MACD and Signal Line
      - Bollinger Bands (20-day MA ± 2 std)
      - Average True Range (ATR, 14-day)
    """
    df = data.copy()

    # SMAs
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD & Signal
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    window = 20
    if len(df) >= window:
        df['MA'] = df['Close'].rolling(window=window).mean()
        df['STD'] = df['Close'].rolling(window=window).std()
        df['Upper_Band'] = df['MA'] + (df['STD'] * 2)
        df['Lower_Band'] = df['MA'] - (df['STD'] * 2)
    else:
        df['MA'] = float('nan')
        df['STD'] = float('nan')
        df['Upper_Band'] = float('nan')
        df['Lower_Band'] = float('nan')

    # ATR
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()

    return df

def get_latest_recommendation(data: pd.DataFrame):
    """
    Returns the latest row of data and a recommendation based on SMA, RSI, and MACD.
    If critical values (50-day or 200-day SMA) are missing, returns "N/A" as recommendation.
    """
    valid_data = data.dropna(subset=['SMA_50', 'SMA_200', 'RSI', 'MACD', 'Signal_Line'])
    if valid_data.empty:
        return None, "N/A"

    latest = valid_data.iloc[-1]
    recommendation = "Hold"
    if latest['Close'] > latest['SMA_50'] > latest['SMA_200'] and latest['RSI'] < 70 and latest['MACD'] > latest['Signal_Line']:
        recommendation = "Buy"
    elif latest['Close'] < latest['SMA_50'] < latest['SMA_200'] or latest['RSI'] > 70 or latest['MACD'] < latest['Signal_Line']:
        recommendation = "Sell"
    return latest, recommendation

def compute_sharpe_ratio(data: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
    """
    Compute the annualized Sharpe Ratio for the stock data.
    risk_free_rate is in decimal form (e.g., 0.02 = 2%).
    """
    df = data.copy()
    df['daily_return'] = df['Close'].pct_change()
    # Subtract daily risk-free rate
    daily_rf = risk_free_rate / 252
    df['excess_return'] = df['daily_return'] - daily_rf

    avg_excess = df['excess_return'].mean()
    std_excess = df['excess_return'].std()
    if std_excess == 0 or pd.isna(std_excess):
        return 0.0

    # Annualize
    sharpe_ratio = (avg_excess * 252) / (std_excess * (252**0.5))
    return round(sharpe_ratio, 2)
