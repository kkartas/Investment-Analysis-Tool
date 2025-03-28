# models/peer_comparison.py

import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_peer_tickers(ticker_symbol):
    """
    Get a list of peer companies for comparison based on industry and sector
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
    
    Returns:
        list: List of peer company ticker symbols
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        if not info:
            return []
            
        # Get sector and industry information
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        
        if not sector or not industry:
            return []
            
        # For demonstration, we'll use a hardcoded list of peer companies
        # In a real implementation, you might use an API to get this data
        
        # Map some common industries to peer groups
        # This is a simplified example - would need to be expanded in production
        peer_groups = {
            "Technology": {
                "Software—Application": ["MSFT", "ORCL", "ADBE", "CRM", "INTU", "NOW"],
                "Software—Infrastructure": ["MSFT", "ORCL", "ADBE", "CRM", "VMW", "CTXS"],
                "Semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "TSM", "TXN", "QCOM"],
                "Consumer Electronics": ["AAPL", "HPQ", "DELL", "LNVGY", "SONY"],
                "Internet Content & Information": ["GOOGL", "META", "BIDU", "TWTR", "SNAP"]
            },
            "Communication Services": {
                "Internet Content & Information": ["GOOGL", "META", "BIDU", "TWTR", "SNAP"],
                "Entertainment": ["NFLX", "CMCSA", "DIS", "VIAC", "WBD"]
            },
            "Consumer Cyclical": {
                "Auto Manufacturers": ["TSLA", "GM", "F", "TM", "NSANY"],
                "Internet Retail": ["AMZN", "BABA", "JD", "EBAY", "ETSY"]
            },
            "Financial Services": {
                "Banks—Diversified": ["JPM", "BAC", "WFC", "C", "GS", "MS"],
                "Financial Data & Stock Exchanges": ["ICE", "SPGI", "MCO", "MSCI", "NDAQ"]
            },
            "Healthcare": {
                "Drug Manufacturers—General": ["JNJ", "PFE", "MRK", "ABBV", "BMY", "LLY"],
                "Biotechnology": ["AMGN", "GILD", "BIIB", "REGN", "VRTX"]
            },
            "Energy": {
                "Oil & Gas E&P": ["XOM", "CVX", "COP", "EOG", "PXD"],
                "Oil & Gas Integrated": ["XOM", "CVX", "BP", "SHEL", "TTE"]
            }
        }
        
        # Try to get peers from the hardcoded map
        if sector in peer_groups and industry in peer_groups[sector]:
            peers = peer_groups[sector][industry]
            # Remove the current ticker from the list if present
            if ticker_symbol.upper() in peers:
                peers.remove(ticker_symbol.upper())
            return peers[:5]  # Return up to 5 peers
            
        # If sector/industry not found, perform a minimal screen based on sector
        # This would be replaced with a proper screener in production
        peers = []
        for potential_peer in ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "JPM", "JNJ",
                             "V", "PG", "UNH", "HD", "BAC", "XOM", "AVGO", "MA", "CVX", "ABBV"]:
            if potential_peer.upper() != ticker_symbol.upper():
                try:
                    peer_ticker = yf.Ticker(potential_peer)
                    peer_info = peer_ticker.info
                    if peer_info.get('sector') == sector:
                        peers.append(potential_peer)
                        if len(peers) >= 5:  # Limit to 5 peers
                            break
                except Exception:
                    continue
                    
        return peers
        
    except Exception as e:
        print(f"Error getting peer tickers for {ticker_symbol}: {e}")
        return []

def get_peer_comparison_data(ticker_symbol, peer_tickers=None):
    """
    Get comparison data for a stock and its peers
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
        peer_tickers (list, optional): List of peer company ticker symbols
    
    Returns:
        dict: Dictionary containing comparison data
    """
    try:
        # If no peer tickers provided, get them
        if peer_tickers is None:
            peer_tickers = get_peer_tickers(ticker_symbol)
            
        if not peer_tickers:
            return {
                "success": False,
                "message": "No peer companies found for comparison"
            }
            
        # Add the main ticker to the list for processing
        all_tickers = [ticker_symbol] + peer_tickers
        
        # Process each ticker to get data
        results = []
        
        def process_ticker(symbol):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    return None
                    
                # Get key metrics
                market_cap = info.get('marketCap', 0) / 1e9  # Convert to billions
                pe_ratio = info.get('trailingPE', 0)
                forward_pe = info.get('forwardPE', 0)
                peg_ratio = info.get('pegRatio', 0)
                price_to_sales = info.get('priceToSalesTrailing12Months', 0)
                price_to_book = info.get('priceToBook', 0)
                ev_to_ebitda = info.get('enterpriseToEbitda', 0)
                ev_to_revenue = info.get('enterpriseToRevenue', 0)
                profit_margins = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
                operating_margins = info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0
                roa = info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0
                roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
                revenue_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
                earnings_growth = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0
                dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
                beta = info.get('beta', 0)
                
                # Get name
                name = info.get('shortName', symbol)
                
                # Create result dictionary
                result = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': market_cap,
                    'pe_ratio': pe_ratio,
                    'forward_pe': forward_pe,
                    'peg_ratio': peg_ratio,
                    'price_to_sales': price_to_sales,
                    'price_to_book': price_to_book,
                    'ev_to_ebitda': ev_to_ebitda,
                    'ev_to_revenue': ev_to_revenue,
                    'profit_margins': profit_margins,
                    'operating_margins': operating_margins,
                    'roa': roa,
                    'roe': roe,
                    'revenue_growth': revenue_growth,
                    'earnings_growth': earnings_growth,
                    'dividend_yield': dividend_yield,
                    'beta': beta
                }
                
                return result
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                return None
                
        # Use ThreadPoolExecutor to process tickers in parallel
        with ThreadPoolExecutor(max_workers=len(all_tickers)) as executor:
            futures = {executor.submit(process_ticker, ticker): ticker for ticker in all_tickers}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        if not results:
            return {
                "success": False,
                "message": "Failed to retrieve comparison data"
            }
            
        # Sort results to ensure main ticker is first
        results.sort(key=lambda x: 0 if x['symbol'].upper() == ticker_symbol.upper() else 1)
        
        # Calculate performance comparison data (past 1 year return)
        performance_data = get_performance_comparison(ticker_symbol, peer_tickers)
        
        # Calculate percentile ranking for the main ticker among peers
        percentile_rankings = {}
        metrics_to_rank = [
            'market_cap', 'pe_ratio', 'forward_pe', 'peg_ratio', 'price_to_sales', 
            'price_to_book', 'ev_to_ebitda', 'ev_to_revenue', 'profit_margins',
            'operating_margins', 'roa', 'roe', 'revenue_growth', 'earnings_growth',
            'dividend_yield', 'beta'
        ]
        
        # For each metric, calculate the ranking
        for metric in metrics_to_rank:
            values = [r[metric] for r in results if r[metric] > 0]  # Exclude zeros
            if not values:
                percentile_rankings[metric] = {'percentile': 0, 'rank': 0, 'total': 0}
                continue
                
            main_value = results[0][metric]
            
            # Skip if main value is 0
            if main_value == 0:
                percentile_rankings[metric] = {'percentile': 0, 'rank': 0, 'total': len(values)}
                continue
                
            # Calculate percentile - higher is better for positive metrics
            better_metrics = ['profit_margins', 'operating_margins', 'roa', 'roe', 
                             'revenue_growth', 'earnings_growth', 'dividend_yield']
            
            # For most metrics, lower is better (PE ratio, etc.)
            better_count = sum(1 for v in values if (
                (metric in better_metrics and v <= main_value) or
                (metric not in better_metrics and v >= main_value)
            ))
            
            percentile = better_count / len(values) * 100
            
            # Determine rank
            if metric in better_metrics:
                sorted_values = sorted(values, reverse=True)  # Higher is better
            else:
                sorted_values = sorted(values)  # Lower is better
                
            rank = sorted_values.index(main_value) + 1 if main_value in sorted_values else 0
            
            percentile_rankings[metric] = {
                'percentile': round(percentile, 1),
                'rank': rank,
                'total': len(values)
            }
        
        return {
            "success": True,
            "main_ticker": ticker_symbol,
            "comparison_data": results,
            "performance_data": performance_data,
            "percentile_rankings": percentile_rankings
        }
        
    except Exception as e:
        print(f"Error in peer comparison for {ticker_symbol}: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def get_performance_comparison(ticker_symbol, peer_tickers, periods=None):
    """
    Get performance comparison data for multiple time periods
    
    Parameters:
        ticker_symbol (str): Main stock ticker symbol
        peer_tickers (list): List of peer company ticker symbols
        periods (list, optional): List of periods to compare ['1m', '3m', '6m', '1y', '5y']
        
    Returns:
        dict: Dictionary containing performance data
    """
    if periods is None:
        periods = ['1m', '3m', '6m', '1y', '5y']
        
    all_tickers = [ticker_symbol] + peer_tickers
    
    # Initialize results
    results = {period: {} for period in periods}
    
    for period in periods:
        # Map periods to lookback parameters
        period_param = {
            '1m': '1mo',
            '3m': '3mo',
            '6m': '6mo',
            '1y': '1y',
            '5y': '5y'
        }.get(period, '1y')
        
        # Get data for all tickers at once
        data = yf.download(all_tickers, period=period_param, group_by='ticker', auto_adjust=True)
        
        for ticker in all_tickers:
            try:
                if ticker in data.columns:
                    # Single ticker data structure is different
                    if len(all_tickers) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[ticker]
                        
                    # Calculate return
                    first_close = ticker_data['Close'].iloc[0]
                    last_close = ticker_data['Close'].iloc[-1]
                    
                    if first_close > 0:
                        return_pct = ((last_close - first_close) / first_close) * 100
                    else:
                        return_pct = 0
                        
                    results[period][ticker] = round(return_pct, 2)
                    
            except Exception as e:
                print(f"Error calculating return for {ticker} over {period}: {e}")
                results[period][ticker] = 0
    
    # Format results for charting
    formatted_results = {
        'periods': periods,
        'tickers': all_tickers,
        'data': []
    }
    
    for ticker in all_tickers:
        ticker_results = []
        for period in periods:
            ticker_results.append(results[period].get(ticker, 0))
            
        formatted_results['data'].append({
            'ticker': ticker,
            'returns': ticker_results
        })
    
    return formatted_results 