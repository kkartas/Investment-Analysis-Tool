import yfinance as yf
import requests_cache

# Configure a session for caching and rate limiting
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'investment-tool/1.0'

def fetch_yfinance_data(stock_symbol):
    ticker = yf.Ticker(stock_symbol, session=session)
    data = ticker.history(period="max")  # Fetches the maximum available historical data
    return data
