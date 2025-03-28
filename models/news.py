# models/news.py
from yfinance import Search
import datetime
import re
import statistics
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup

def get_news_by_search(query, news_count=8, include_sentiment=False):
    """
    Fetch up to `news_count` news articles for a given query using yfinance.Search.
    If include_sentiment is True, analyze the sentiment of each article.
    """
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
                
            news_item = {
                "title": title,
                "publisher": publisher,
                "link": link,
                "publishedDate": published_str
            }
            
            if include_sentiment:
                sentiment_score, sentiment_label = analyze_sentiment(title)
                news_item["sentiment_score"] = sentiment_score
                news_item["sentiment"] = sentiment_label

            results.append(news_item)

        # If sentiment is included, also add overall sentiment stats
        if include_sentiment and results:
            sentiment_scores = [item["sentiment_score"] for item in results]
            avg_sentiment = statistics.mean(sentiment_scores)
            overall_sentiment = get_sentiment_label(avg_sentiment)
            
            # Count sentiment types
            sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
            for item in results:
                sentiment_counts[item["sentiment"]] += 1
                
            sentiment_summary = {
                "average_score": round(avg_sentiment, 2),
                "overall_sentiment": overall_sentiment,
                "counts": sentiment_counts
            }
            
            return {"articles": results, "sentiment_summary": sentiment_summary}

        return results

    except Exception as e:
        print("Exception in get_news_by_search:", e)
        return []

def analyze_sentiment(text):
    """
    Analyze the sentiment of a piece of text.
    Returns a tuple of (sentiment_score, sentiment_label)
    """
    try:
        analysis = TextBlob(text)
        # Polarity score: -1 to 1 (negative to positive)
        score = analysis.sentiment.polarity
        label = get_sentiment_label(score)
        return score, label
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return 0, "neutral"

def get_sentiment_label(score):
    """Convert a sentiment score to a label"""
    if score > 0.1:
        return "positive"
    elif score < -0.1:
        return "negative"
    else:
        return "neutral"

def get_news_sentiment_for_ticker(ticker_symbol, news_count=15):
    """
    Get news sentiment specifically for a stock ticker.
    Returns news articles with sentiment analysis.
    """
    return get_news_by_search(ticker_symbol, news_count, include_sentiment=True)
