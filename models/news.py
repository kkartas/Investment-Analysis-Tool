# models/news.py
import datetime

def get_news(ticker):
    """
    Retrieves up to 10 news items from the yfinance Ticker object.
    """
    news = ticker.news
    if not news:
        return []
    
    enhanced_news = []
    for item in news:
        title = item.get("title") or "No Title"
        publisher = item.get("publisher") or item.get("source") or "Unknown"
        link = item.get("link") or "#"
        published = item.get("providerPublishTime")
        if isinstance(published, int):
            published = datetime.datetime.fromtimestamp(published).strftime("%d/%m/%Y %H:%M")
        elif not published:
            published = "N/A"
        enhanced_news.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "publishedDate": published
        })
    return enhanced_news[:10]
