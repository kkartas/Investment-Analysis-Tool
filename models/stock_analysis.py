import pandas as pd
from typing import Optional, Tuple


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators such as SMA, RSI, MACD and Signal Line.
    """
    df = data.copy()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # RSI calculation
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD calculation
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    return df

def get_latest_recommendation(data: pd.DataFrame) -> Tuple[Optional[pd.Series], str]:
    valid_data = data.dropna(subset=['SMA_50', 'SMA_200', 'RSI', 'MACD', 'Signal_Line'])
    if valid_data.empty:
        # Not enough data for full technical analysis
        return None, ""
    
    latest_data = valid_data.iloc[-1]
    recommendation = "Hold"
    if (latest_data['Close'] > latest_data['SMA_50'] > latest_data['SMA_200'] and 
        latest_data['RSI'] < 70 and 
        latest_data['MACD'] > latest_data['Signal_Line']):
        recommendation = "Buy"
    elif (latest_data['Close'] < latest_data['SMA_50'] < latest_data['SMA_200'] or 
          latest_data['RSI'] > 70 or 
          latest_data['MACD'] < latest_data['Signal_Line']):
        recommendation = "Sell"
        
    return latest_data, recommendation

import pandas as pd

def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators:
      - 50-day and 200-day SMA
      - RSI (14-day)
      - MACD and Signal Line
      - Bollinger Bands (20-day MA ± 2 standard deviations)
      - Average True Range (ATR, 14-day)
    """
    df = data.copy()
    
    # SMAs
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI Calculation
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD & Signal Line
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
        # Not enough data: create the columns with NaN values
        df['MA'] = pd.Series([float('nan')]*len(df), index=df.index)
        df['STD'] = pd.Series([float('nan')]*len(df), index=df.index)
        df['Upper_Band'] = pd.Series([float('nan')]*len(df), index=df.index)
        df['Lower_Band'] = pd.Series([float('nan')]*len(df), index=df.index)
    
    # ATR Calculation
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