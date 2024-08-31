import yfinance as yf
import requests_cache
from requests.exceptions import RequestException

# Configure a session for caching to avoid making repeated requests to the Yahoo Finance API
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'investment-tool/1.0'

def fetch_yfinance_data(stock_symbol):
    """
    Fetches historical stock data for the given symbol from Yahoo Finance.

    Args:
        stock_symbol (str): The stock symbol for which to fetch data.

    Returns:
        tuple: (data, error_message)
            - data: pandas.DataFrame if successful, or None if an error occurred.
            - error_message: str containing the error message if an error occurred, otherwise None.
    """
    try:
        ticker = yf.Ticker(stock_symbol, session=session)
        data = ticker.history(period="max")  # Fetches the maximum available historical data
        if data.empty:
            return None, f"No data found for {stock_symbol}. The stock may be delisted or unavailable."
        return data, None
    except RequestException as e:
        return None, f"Network error occurred: {e}"
    except Exception as e:
        return None, str(e)
