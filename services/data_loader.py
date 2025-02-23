import yfinance as yf
from requests.exceptions import RequestException

def fetch_stock_data(symbol: str):
    """
    Fetches historical stock data for a given symbol using yfinance.
    Raises an error if no data is returned.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="max")
        if data.empty:
            raise ValueError(f"No data found for {symbol}.")
        return data
    except RequestException as e:
        raise ConnectionError(f"Network error occurred: {e}")
    except Exception as e:
        raise Exception(str(e))
