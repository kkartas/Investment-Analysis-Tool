def get_fundamentals(ticker):
    """
    Returns a dictionary of key fundamental data from a yfinance.Ticker object.
    """
    info = ticker.info
    fundamentals = {
        "Name": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Market Cap": info.get("marketCap", "N/A"),
        "Trailing P/E": info.get("trailingPE", "N/A"),
        "Forward P/E": info.get("forwardPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
        "Dividend Rate": info.get("dividendRate", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "Revenue": info.get("totalRevenue", "N/A"),
        "Profit Margin": info.get("profitMargins", "N/A")
    }
    return fundamentals
