# models/earnings.py
import requests

def fetch_earnings(symbol: str, api_key: str):
    """
    Fetch upcoming earnings for the given symbol using Financial Modeling Prep API.
    Returns a list of earnings events.
    """
    url = f"https://financialmodelingprep.com/api/v3/earning_calendar?symbol={symbol}&apikey={api_key}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print("Earnings API error:", response.status_code)
            return []
        data = response.json()
        return data if data else []
    except Exception as e:
        print("Exception in fetch_earnings:", e)
        return []
