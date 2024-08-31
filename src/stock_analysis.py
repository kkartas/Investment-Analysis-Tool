import pandas as pd

def calculate_indicators(data):
    data = data.copy()  # Avoid modifying the original DataFrame directly
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
    data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = data['EMA_12'] - data['EMA_26']
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    return data

def get_latest_recommendation(data):
    latest_data = data.dropna(subset=['SMA_50', 'SMA_200', 'RSI', 'MACD', 'Signal_Line']).iloc[-1]

    recommendation = "Hold"
    if latest_data['Close'] > latest_data['SMA_50'] > latest_data['SMA_200'] and latest_data['RSI'] < 70 and latest_data['MACD'] > latest_data['Signal_Line']:
        recommendation = "Buy"
    elif latest_data['Close'] < latest_data['SMA_50'] < latest_data['SMA_200'] or latest_data['RSI'] > 70 or latest_data['MACD'] < latest_data['Signal_Line']:
        recommendation = "Sell"

    return latest_data, recommendation
