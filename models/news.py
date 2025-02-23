# models/news.py
from yfinance import Search
import datetime

def get_news_by_search(query, news_count=8):
    """Fetch up to `news_count` news articles for a given query using yfinance.Search."""
    try:
        srch = Search(query=query, max_results=8, news_count=news_count)
        srch.search()  # perform the search

        yf_news = srch.news
        if not yf_news:
            return []

        results = []
        for item in yf_news:
            title = item.get("title", "No Title")
            link = item.get("link", "#")
            publisher = item.get("publisher", "Unknown")
            published_ts = item.get("providerPublishTime")
            if isinstance(published_ts, int):
                published_str = datetime.datetime.fromtimestamp(published_ts).strftime("%d/%m/%Y %H:%M")
            else:
                published_str = "N/A"

            results.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "publishedDate": published_str
            })

        return results

    except Exception as e:
        print("Exception in get_news_by_search:", e)
        return []
