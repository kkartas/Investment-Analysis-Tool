# stock_analysis.py

import pandas as pd

def calculate_indicators(data):
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()
    delta = data['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.rolling(window=14).mean()
    avg_loss = down.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    return data

def get_latest_recommendation(data):
    latest = data.iloc[-1]
    recommendation = "Hold"
    if latest['SMA_50'] > latest['SMA_200'] and latest['RSI'] < 70 and latest['MACD'] > latest['Signal_Line']:
        recommendation = "Buy"
    elif latest['SMA_50'] < latest['SMA_200'] and latest['RSI'] > 30 and latest['MACD'] < latest['Signal_Line']:
        recommendation = "Sell"
    return latest, recommendation
