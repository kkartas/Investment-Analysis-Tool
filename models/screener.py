import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

def screen_stocks(filters, max_stocks=100):
    """
    Screen stocks based on provided filters
    
    Parameters:
        filters (dict): Dictionary of filters to apply
            - market_cap_min (float): Minimum market cap in billions
            - market_cap_max (float): Maximum market cap in billions
            - pe_ratio_min (float): Minimum P/E ratio
            - pe_ratio_max (float): Maximum P/E ratio
            - dividend_yield_min (float): Minimum dividend yield (%)
            - dividend_yield_max (float): Maximum dividend yield (%)
            - beta_min (float): Minimum beta
            - beta_max (float): Maximum beta
            - sector (str): Specific sector to filter by
            - industry (str): Specific industry to filter by
            - price_min (float): Minimum stock price
            - price_max (float): Maximum stock price
        max_stocks (int): Maximum number of stocks to return
    
    Returns:
        pandas.DataFrame: Filtered stock data
    """
    # For demonstration, we'll use a subset of popular stocks
    # In a real implementation, you'd use a more comprehensive list or API
    tickers_list = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "JPM", "JNJ",
        "V", "PG", "UNH", "HD", "BAC", "XOM", "AVGO", "MA", "CVX", "ABBV",
        "COST", "MRK", "PEP", "KO", "LLY", "TMO", "CSCO", "ADBE", "MCD", "ABT",
        "CRM", "CMCSA", "PFE", "NFLX", "AMD", "DHR", "INTC", "NKE", "VZ", "WMT",
        "ORCL", "QCOM", "TXN", "IBM", "PM", "LOW", "UPS", "INTU", "AMAT", "BA"
    ]
    
    # Use fewer stocks for testing
    tickers_list = tickers_list[:max_stocks]
    
    results = []
    
    def process_ticker(ticker_symbol):
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            if not info:
                return None
                
            # Extract relevant data
            data = {
                'symbol': ticker_symbol,
                'name': info.get('shortName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0) / 1e9,  # Convert to billions
                'price': info.get('currentPrice', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,  # Convert to percentage
                'beta': info.get('beta', 0),
                'eps': info.get('trailingEps', 0),
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,  # Convert to percentage
                'profit_margins': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,  # Convert to percentage
                'debt_to_equity': info.get('debtToEquity', 0),
                'roa': info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0,  # Convert to percentage
                'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,  # Convert to percentage
            }
            
            return data
        except Exception as e:
            print(f"Error processing {ticker_symbol}: {e}")
            return None
    
    # Process tickers in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_ticker, ticker): ticker for ticker in tickers_list}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Apply filters
    if df.empty:
        return df
        
    if filters.get('market_cap_min'):
        df = df[df['market_cap'] >= float(filters['market_cap_min'])]
    if filters.get('market_cap_max'):
        df = df[df['market_cap'] <= float(filters['market_cap_max'])]
    
    if filters.get('pe_ratio_min'):
        df = df[(df['pe_ratio'] >= float(filters['pe_ratio_min'])) | (df['pe_ratio'] == 0)]  # Include stocks with no PE
    if filters.get('pe_ratio_max'):
        df = df[(df['pe_ratio'] <= float(filters['pe_ratio_max'])) | (df['pe_ratio'] == 0)]  # Include stocks with no PE
    
    if filters.get('dividend_yield_min'):
        df = df[df['dividend_yield'] >= float(filters['dividend_yield_min'])]
    if filters.get('dividend_yield_max'):
        df = df[df['dividend_yield'] <= float(filters['dividend_yield_max'])]
    
    if filters.get('beta_min'):
        df = df[df['beta'] >= float(filters['beta_min'])]
    if filters.get('beta_max'):
        df = df[df['beta'] <= float(filters['beta_max'])]
    
    if filters.get('sector') and filters['sector'] != 'All':
        df = df[df['sector'] == filters['sector']]
    
    if filters.get('industry') and filters['industry'] != 'All':
        df = df[df['industry'] == filters['industry']]
    
    if filters.get('price_min'):
        df = df[df['price'] >= float(filters['price_min'])]
    if filters.get('price_max'):
        df = df[df['price'] <= float(filters['price_max'])]
    
    # Sort by market cap by default
    df = df.sort_values('market_cap', ascending=False)
    
    return df

def get_available_sectors():
    """Get a list of available sectors for filtering"""
    # In a real implementation, you'd get this from an API or database
    return [
        "Technology", "Healthcare", "Consumer Cyclical", "Financial Services",
        "Communication Services", "Industrials", "Consumer Defensive", "Energy",
        "Basic Materials", "Utilities", "Real Estate"
    ] 