# models/news.py
import datetime

def get_news(ticker):
    """
    Retrieves news from the given yfinance Ticker object.
    Returns a list of up to 10 news items with keys: 'title', 'publisher', 'link', and 'publishedDate'.
    Falls back to alternate keys if the expected ones are missing.
    """
    news = ticker.news
    if not news:
        return []
    
    enhanced_news = []
    for item in news:
        # Use safe get() with fallbacks
        title = item.get("title") or item.get("summary") or "No Title"
        publisher = item.get("publisher") or item.get("source") or "Unknown"
        link = item.get("link", "#")
        published = item.get("providerPublishTime")
        # If published is a Unix timestamp, convert it to a readable date
        if isinstance(published, int):
            published = datetime.datetime.fromtimestamp(published).strftime("%Y-%m-%d %H:%M")
        elif not published:
            published = "N/A"
        enhanced_news.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "publishedDate": published
        })
    return enhanced_news[:10]
