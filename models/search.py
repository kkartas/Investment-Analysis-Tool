# search.py
from yfinance import Search

def search_tickers(query, max_results=10):
    """
    Returns a list of dicts for possible matches to `query`,
    using yfinance.Search for partial/fuzzy matches to symbols or company names.

    Each dict includes keys like:
        'symbol', 'shortname', 'longname', 'exch', 'type'

    If no query is provided or no results, returns [].
    """
    # Empty or blank query => no results
    if not query:
        return []

    try:
        # Perform the Yahoo Finance search
        srch = Search(query=query, max_results=max_results, news_count=0, recommended=5)
        srch.search()

        # srch.quotes is a list of possible matches
        possible_matches = srch.quotes
        results = []
        for match in possible_matches:
            results.append({
                'symbol': match.get('symbol', ''),
                'shortname': match.get('shortname', ''),
                'longname': match.get('longname', ''),
                'exch': match.get('exch', ''),
                'type': match.get('typeDisp', '')
            })
        return results
    except Exception as e:
        print("Error in search_tickers:", e)
        return []
