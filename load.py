import yfinance as yf
import pandas as pd
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
from PyQt5.QtWidgets import QMessageBox

# Create a custom session with caching and rate limiting
class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

# Configure the session
session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND * 5)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
)

def fetch_yfinance_data(symbol):
    """
    Fetch historical stock data from Yahoo Finance using the yfinance library,
    with caching and rate limiting.

    Args:
        symbol (str): The stock ticker symbol.

    Returns:
        pd.DataFrame: DataFrame containing historical stock data.
    """
    try:
        ticker = yf.Ticker(symbol, session=session)
        data = ticker.history(period="max")
        if data.empty:
            QMessageBox.critical(None, "Data Error", f"No data found for symbol: {symbol}")
            return None
        data.reset_index(inplace=True)
        data['Date'] = pd.to_datetime(data['Date'])
        data.set_index('Date', inplace=True)
        return data
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to fetch data: {e}")
        return None

def load_file():
    file_dialog = QFileDialog()
    file_path, _ = file_dialog.getOpenFileName(None, "Select Data File", "", "CSV Files (*.csv)")
    if file_path:
        try:
            data = pd.read_csv(file_path)
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
            return data
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load file: {e}")
            return None
    else:
        return None
