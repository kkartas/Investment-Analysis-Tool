import yfinance as yf
import requests_cache
from requests.exceptions import RequestException

# Install a cache that expires after 1 hour (3600 seconds)
requests_cache.install_cache('yfinance_cache', expire_after=3600)
session = requests_cache.CachedSession('yfinance_cache')
session.headers['User-Agent'] = 'investment-tool/1.0'

def fetch_stock_data(symbol: str):
    """
    Fetches historical stock data for a given symbol.
    Raises an error if no data is returned.
    """
    try:
        ticker = yf.Ticker(symbol, session=session)
        data = ticker.history(period="max")
        if data.empty:
            raise ValueError(f"No data found for {symbol}.")
        return data
    except RequestException as e:
        raise ConnectionError(f"Network error occurred: {e}")
    except Exception as e:
        raise Exception(str(e))
