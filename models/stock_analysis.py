# models/stock_analysis.py
import pandas as pd
import numpy as np

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

def calculate_custom_indicators(data: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Calculate technical indicators with customizable parameters.
    
    Parameters:
        data (pd.DataFrame): Stock price data with OHLCV
        params (dict): Dictionary of parameters for each indicator:
            - sma_periods: List of SMA periods to calculate [int]
            - ema_periods: List of EMA periods to calculate [int]
            - rsi_period: Period for RSI calculation [int]
            - macd_params: Tuple of (fast, slow, signal) periods [tuple]
            - bb_params: Tuple of (period, std_dev) for Bollinger Bands [tuple]
            - atr_period: Period for ATR calculation [int]
            - stoch_params: Tuple of (k_period, d_period, slowing) for Stochastic Oscillator [tuple]
            - adx_period: Period for ADX calculation [int]
            - cci_period: Period for CCI calculation [int]
            - fibonacci_retracement: Whether to calculate Fibonacci retracement levels [bool]
    
    Returns:
        pd.DataFrame: DataFrame with calculated indicators
    """
    df = data.copy()
    
    # Extract parameters with defaults
    sma_periods = params.get('sma_periods', [10, 20, 50, 100, 200])
    ema_periods = params.get('ema_periods', [9, 12, 26])
    rsi_period = params.get('rsi_period', 14)
    macd_params = params.get('macd_params', (12, 26, 9))
    bb_params = params.get('bb_params', (20, 2))
    atr_period = params.get('atr_period', 14)
    stoch_params = params.get('stoch_params', (14, 3, 3))
    adx_period = params.get('adx_period', 14)
    cci_period = params.get('cci_period', 20)
    fibonacci_enabled = params.get('fibonacci_retracement', False)
    
    # Calculate SMAs
    for period in sma_periods:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
    
    # Calculate EMAs
    for period in ema_periods:
        df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
    
    # Calculate RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Calculate MACD
    fast_period, slow_period, signal_period = macd_params
    df[f'EMA_{fast_period}'] = df['Close'].ewm(span=fast_period, adjust=False).mean()
    df[f'EMA_{slow_period}'] = df['Close'].ewm(span=slow_period, adjust=False).mean()
    df['MACD'] = df[f'EMA_{fast_period}'] - df[f'EMA_{slow_period}']
    df['Signal_Line'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
    
    # Calculate Bollinger Bands
    bb_period, bb_std = bb_params
    if len(df) >= bb_period:
        df['BB_MA'] = df['Close'].rolling(window=bb_period).mean()
        df['BB_STD'] = df['Close'].rolling(window=bb_period).std()
        df['BB_Upper'] = df['BB_MA'] + (df['BB_STD'] * bb_std)
        df['BB_Lower'] = df['BB_MA'] - (df['BB_STD'] * bb_std)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_MA']
    
    # Calculate ATR
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean()
    
    # Calculate Stochastic Oscillator
    k_period, d_period, slowing = stoch_params
    df['Stoch_Lowest_Low'] = df['Low'].rolling(window=k_period).min()
    df['Stoch_Highest_High'] = df['High'].rolling(window=k_period).max()
    df['Stoch_%K'] = ((df['Close'] - df['Stoch_Lowest_Low']) / 
                     (df['Stoch_Highest_High'] - df['Stoch_Lowest_Low'])) * 100
    df['Stoch_%K'] = df['Stoch_%K'].rolling(window=slowing).mean()
    df['Stoch_%D'] = df['Stoch_%K'].rolling(window=d_period).mean()
    
    # Calculate ADX (Average Directional Index)
    if len(df) > adx_period:
        # True Range
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        
        # Plus Directional Movement (+DM)
        df['+DM'] = np.where((df['High'] - df['High'].shift(1)) > 
                             (df['Low'].shift(1) - df['Low']),
                             np.maximum(df['High'] - df['High'].shift(1), 0), 0)
        
        # Minus Directional Movement (-DM)
        df['-DM'] = np.where((df['Low'].shift(1) - df['Low']) > 
                             (df['High'] - df['High'].shift(1)),
                             np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)
        
        # Smoothed TR, +DM, -DM
        df['TR_Smooth'] = df['TR'].rolling(window=adx_period).sum()
        df['+DM_Smooth'] = df['+DM'].rolling(window=adx_period).sum()
        df['-DM_Smooth'] = df['-DM'].rolling(window=adx_period).sum()
        
        # Directional Indicators
        df['+DI'] = (df['+DM_Smooth'] / df['TR_Smooth']) * 100
        df['-DI'] = (df['-DM_Smooth'] / df['TR_Smooth']) * 100
        
        # Directional Index
        df['DX'] = (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])) * 100
        
        # Average Directional Index
        df['ADX'] = df['DX'].rolling(window=adx_period).mean()
    
    # Calculate CCI (Commodity Channel Index)
    if len(df) >= cci_period:
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TP_SMA'] = df['TP'].rolling(window=cci_period).mean()
        df['TP_Dev'] = abs(df['TP'] - df['TP_SMA'])
        df['TP_Dev_SMA'] = df['TP_Dev'].rolling(window=cci_period).mean()
        df['CCI'] = (df['TP'] - df['TP_SMA']) / (0.015 * df['TP_Dev_SMA'])
    
    # Calculate Fibonacci Retracement Levels
    if fibonacci_enabled and len(df) > 0:
        highest_price = df['High'].max()
        lowest_price = df['Low'].min()
        price_range = highest_price - lowest_price
        
        df['Fib_0.0'] = lowest_price
        df['Fib_0.236'] = lowest_price + (price_range * 0.236)
        df['Fib_0.382'] = lowest_price + (price_range * 0.382)
        df['Fib_0.5'] = lowest_price + (price_range * 0.5)
        df['Fib_0.618'] = lowest_price + (price_range * 0.618)
        df['Fib_0.786'] = lowest_price + (price_range * 0.786)
        df['Fib_1.0'] = highest_price
    
    # Optional: Clean up intermediate calculations
    columns_to_drop = ['H-L', 'H-PC', 'L-PC', 'Stoch_Lowest_Low', 'Stoch_Highest_High']
    df = df.drop(columns=columns_to_drop, errors='ignore')
    
    return df

def get_advanced_recommendation(data: pd.DataFrame) -> dict:
    """
    Generate advanced recommendations based on multiple technical indicators.
    Uses a combination of indicators to provide more nuanced analysis.
    
    Parameters:
        data (pd.DataFrame): DataFrame with calculated technical indicators
        
    Returns:
        dict: Dictionary containing recommendations and analysis
    """
    try:
        # Ensure we have enough data with indicators
        required_columns = ['Close', 'SMA_50', 'SMA_200', 'RSI', 'MACD', 'Signal_Line']
        
        for col in required_columns:
            if col not in data.columns:
                return {
                    "summary": "N/A",
                    "details": "Insufficient indicator data",
                    "confidence": 0
                }
                
        # Get latest data with indicators
        valid_data = data.dropna(subset=required_columns)
        if len(valid_data) < 2:
            return {
                "summary": "N/A",
                "details": "Insufficient historical data",
                "confidence": 0
            }
        
        latest = valid_data.iloc[-1]
        previous = valid_data.iloc[-2]
        
        # Initialize scoring system (positive = bullish, negative = bearish)
        signals = []
        score = 0
        
        # 1. Trend Analysis - Moving Averages
        if latest['Close'] > latest['SMA_50']:
            signals.append({"indicator": "Price vs SMA50", "signal": "Bullish", "details": "Price above 50-day moving average"})
            score += 1
        else:
            signals.append({"indicator": "Price vs SMA50", "signal": "Bearish", "details": "Price below 50-day moving average"})
            score -= 1
            
        if latest['Close'] > latest['SMA_200']:
            signals.append({"indicator": "Price vs SMA200", "signal": "Bullish", "details": "Price above 200-day moving average"})
            score += 1
        else:
            signals.append({"indicator": "Price vs SMA200", "signal": "Bearish", "details": "Price below 200-day moving average"})
            score -= 1
            
        if latest['SMA_50'] > latest['SMA_200']:
            signals.append({"indicator": "Golden Cross", "signal": "Bullish", "details": "50-day MA above 200-day MA"})
            score += 2
        elif latest['SMA_50'] < latest['SMA_200']:
            signals.append({"indicator": "Death Cross", "signal": "Bearish", "details": "50-day MA below 200-day MA"})
            score -= 2
            
        # 2. Momentum - RSI
        if 'RSI' in latest:
            if latest['RSI'] < 30:
                signals.append({"indicator": "RSI", "signal": "Bullish", "details": "Oversold (RSI < 30)"})
                score += 2
            elif latest['RSI'] > 70:
                signals.append({"indicator": "RSI", "signal": "Bearish", "details": "Overbought (RSI > 70)"})
                score -= 2
            elif 30 <= latest['RSI'] < 50:
                signals.append({"indicator": "RSI", "signal": "Neutral-Bullish", "details": "RSI between 30-50"})
                score += 0.5
            elif 50 < latest['RSI'] <= 70:
                signals.append({"indicator": "RSI", "signal": "Neutral-Bearish", "details": "RSI between 50-70"})
                score -= 0.5
                
        # 3. MACD Signal
        if 'MACD' in latest and 'Signal_Line' in latest:
            if latest['MACD'] > latest['Signal_Line'] and previous['MACD'] <= previous['Signal_Line']:
                signals.append({"indicator": "MACD", "signal": "Bullish", "details": "MACD crosses above signal line"})
                score += 2
            elif latest['MACD'] < latest['Signal_Line'] and previous['MACD'] >= previous['Signal_Line']:
                signals.append({"indicator": "MACD", "signal": "Bearish", "details": "MACD crosses below signal line"})
                score -= 2
            elif latest['MACD'] > latest['Signal_Line']:
                signals.append({"indicator": "MACD", "signal": "Bullish", "details": "MACD above signal line"})
                score += 1
            elif latest['MACD'] < latest['Signal_Line']:
                signals.append({"indicator": "MACD", "signal": "Bearish", "details": "MACD below signal line"})
                score -= 1
                
        # 4. Bollinger Bands
        if all(col in latest for col in ['Close', 'BB_Upper', 'BB_Lower']):
            if latest['Close'] > latest['BB_Upper']:
                signals.append({"indicator": "Bollinger Bands", "signal": "Bearish", "details": "Price above upper band (overbought)"})
                score -= 1.5
            elif latest['Close'] < latest['BB_Lower']:
                signals.append({"indicator": "Bollinger Bands", "signal": "Bullish", "details": "Price below lower band (oversold)"})
                score += 1.5
                
        # 5. Stochastic Oscillator
        if all(col in latest for col in ['Stoch_%K', 'Stoch_%D']):
            if latest['Stoch_%K'] < 20 and latest['Stoch_%D'] < 20:
                signals.append({"indicator": "Stochastic", "signal": "Bullish", "details": "Stochastic in oversold territory"})
                score += 1.5
            elif latest['Stoch_%K'] > 80 and latest['Stoch_%D'] > 80:
                signals.append({"indicator": "Stochastic", "signal": "Bearish", "details": "Stochastic in overbought territory"})
                score -= 1.5
            elif latest['Stoch_%K'] > latest['Stoch_%D'] and previous['Stoch_%K'] <= previous['Stoch_%D']:
                signals.append({"indicator": "Stochastic", "signal": "Bullish", "details": "%K crosses above %D"})
                score += 1
            elif latest['Stoch_%K'] < latest['Stoch_%D'] and previous['Stoch_%K'] >= previous['Stoch_%D']:
                signals.append({"indicator": "Stochastic", "signal": "Bearish", "details": "%K crosses below %D"})
                score -= 1
                
        # 6. ADX - Trend Strength
        if 'ADX' in latest:
            adx_value = latest['ADX']
            if adx_value > 25:
                if all(col in latest for col in ['+DI', '-DI']):
                    if latest['+DI'] > latest['-DI']:
                        signals.append({"indicator": "ADX", "signal": "Bullish", "details": f"Strong uptrend (ADX: {adx_value:.1f})"})
                        score += 1.5
                    else:
                        signals.append({"indicator": "ADX", "signal": "Bearish", "details": f"Strong downtrend (ADX: {adx_value:.1f})"})
                        score -= 1.5
                else:
                    signals.append({"indicator": "ADX", "signal": "Neutral", "details": f"Strong trend (ADX: {adx_value:.1f})"})
            else:
                signals.append({"indicator": "ADX", "signal": "Neutral", "details": f"Weak or no trend (ADX: {adx_value:.1f})"})
        
        # Calculate overall confidence score (scale of 0-100)
        max_possible_score = 10  # Approximate maximum possible score
        confidence = min(100, max(0, 50 + (score / max_possible_score) * 50))
        
        # Determine overall recommendation
        if score >= 3:
            summary = "Strong Buy"
        elif score >= 1:
            summary = "Buy"
        elif score > -1:
            summary = "Hold"
        elif score > -3:
            summary = "Sell"
        else:
            summary = "Strong Sell"
            
        # Create detailed analysis summary
        details = []
        bullish_signals = [s for s in signals if s['signal'] in ['Bullish', 'Neutral-Bullish']]
        bearish_signals = [s for s in signals if s['signal'] in ['Bearish', 'Neutral-Bearish']]
        neutral_signals = [s for s in signals if s['signal'] == 'Neutral']
        
        if bullish_signals:
            details.append(f"Bullish Signals ({len(bullish_signals)}):")
            for signal in bullish_signals:
                details.append(f"  • {signal['indicator']}: {signal['details']}")
                
        if bearish_signals:
            details.append(f"Bearish Signals ({len(bearish_signals)}):")
            for signal in bearish_signals:
                details.append(f"  • {signal['indicator']}: {signal['details']}")
                
        if neutral_signals:
            details.append(f"Neutral Signals ({len(neutral_signals)}):")
            for signal in neutral_signals:
                details.append(f"  • {signal['indicator']}: {signal['details']}")
                
        return {
            "summary": summary,
            "score": round(score, 2),
            "signals": signals,
            "details": details,
            "confidence": round(confidence, 2)
        }
            
    except Exception as e:
        print(f"Error generating advanced recommendation: {e}")
        return {
            "summary": "Error",
            "details": f"Error generating recommendation: {str(e)}",
            "confidence": 0
        }
