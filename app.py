# app.py

from flask import Flask, render_template, request, flash, jsonify, redirect, url_for
import yfinance as yf
from datetime import datetime, timedelta
import math
import pandas as pd
import numpy as np
import json # Added import
from markupsafe import Markup # Added import
import traceback
import random

from models.stock_analysis import calculate_indicators, get_latest_recommendation, get_advanced_recommendation, calculate_custom_indicators
from models.dca_calculations import dca_calculation, calculate_average_annual_return
from services.data_loader import fetch_stock_data
from models.fundamentals import get_fundamentals
from models.news import get_news_by_search, get_news_sentiment_for_ticker
from models.recommendations import get_market_recommendation
from models.search import search_tickers
from models.earnings import get_earnings, get_earnings_surprises_with_price_reaction, get_earnings_trend
from models.screener import screen_stocks, get_available_sectors
from models.dividends import get_dividend_history, calculate_dividend_growth_metrics
from models.peer_comparison import get_peer_tickers, get_peer_comparison_data
from models.risk_assessment import assess_risk, compare_risk_metrics, calculate_financial_health_score
# from models.dca import calculate_dca_investment # <<< COMMENTED OUT

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Add utility functions to Jinja2 environment
app.jinja_env.globals.update(max=max)
app.jinja_env.globals.update(min=min)
app.jinja_env.globals.update(round=round)
app.jinja_env.globals.update(cos=math.cos)
app.jinja_env.globals.update(sin=math.sin)
app.jinja_env.globals.update(pi=math.pi)

# Helper function to handle NaN in JSON serialization
def nan_to_null(obj):
    if isinstance(obj, dict):
        return {k: nan_to_null(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [nan_to_null(i) for i in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None # Convert NaN to null for JSON/JavaScript
    return obj

# Helper function to map sectors to ETFs
def get_etf_for_sector(sector_name):
    """Maps a sector name to a common representative ETF symbol."""
    mapping = {
        # Using common SPDR ETFs, add more or adjust as needed
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financial Services': 'XLF',
        'Consumer Cyclical': 'XLY',
        'Industrials': 'XLI',
        'Communication Services': 'XLC',
        'Utilities': 'XLU',
        'Basic Materials': 'XLB',
        'Consumer Defensive': 'XLP',
        'Energy': 'XLE',
        'Real Estate': 'XLRE',
        # Add fallbacks or other sectors if necessary
    }
    return mapping.get(sector_name)

# Helper function to get ETF yield
def get_etf_yield(etf_symbol):
    """Fetches the dividend yield for a given ETF symbol."""
    if not etf_symbol:
        return 0.0
    try:
        etf = yf.Ticker(etf_symbol)
        etf_info = etf.info
        yield_val = etf_info.get('yield', 0.0) # Some ETFs use 'yield' instead of 'dividendYield'
        if yield_val is None: # Check for None specifically
             yield_val = etf_info.get('dividendYield', 0.0) # Try dividendYield as fallback
        
        # Ensure yield_val is treated as a float, convert None to 0.0
        yield_val = float(yield_val) if yield_val is not None else 0.0 
        
        return round(yield_val * 100, 2) # Return as percentage
    except Exception as e:
        print(f"Could not fetch yield for ETF {etf_symbol}: {e}")
        return 0.0


def safe_str(val):
    """Return a formatted string (2 decimals) if numeric, else 'N/A'."""
    try:
        if isinstance(val, (int, float)):
            if math.isnan(val):
                return "N/A"
            return f"{val:.2f}"
        return str(val)
    except Exception:
        return "N/A"


def safe_chart_val(val):
    """Return a rounded numeric value if numeric, else None (for Chart.js)."""
    try:
        if isinstance(val, (int, float)):
            if math.isnan(val):
                return None
            return round(val, 2)
        return None
    except Exception:
        return None


@app.route('/search_tickers', methods=['GET'])
def search_tickers_route():
    """
    AJAX endpoint for partial search of company names / tickers.
    e.g., GET /search_tickers?query=AAPL
    """
    query = request.args.get('query', '').strip()
    results = search_tickers(query, max_results=10)
    return jsonify(results)


@app.route('/period')
def period():
    """
    Handle period links for chart time periods (1d, 5d, 1m, 3m, 6m, 1y, 5y, all)
    """
    symbol = request.args.get('symbol')
    period = request.args.get('period', '1d')  # Default to 1d if not specified
    
    if not symbol:
        flash('No symbol provided', 'danger')
        return redirect('/')
        
    # Calculate start and end dates based on period
    end_date = datetime.today()
    
    if period == '1d':
        start_date = end_date - timedelta(days=1)
    elif period == '5d':
        start_date = end_date - timedelta(days=5)
    elif period == '1m':
        start_date = end_date - timedelta(days=30)
    elif period == '3m':
        start_date = end_date - timedelta(days=90)
    elif period == '6m':
        start_date = end_date - timedelta(days=180)
    elif period == 'ytd':
        start_date = datetime(end_date.year, 1, 1)  # January 1st of current year
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
    elif period == '5y':
        start_date = end_date - timedelta(days=1825)
    elif period == 'all':
        # For 'all', we'll set a very old date - yfinance will return all available data
        start_date = end_date - timedelta(days=36500)  # ~100 years
    else:
        start_date = end_date - timedelta(days=1)  # Default to 1d
    
    # Format dates as dd/mm/yyyy
    start_date_str = start_date.strftime('%d/%m/%Y')
    end_date_str = end_date.strftime('%d/%m/%Y')
    
    # Redirect to main route with parameters
    return redirect(url_for('index', 
                           symbol=symbol, 
                           start_date=start_date_str, 
                           end_date=end_date_str, 
                           period=period,
                           action='load_stock'))


@app.route('/', methods=['GET', 'POST'])
def index():
    # Variables for the template
    result = {}
    dca_result = {}
    fundamentals_data = {}
    news_data = []
    earnings_data = []  # we'll fill it with get_earnings
    error = None
    stock_chart_data = {}
    dca_chart_data = {}
    active_tab = 'stock-data'  # default
    period = request.args.get('period', '1y')  # Default to 1y

    # Default date range: 1 year (instead of 2 years)
    default_end_date_dt = datetime.today()
    default_start_date_dt = default_end_date_dt - timedelta(days=365)  # 1 year instead of 730 days
    default_end_date = default_end_date_dt.strftime('%d/%m/%Y')
    default_start_date = default_start_date_dt.strftime('%d/%m/%Y')

    # Initialize dates from request parameters or defaults
    start_date_input = request.args.get('start_date') or default_start_date
    end_date_input = request.args.get('end_date') or default_end_date

    # Handle both GET and POST for loading stock data
    if request.method == 'POST' or (request.method == 'GET' and request.args.get('symbol')):
        # For GET requests from period links
        if request.method == 'GET':
            action = request.args.get('action')
            symbol = request.args.get('symbol', '').strip()
        else:  # POST method
            action = request.form.get("action")
            symbol = request.form.get('symbol', '').strip()
            start_date_input = request.form.get('start_date') or start_date_input
            end_date_input = request.form.get('end_date') or end_date_input

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            error = "Dates must be in DD/MM/YYYY format."
            return render_template(
                'index.html',
                error=error,
                default_start_date=start_date_input,
                default_end_date=end_date_input,
                active_tab=active_tab,
                period=period
            )

        if not symbol:
            error = "Please enter a valid stock symbol."
        else:
            # Attempt to fetch historical data
            try:
                data = fetch_stock_data(symbol)
                ticker = yf.Ticker(symbol)
            except Exception as e:
                error = f"Failed to fetch data for {symbol}. Error: {str(e)}"
                data = None

            if data is not None:
                # Filter by the chosen date range
                try:
                    data = data.loc[start_date:end_date]
                except Exception as e:
                    error = f"Error filtering data by dates: {str(e)}"

                if data.empty:
                    error = "No data available for the selected date range."
                else:
                    # Calculate indicators
                    data = calculate_indicators(data)
                    latest_row, our_rec = get_latest_recommendation(data)

                    # Prepare chart data
                    stock_chart_data = {
                        'dates': data.index.strftime('%d/%m/%Y').tolist(),
                        'close': [safe_chart_val(val) for val in data['Close'].tolist()],
                        'sma50': [safe_chart_val(val) for val in data.get('SMA_50', []).tolist()],
                        'sma200': [safe_chart_val(val) for val in data.get('SMA_200', []).tolist()],
                        'macd': [safe_chart_val(val) for val in data.get('MACD', []).tolist()],
                        'rsi': [safe_chart_val(val) for val in data.get('RSI', []).tolist()]
                    }

                    if not data.empty:
                        latest_data = data.iloc[-1]
                        # Calculate price change percentage for the period
                        first_close = data.iloc[0]['Close'] if not data.empty else 0
                        last_close = data.iloc[-1]['Close'] if not data.empty else 0
                        price_change_pct = ((last_close - first_close) / first_close * 100) if first_close > 0 else 0
                        price_change_pct = round(price_change_pct, 2)
                        
                        # Market recommendation
                        market_label, market_counts = get_market_recommendation(ticker)
                        
                        # Convert market_counts to lowercase keys for consistent access in template
                        standardized_market_counts = {}
                        if market_counts:
                            for key, value in market_counts.items():
                                # Map the case-sensitive keys to lowercase
                                if key.lower() in ['strong buy', 'buy']:
                                    standardized_market_counts['buy'] = standardized_market_counts.get('buy', 0) + value
                                elif key.lower() == 'hold':
                                    standardized_market_counts['hold'] = value
                                elif key.lower() in ['sell', 'strong sell']:
                                    standardized_market_counts['sell'] = standardized_market_counts.get('sell', 0) + value
                            
                            # Ensure all required keys exist
                            for key in ['buy', 'hold', 'sell']:
                                if key not in standardized_market_counts:
                                    standardized_market_counts[key] = 0

                        result = {
                            'symbol': symbol,
                            'latest_close': safe_str(latest_data.get('Close', float('nan'))),
                            'SMA_50': safe_str(latest_data.get('SMA_50', float('nan'))),
                            'SMA_200': safe_str(latest_data.get('SMA_200', float('nan'))),
                            'RSI': safe_str(latest_data.get('RSI', float('nan'))),
                            'MACD': safe_str(latest_data.get('MACD', float('nan'))),
                            'Signal_Line': safe_str(latest_data.get('Signal_Line', float('nan'))),
                            'our_recommendation': our_rec,
                            'market_recommendation': market_label,
                            'market_recommendation_counts': standardized_market_counts,
                            'price_change_pct': price_change_pct
                        }

                    # DCA handling
                    init_inv_str = request.form.get('initial_investment')
                    period_inv_str = request.form.get('periodic_investment')
                    duration_str = request.form.get('duration')

                    init_inv = float(init_inv_str.strip()) if init_inv_str and init_inv_str.strip() else 1000.0
                    period_inv = float(period_inv_str.strip()) if period_inv_str and period_inv_str.strip() else 200.0
                    dur = int(duration_str.strip()) if duration_str and duration_str.strip() else 5

                    calc_return = calculate_average_annual_return(data)
                    total_inv, future_value, total_profit, data_points = dca_calculation(
                        data,
                        initial_investment=init_inv,
                        periodic_investment=period_inv,
                        frequency=(request.form.get('frequency') or 'monthly').lower(),
                        years=dur,
                        annual_return=calc_return
                    )
                    dca_result = {
                        'total_invested': f"{total_inv:,.0f}",
                        'future_value': f"{future_value:,.0f}",
                        'total_profit': f"{total_profit:,.0f}",
                        'expected_return': f"{calc_return * 100:.2f}"
                    }

                    # Build DCA chart data
                    try:
                        dates_pd = pd.to_datetime(data_points['dates'])
                        yearly_dates = []
                        yearly_invested = []
                        yearly_value = []
                        prev_year = None
                        for dt, inv, val in zip(dates_pd, data_points['invested'], data_points['value']):
                            if prev_year != dt.year:
                                yearly_dates.append(dt.strftime('%Y'))
                                yearly_invested.append(inv)
                                yearly_value.append(val)
                                prev_year = dt.year
                        dca_chart_data = {
                            'dates': yearly_dates,
                            'invested': yearly_invested,
                            'value': yearly_value
                        }
                    except Exception:
                        dca_chart_data = {
                            'dates': [d.strftime('%d/%m/%Y') for d in data_points['dates']],
                            'invested': data_points['invested'],
                            'value': data_points['value']
                        }

                    # Which tab after POST
                    if action == "calculate_dca":
                        active_tab = 'dca'
                    else:
                        active_tab = 'stock-data'

                    # Fundamentals
                    try:
                        fundamentals_data = get_fundamentals(ticker)
                    except Exception:
                        fundamentals_data = {}

                    # ### NEW EARNINGS CODE ###
                    # Instead of old approach, call get_earnings from models/earnings.py
                    try:
                        raw_earnings_data = get_earnings(symbol)  # returns a list of dicts
                        
                        # Standardize earnings data structure for the template
                        earnings_data = []
                        for item in raw_earnings_data:
                            # Create a standardized earnings item with default values
                            standardized_item = {
                                'quarter': item.get('period', 'N/A'),
                                'date': item.get('date', item.get('period', 'N/A')),
                                'eps_estimate': item.get('eps_estimate', 'N/A'),
                                'eps_actual': item.get('eps_actual', 'N/A'),
                                'surprise': item.get('surprise', 'N/A')
                            }
                            earnings_data.append(standardized_item)
                            
                    except Exception as e:
                        print("Error fetching new earnings:", e)
                        earnings_data = []

                    # News
                    try:
                        raw_news_data = get_news_by_search(symbol, news_count=8)
                        
                        # Standardize news data structure for the template
                        news_data = []
                        for item in raw_news_data:
                            # Create a standardized news item with default values
                            standardized_item = {
                                'title': item.get('title', 'No Title'),
                                'publisher': item.get('publisher', 'Unknown'),
                                'published_date': item.get('publishedDate', item.get('published_date', 'N/A')),
                                'link': item.get('link', '#'),
                                # Summary might not exist in all news items
                                'summary': item.get('summary', '')
                            }
                            news_data.append(standardized_item)
                            
                    except Exception as e:
                        print("News fetch exception:", e)
                        news_data = []

    return render_template(
        'index.html',
        result=result,
        dca_result=dca_result,
        fundamentals=fundamentals_data,
        earnings=earnings_data,  # pass to template
        news=news_data,
        error=error,
        default_start_date=start_date_input,
        default_end_date=end_date_input,
        stock_chart_data=stock_chart_data,
        dca_chart_data=dca_chart_data,
        active_tab=active_tab,
        period=period
    )


@app.route('/screener', methods=['GET', 'POST'])
def screener():
    """
    Stock screener page for finding stocks based on various criteria
    """
    results = []
    filters = {}
    sectors = get_available_sectors()
    
    if request.method == 'POST':
        # Get filters from form
        market_cap_min = request.form.get('market_cap_min')
        market_cap_max = request.form.get('market_cap_max')
        pe_ratio_min = request.form.get('pe_ratio_min')
        pe_ratio_max = request.form.get('pe_ratio_max')
        dividend_yield_min = request.form.get('dividend_yield_min')
        dividend_yield_max = request.form.get('dividend_yield_max')
        beta_min = request.form.get('beta_min')
        beta_max = request.form.get('beta_max')
        sector = request.form.get('sector')
        industry = request.form.get('industry')
        price_min = request.form.get('price_min')
        price_max = request.form.get('price_max')
        
        # Build filters dictionary
        filters = {
            'market_cap_min': market_cap_min,
            'market_cap_max': market_cap_max,
            'pe_ratio_min': pe_ratio_min,
            'pe_ratio_max': pe_ratio_max,
            'dividend_yield_min': dividend_yield_min,
            'dividend_yield_max': dividend_yield_max,
            'beta_min': beta_min,
            'beta_max': beta_max,
            'sector': sector,
            'industry': industry,
            'price_min': price_min,
            'price_max': price_max
        }
        
        # Remove None or empty values
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        # Call the screener function
        results_df = screen_stocks(filters)
        if not results_df.empty:
            results = results_df.to_dict(orient='records')
    
    return render_template(
        'screener.html',
        results=results,
        filters=filters,
        sectors=sectors
    )

@app.route('/news_sentiment')
def news_sentiment():
    """
    Display news sentiment analysis for a stock using models.news
    """
    symbol = request.args.get('symbol', '').strip()
    
    if not symbol:
        flash('Please provide a stock symbol', 'danger')
        return redirect('/')
        
    ticker_data = get_ticker_data(symbol)
    
    # Only fetch the number of articles needed for the sentiment overview
    recent_news_count = 15  # Recent articles for the sentiment overview
    
    # Call the function from models.news
    news_result = get_news_by_search(symbol, news_count=recent_news_count, include_sentiment=True) 
    
    # Debug the raw result from get_news_by_search
    print(f"[DEBUG] Result count from get_news_by_search for {symbol}: {len(news_result.get('articles', [])) if isinstance(news_result, dict) else 0}")
    
    # Prepare data structure for the template based on news_result format
    articles = []
    sentiment_summary = {}

    if isinstance(news_result, dict) and 'articles' in news_result and 'sentiment_summary' in news_result:
        articles = news_result.get('articles', [])
        sentiment_summary = news_result.get('sentiment_summary', {})
        
        # Process articles for display
        for article in articles:
            # Format sentiment score for display in badges (-1 to 1 scale → percentage)
            raw_score = article.get('sentiment_score', 0)
            # Convert to 0-100 scale for display
            badge_score = int((raw_score + 1) / 2 * 100)
            article['sentiment_score'] = badge_score
            
            # Map link to url if needed
            if 'url' not in article and 'link' in article:
                article['url'] = article['link']
                
            # Format source publisher if needed
            if 'source' not in article and 'publisher' in article:
                article['source'] = article['publisher']
                
            # Format date if needed (assume publishedDate is available)
            if 'date' not in article and 'publishedDate' in article:
                date_str = article.get('publishedDate', '')
                try:
                    # Try to format date nicely if it's parseable
                    dt_obj = datetime.strptime(date_str.split()[0], '%d/%m/%Y')
                    article['date'] = dt_obj.strftime('%b %d, %Y')
                except:
                    article['date'] = date_str
            
            # Ensure it has a summary
            if 'summary' not in article or not article['summary']:
                article['summary'] = "No summary available."
        
    elif isinstance(news_result, list): # Handle case where only a list of articles might be returned (no sentiment)
         articles = news_result
         print(f"[WARN] get_news_by_search returned a list, not dict. Sentiment data might be missing.")
    else:
        print(f"[WARN] Unexpected result format from get_news_by_search: {type(news_result)}")

    article_count = len(articles)
    positive_count = sentiment_summary.get('counts', {}).get('positive', 0)
    negative_count = sentiment_summary.get('counts', {}).get('negative', 0)
    neutral_count = sentiment_summary.get('counts', {}).get('neutral', 0)
    # Convert avg score (-1 to 1) to 0-100 for display
    avg_score_raw = sentiment_summary.get('average_score', 0)
    sentiment_score_scaled = int((avg_score_raw + 1) / 2 * 100)
    
    sentiment_category = sentiment_summary.get('overall_sentiment', 'neutral') # Use label directly from model

    sentiment_data = {
        'articles': articles, # Use articles fetched by get_news_by_search
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count,
        'overall_sentiment': sentiment_score_scaled, # Use the 0-100 scaled score
        'sentiment_category': sentiment_category,
        'summary': f"Based on {article_count} recent news article titles, the sentiment is generally {sentiment_category}.",
        'positive_pct': round((positive_count / article_count * 100) if article_count else 0, 1),
        'negative_pct': round((negative_count / article_count * 100) if article_count else 0, 1),
        'neutral_pct': round((neutral_count / article_count * 100) if article_count else 0, 1),
    }
    
    return render_template(
        'news_sentiment.html',
        ticker_data=ticker_data,
        sentiment_data=sentiment_data,
    )

@app.route('/dividends')
def dividends():
    """
    Display dividend information for a stock
    """
    symbol = request.args.get('symbol', '').strip()
    period = request.args.get('period', '5y')
    
    if not symbol:
        flash('Please provide a stock symbol', 'danger')
        return redirect('/')
        
    ticker_data = get_ticker_data(symbol)
    dividend_data = get_dividend_data(symbol)
    
    return render_template(
        'dividends.html',
        ticker_data=ticker_data,
        dividend_data=dividend_data,
        selected_period=period
    )

@app.route('/technical_indicators')
def technical_indicators():
    """Display detailed technical indicators for a stock"""
    # Get the stock symbol from the request
    symbol = request.args.get('symbol', 'AAPL')
    period = request.args.get('period', '1y')
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        company_name = info.get('shortName', symbol)
        
        # Get technical indicators
        indicators_data = get_technical_indicators(symbol, period)
        
        # Clean chart_data for JSON serialization
        chart_data = nan_to_null(indicators_data.get('chart_data', {}))
        
        # Debug the chart data structure
        print(f"[DEBUG] Chart data keys: {chart_data.keys()}")
        if 'adx' in chart_data:
            print(f"[DEBUG] ADX structure: {type(chart_data['adx'])}")
            if isinstance(chart_data['adx'], dict):
                for k, v in chart_data['adx'].items():
                    print(f"[DEBUG] ADX {k}: {type(v)}, length: {len(v) if isinstance(v, list) else 'not a list'}")
        
        # Try to serialize to JSON with handling for string conversion errors
        try:
            json_str = json.dumps(chart_data)
            chart_data_json = f"'{json_str}'"  # Wrap in single quotes as a JavaScript string literal
            
            # Debug the format of the first 100 chars of chart_data_json
            print(f"[DEBUG] chart_data_json (first 100 chars): {chart_data_json[:100]}")
            
        except (TypeError, ValueError) as e:
            print(f"[ERROR] Error serializing chart data: {e}")
            # Create a minimal set of empty data
            empty_data = {
                'dates': [],
                'close': [],
                'volume': [],
                'sma20': [], 'sma50': [], 'sma200': [],
                'rsi': [],
                'macd_line': [], 'macd_signal': [], 'macd_hist': [],
                'bb_upper': [], 'bb_middle': [], 'bb_lower': [],
                'stoch_k': [], 'stoch_d': [],
                'atr': [],
                'obv': [],
                'adx': {'adx': [], 'plus_di': [], 'minus_di': []},
                'cci': []
            }
            chart_data_json = f"'{json.dumps(empty_data)}'"
        
        return render_template('technical_indicators.html',
                              symbol=symbol,
                              company_name=company_name,
                              selected_period=period,
                              recommendation=indicators_data.get('recommendation', {'label': 'N/A', 'score': 50}),
                              confidence=int(indicators_data.get('score', 0)),
                              signals=[
                                  {'indicator': k, 'signal': v.get('signal', 'N/A'), 'details': v.get('value', 'N/A')}
                                  for k, v in indicators_data.get('signals', {}).items()
                              ],
                              chart_data_json=chart_data_json)
                              
    except Exception as e:
        print(f"Error in technical_indicators route: {e}")
        traceback.print_exc()
        # Return a basic template with error message
        return render_template('technical_indicators.html',
                              symbol=symbol,
                              company_name=symbol,
                              selected_period=period,
                              recommendation={'label': 'Error', 'score': 0},
                              confidence=0,
                              signals=[{'indicator': 'Error', 'signal': 'Data Error', 'details': str(e)}],
                              chart_data_json="'{}'")  # Empty JSON object as string literal

@app.route('/risk_assessment')
def risk_assessment():
    """
    Display risk assessment metrics for a stock
    """
    symbol = request.args.get('symbol', '').strip()
    benchmark = request.args.get('benchmark', '^GSPC')  # Default to S&P 500
    period = request.args.get('period', '1y')
    
    if not symbol:
        flash('Please provide a stock symbol', 'danger')
        return redirect('/')
        
    ticker_data = get_ticker_data(symbol)
    risk_data = get_risk_data(symbol)
    
    # Clean and serialize chart_data for JavaScript
    chart_data_cleaned = nan_to_null(risk_data.get('chart_data', {}))
    try:
        # Use json.dumps to create a valid JSON string
        chart_data_json = Markup(json.dumps(chart_data_cleaned))
    except Exception as e:
        print(f"Error serializing chart_data for risk assessment: {e}")
        chart_data_json = Markup(json.dumps({})) # Fallback to empty JSON

    # Add template helper functions (These might already be global, check base template or earlier setup)
    # Keeping them here for now just in case they aren't global yet.
    # Ideally, make them global once using app.jinja_env.globals.update
    import math
    def cos(x):
        return math.cos(x)
    
    def min_val(a, b):
        return a if a < b else b

    # Ensure all required attributes exist for the template (simplified example)
    # ... (Keep existing default value checks as they are important) ...
    if 'risk_color' not in risk_data: risk_data['risk_color'] = '#ffc107' # Default yellow
    if 'risk_category' not in risk_data: risk_data['risk_category'] = 'Moderate Risk'
    # ... (Add similar checks for all expected keys in risk_data based on the template)
    
    return render_template(
        'risk_assessment.html',
        ticker_data=ticker_data,
        risk_data=risk_data,
        selected_period=period,
        benchmark=benchmark,
        cos=cos, # Pass helper if not global
        min=min_val, # Pass helper if not global (renamed to avoid conflict)
        chart_data_json=chart_data_json # Pass the JSON string
    )

# Helper functions for the new routes
def get_ticker_data(symbol):
    """Get basic ticker data for a symbol using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Handle None values and missing keys
        market_cap = info.get('marketCap', 'N/A')
        if market_cap != 'N/A':
            # Format large numbers in billions/millions
            if market_cap >= 1_000_000_000:
                market_cap = f"{market_cap / 1_000_000_000:.2f}B"
            elif market_cap >= 1_000_000:
                market_cap = f"{market_cap / 1_000_000:.2f}M"
        
        # Get current price from either regularMarketPrice or previousClose
        current_price = info.get('regularMarketPrice', info.get('previousClose', 'N/A'))
        
        # Calculate dividend yield if needed
        dividend_yield = info.get('dividendYield', None)
        if dividend_yield is not None:
            dividend_yield = round(dividend_yield * 100, 2)
        else:
            dividend_yield = 0.0
            
        # Calculate 1 year return
        one_year_return = None
        try:
            hist = ticker.history(period="1y")
            if len(hist) > 0:
                first_price = hist['Close'].iloc[0]
                last_price = hist['Close'].iloc[-1]
                one_year_return = round(((last_price - first_price) / first_price) * 100, 2)
        except:
            one_year_return = 'N/A'
        
        return {
            'symbol': symbol.upper(),
            'company_name': info.get('shortName', info.get('longName', symbol)),
            'current_price': current_price,
            'market_cap': market_cap,
            'pe_ratio': info.get('trailingPE', info.get('forwardPE', 'N/A')),
            'dividend_yield': dividend_yield,
            'beta': info.get('beta', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'one_year_return': one_year_return
        }
    except Exception as e:
        print(f"Error getting ticker data for {symbol}: {e}")
        # Provide minimal fallback data
        return {
            'symbol': symbol.upper(),
            'company_name': symbol.upper(),
            'current_price': 'N/A',
            'market_cap': 'N/A',
            'pe_ratio': 'N/A',
            'dividend_yield': 'N/A',
            'beta': 'N/A',
            'sector': 'N/A',
            'industry': 'N/A',
            'one_year_return': 'N/A'
        }

def get_dividend_data(symbol):
    """Get dividend data for a symbol using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get dividend history
        dividend_history = ticker.dividends
        
        # Convert to pandas Series if it's not already
        if not isinstance(dividend_history, pd.Series):
            if len(dividend_history) == 0:
                # No dividend history
                return {
                    'current_yield': 0.0,
                    'yield_vs_sector': 0.0,
                    'annual_dividend': 0.0,
                    'payout_ratio': 0.0,
                    'ex_date': 'N/A',
                    'frequency': 'none',
                    'growth_rates': {
                        '1y': 0.0,
                        '3y': 0.0,
                        '5y': 0.0,
                        '10y': 0.0
                    },
                    'consistency_score': 0,
                    'years_of_growth': 0,
                    'is_aristocrat': False,
                    'years_since_cut': 0,
                    'history': [],
                    'chart_data': {
                        'years': [],
                        'amounts': [],
                        'yields': []
                    }
                }
            dividend_history = pd.Series(dividend_history)
        
        # Calculate current dividend yield
        dividend_yield = info.get('dividendYield', 0)
        if dividend_yield is not None:
            dividend_yield = round(dividend_yield * 100, 2)
        else:
            dividend_yield = 0.0
            
        # Calculate annual dividend
        annual_dividend = info.get('dividendRate', 0)
        if annual_dividend is None:
            annual_dividend = 0.0
            
        # Get payout ratio
        payout_ratio = info.get('payoutRatio', 0)
        if payout_ratio is not None:
            payout_ratio = round(payout_ratio * 100, 2)
        else:
            payout_ratio = 0.0
            
        # Determine dividend frequency
        if len(dividend_history) > 0:
            dividend_history = dividend_history.sort_index()
            # Get dates as list
            dates = dividend_history.index.tolist()
            # Check frequency based on number of dividends per year
            current_year = pd.Timestamp.now().year
            dividends_this_year = sum(1 for date in dates if date.year == current_year)
            dividends_last_year = sum(1 for date in dates if date.year == current_year - 1)
            
            annual_count = max(dividends_this_year, dividends_last_year)
            
            if annual_count == 0:
                frequency = "none"
            elif annual_count == 1:
                frequency = "annual"
            elif annual_count == 2:
                frequency = "semi-annual"
            elif annual_count == 4:
                frequency = "quarterly"
            elif annual_count == 12:
                frequency = "monthly"
            else:
                frequency = "irregular"
        else:
            frequency = "none"
            
        # Get latest ex-dividend date
        ex_date = "N/A"
        if len(dividend_history) > 0:
            ex_date = dividend_history.index[-1].strftime('%Y-%m-%d')
            
        # Calculate growth rates
        growth_rates = {'1y': 0.0, '3y': 0.0, '5y': 0.0, '10y': 0.0}
        
        if len(dividend_history) > 0:
            # Group dividends by year and calculate annual totals
            dividend_history_df = pd.DataFrame({'amount': dividend_history})
            dividend_history_df.index = pd.to_datetime(dividend_history_df.index)
            annual_dividends = dividend_history_df.resample('Y').sum()
            
            # Calculate year-over-year growth
            if len(annual_dividends) >= 2:
                current_year_div = annual_dividends['amount'].iloc[-1]
                prev_year_div = annual_dividends['amount'].iloc[-2]
                if prev_year_div > 0:
                    growth_rates['1y'] = round(((current_year_div / prev_year_div) - 1) * 100, 2)
            
            # 3-year growth rate (annualized)
            if len(annual_dividends) >= 4:
                current_year_div = annual_dividends['amount'].iloc[-1]
                three_years_ago_div = annual_dividends['amount'].iloc[-4]
                if three_years_ago_div > 0:
                    total_growth = (current_year_div / three_years_ago_div) - 1
                    growth_rates['3y'] = round(((1 + total_growth) ** (1/3) - 1) * 100, 2)
            
            # 5-year growth rate (annualized)
            if len(annual_dividends) >= 6:
                current_year_div = annual_dividends['amount'].iloc[-1]
                five_years_ago_div = annual_dividends['amount'].iloc[-6]
                if five_years_ago_div > 0:
                    total_growth = (current_year_div / five_years_ago_div) - 1
                    growth_rates['5y'] = round(((1 + total_growth) ** (1/5) - 1) * 100, 2)
            
            # 10-year growth rate (annualized)
            if len(annual_dividends) >= 11:
                current_year_div = annual_dividends['amount'].iloc[-1]
                ten_years_ago_div = annual_dividends['amount'].iloc[-11]
                if ten_years_ago_div > 0:
                    total_growth = (current_year_div / ten_years_ago_div) - 1
                    growth_rates['10y'] = round(((1 + total_growth) ** (1/10) - 1) * 100, 2)
        
        # Calculate consistency score and years of growth
        consistency_score = 0
        years_of_growth = 0
        
        if len(dividend_history) > 0:
            dividend_history_df = pd.DataFrame({'amount': dividend_history})
            dividend_history_df.index = pd.to_datetime(dividend_history_df.index)
            annual_dividends = dividend_history_df.resample('Y').sum()
            
            # Count consecutive years of dividend growth
            consecutive_growth_years = 0
            for i in range(len(annual_dividends) - 1, 0, -1):
                if annual_dividends['amount'].iloc[i] > annual_dividends['amount'].iloc[i-1]:
                    consecutive_growth_years += 1
                else:
                    break
                    
            years_of_growth = consecutive_growth_years
            
            # Calculate consistency score (0-100)
            # Based on: years of history, growth consistency, and frequency
            history_years = min(len(annual_dividends), 20)  # Cap at 20 years
            history_score = history_years * 2.5  # Up to 50 points
            
            # Growth consistency (up to 30 points)
            if len(annual_dividends) > 1:
                growth_count = sum(1 for i in range(1, len(annual_dividends)) 
                                 if annual_dividends['amount'].iloc[i] >= annual_dividends['amount'].iloc[i-1])
                growth_percentage = growth_count / (len(annual_dividends) - 1)
                growth_score = growth_percentage * 30
            else:
                growth_score = 0
            
            # Frequency bonus (up to 20 points)
            frequency_score = 0
            if frequency == "quarterly":
                frequency_score = 20
            elif frequency == "monthly":
                frequency_score = 20
            elif frequency == "semi-annual":
                frequency_score = 15
            elif frequency == "annual":
                frequency_score = 10
                
            consistency_score = min(round(history_score + growth_score + frequency_score), 100)
            
        # Determine if dividend aristocrat (25+ years of consecutive dividend increases)
        is_aristocrat = years_of_growth >= 25
        
        # Calculate years since dividend cut
        years_since_cut = 0
        if len(dividend_history) > 0:
            dividend_history_df = pd.DataFrame({'amount': dividend_history})
            dividend_history_df.index = pd.to_datetime(dividend_history_df.index)
            annual_dividends = dividend_history_df.resample('Y').sum()
            
            # Find the most recent year with a dividend cut
            cut_year = None
            for i in range(len(annual_dividends) - 1, 0, -1):
                if annual_dividends['amount'].iloc[i] < annual_dividends['amount'].iloc[i-1]:
                    cut_year = annual_dividends.index[i].year
                    break
                    
            if cut_year is not None:
                years_since_cut = pd.Timestamp.now().year - cut_year
            else:
                # If no cut found, use the length of the history
                years_since_cut = len(annual_dividends)
        
        # Create dividend history list
        history = []
        if len(dividend_history) > 0:
            # Get stock price history to calculate yield at time of dividend
            stock_history = ticker.history(period="max")
            
            # Create dividend history entries
            for date, amount in dividend_history.iteritems():
                # Find the stock price on the dividend date
                ex_date_str = date.strftime('%Y-%m-%d')
                
                # Get the closest stock price to the dividend date
                try:
                    close_price = stock_history.loc[stock_history.index <= date, 'Close'].iloc[-1]
                    annualized_yield = round((amount * 4 / close_price) * 100, 2) if frequency == "quarterly" else 0
                except:
                    close_price = 0
                    annualized_yield = 0
                
                # Calculate year-over-year change
                yoy_change = 0
                try:
                    # Find the same quarter's dividend from the previous year
                    prev_year_date = pd.Timestamp(date.year - 1, date.month, date.day)
                    prev_year_dividend = dividend_history.loc[(dividend_history.index.month == date.month) & 
                                                           (dividend_history.index.year == date.year - 1)]
                    if len(prev_year_dividend) > 0:
                        prev_amount = prev_year_dividend.iloc[0]
                        yoy_change = round(((amount / prev_amount) - 1) * 100, 2)
                except:
                    yoy_change = 0
                
                # Create dividend entry
                entry = {
                    'ex_date': ex_date_str,
                    'payment_date': (date + pd.Timedelta(days=15)).strftime('%Y-%m-%d'),  # Estimate payment date
                    'amount': round(amount, 3),
                    'type': 'regular',
                    'yoy_change': yoy_change,
                    'annualized_yield': annualized_yield,
                    'stock_price': round(close_price, 2) if close_price > 0 else 'N/A'
                }
                history.append(entry)
        
            # Sort by date (most recent first)
            history = sorted(history, key=lambda x: x['ex_date'], reverse=True)
        
        # Create chart data
        chart_data = {'years': [], 'amounts': [], 'yields': []}
        if len(dividend_history) > 0:
            dividend_history_df = pd.DataFrame({'amount': dividend_history})
            dividend_history_df.index = pd.to_datetime(dividend_history_df.index)
            annual_dividends = dividend_history_df.resample('Y').sum()
            
            # Get up to 10 years of data
            years_to_show = min(len(annual_dividends), 10)
            
            # Extract the years, amounts, and calculate yields
            for i in range(years_to_show):
                idx = len(annual_dividends) - years_to_show + i
                if idx >= 0:
                    year = annual_dividends.index[idx].year
                    amount = round(annual_dividends['amount'].iloc[idx], 2)
                    
                    # Calculate approximate yield for that year
                    try:
                        avg_price = stock_history[stock_history.index.year == year]['Close'].mean()
                        year_yield = round((amount / avg_price) * 100, 2) if avg_price > 0 else 0
                    except:
                        year_yield = 0
                    
                    chart_data['years'].append(str(year))
                    chart_data['amounts'].append(amount)
                    chart_data['yields'].append(year_yield)
        
        # Get sector average dividend yield for comparison
        sector = info.get('sector', '')
        yield_vs_sector = 0
        sector_yield = 0 # Initialize sector_yield
        
        if sector and dividend_yield > 0:
            etf_symbol = get_etf_for_sector(sector)
            if etf_symbol:
                sector_yield = get_etf_yield(etf_symbol)
                if sector_yield is not None: # Ensure we got a valid number
                    yield_vs_sector = round(dividend_yield - sector_yield, 2)
                else:
                    sector_yield = 0 # Set to 0 if ETF fetch failed
            else:
                print(f"No ETF mapping found for sector: {sector}")
        
        return {
            'current_yield': dividend_yield,
            'yield_vs_sector': yield_vs_sector,
            'sector_yield': sector_yield, # Pass the sector yield to the template if needed
            'annual_dividend': annual_dividend,
            'payout_ratio': payout_ratio,
            'ex_date': ex_date,
            'frequency': frequency,
            'growth_rates': growth_rates,
            'consistency_score': consistency_score,
            'years_of_growth': years_of_growth,
            'is_aristocrat': is_aristocrat,
            'years_since_cut': years_since_cut,
            'history': history,
            'chart_data': chart_data
        }
        
    except Exception as e:
        print(f"Error getting dividend data for {symbol}: {e}")
        # Return empty data structure
        return {
            'current_yield': 0.0,
            'yield_vs_sector': 0.0,
            'sector_yield': 0.0, # Add default here too
            'annual_dividend': 0.0,
            'payout_ratio': 0.0,
            'ex_date': 'N/A',
            'frequency': 'none',
            'growth_rates': {
                '1y': 0.0,
                '3y': 0.0,
                '5y': 0.0,
                '10y': 0.0
            },
            'consistency_score': 0,
            'years_of_growth': 0,
            'is_aristocrat': False,
            'years_since_cut': 0,
            'history': [],
            'chart_data': {
                'years': [],
                'amounts': [],
                'yields': []
            }
        }

def get_risk_data(symbol):
    """Get risk assessment data for a symbol using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get price history (2 years)
        hist = ticker.history(period="2y")
        
        if hist.empty:
            return {
                'risk_score': 50,
                'risk_category': 'Moderate Risk',
                'risk_color': '#ffc107',
                'risk_summary': 'Insufficient data to assess risk',
                'volatility': 0,
                'beta': 1.0,
                'max_drawdown': 0,
                'value_at_risk': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'treynor_ratio': 0,
                'alpha': 0,
                'information_ratio': 0,
                'r_squared': 0,
                'financial_health_score': 50,
                'financial_health_category': 'Average',
                'financial_health_color': '#ffc107',
                'financial_health_summary': 'Insufficient data to assess financial health',
                'financial_components': {
                    'profitability': 50,
                    'solvency': 50,
                    'liquidity': 50,
                    'efficiency': 50
                },
                'altman_z_score': 1.8,
                'benchmark': 'SPY',
                'benchmark_volatility': 0,
                'chart_data': {
                    'volatility': {
                        'dates': [],
                        '30': [],
                        '60': [],
                        '90': []
                    },
                    'benchmark_volatility': {
                        '30': [],
                        '60': [],
                        '90': []
                    },
                    'drawdown': {
                        'dates': [],
                        'stock': [],
                        'benchmark': []
                    },
                    'radar': {
                        'labels': ['Volatility', 'Beta', 'Drawdown', 'Financial Health', 'Bankruptcy Risk'],
                        'stock_values': [50, 50, 50, 50, 50],
                        'industry_values': [50, 50, 50, 50, 50]
                    }
                }
            }
        
        # Get benchmark data (S&P 500 / SPY)
        benchmark = yf.Ticker('SPY')
        benchmark_hist = benchmark.history(period="2y")
        
        # Calculate returns
        hist['daily_return'] = hist['Close'].pct_change().fillna(0)
        benchmark_hist['daily_return'] = benchmark_hist['Close'].pct_change().fillna(0)
        
        # Calculate volatility (annualized)
        volatility = hist['daily_return'].std() * (252 ** 0.5) * 100  # convert to percentage
        benchmark_volatility = benchmark_hist['daily_return'].std() * (252 ** 0.5) * 100
        
        # Calculate beta
        # Align dates
        common_dates = hist.index.intersection(benchmark_hist.index)
        if len(common_dates) > 0:
            stock_returns = hist.loc[common_dates, 'daily_return']
            benchmark_returns = benchmark_hist.loc[common_dates, 'daily_return']
            
            # Calculate beta
            covariance = stock_returns.cov(benchmark_returns)
            variance = benchmark_returns.var()
            beta = covariance / variance if variance > 0 else 1.0
            
            # Calculate correlation
            correlation = stock_returns.corr(benchmark_returns)
            
            # Calculate R-squared
            r_squared = correlation ** 2
        else:
            beta = 1.0
            correlation = 0.0
            r_squared = 0.0
        
        # Calculate maximum drawdown
        cumulative_returns = (1 + hist['daily_return']).cumprod()
        max_values = cumulative_returns.cummax()
        drawdown = (cumulative_returns / max_values - 1) * 100
        max_drawdown = drawdown.min()
        
        # Calculate Value at Risk (95% confidence)
        # Fix for empty array issue
        if len(hist['daily_return']) > 0:
            var_95 = np.percentile(hist['daily_return'], 5) * 100
        else:
            var_95 = 0
        
        # Calculate risk-adjusted return metrics
        # Assuming risk-free rate of 2%
        risk_free_rate = 0.02 / 252  # daily risk-free rate
        
        # Calculate Sharpe Ratio
        excess_return = hist['daily_return'] - risk_free_rate
        sharpe_ratio = excess_return.mean() / hist['daily_return'].std() * (252 ** 0.5) if hist['daily_return'].std() > 0 else 0
        
        # Calculate Sortino Ratio (downside deviation)
        downside_returns = hist['daily_return'][hist['daily_return'] < 0]
        # Fix: Check array length instead of using array in boolean context
        downside_deviation = downside_returns.std() * (252 ** 0.5) if len(downside_returns) > 0 else hist['daily_return'].std() * (252 ** 0.5)
        sortino_ratio = excess_return.mean() / downside_deviation * (252 ** 0.5) if downside_deviation > 0 else 0
        
        # Calculate Treynor Ratio
        treynor_ratio = excess_return.mean() / beta * (252 ** 0.5) if beta > 0 else 0
        
        # Calculate Jensen's Alpha
        if len(common_dates) > 0:
            benchmark_excess_return = benchmark_hist.loc[common_dates, 'daily_return'] - risk_free_rate
            expected_return = risk_free_rate + beta * benchmark_excess_return.mean()
            alpha = (hist.loc[common_dates, 'daily_return'].mean() - expected_return) * 252 * 100  # annualized and in percentage
        else:
            alpha = 0.0
            
        # Calculate Information Ratio
        if len(common_dates) > 0:
            active_return = hist.loc[common_dates, 'daily_return'] - benchmark_hist.loc[common_dates, 'daily_return']
            # Fix: Check standard deviation before division
            information_ratio = active_return.mean() / active_return.std() * (252 ** 0.5) if active_return.std() > 0 else 0
        else:
            information_ratio = 0.0
            
        # Calculate rolling volatility
        rolling_vol_30 = hist['daily_return'].rolling(window=30).std() * (252 ** 0.5) * 100
        rolling_vol_60 = hist['daily_return'].rolling(window=60).std() * (252 ** 0.5) * 100
        rolling_vol_90 = hist['daily_return'].rolling(window=90).std() * (252 ** 0.5) * 100
        
        # Calculate benchmark rolling volatility
        bench_rolling_vol_30 = benchmark_hist['daily_return'].rolling(window=30).std() * (252 ** 0.5) * 100
        bench_rolling_vol_60 = benchmark_hist['daily_return'].rolling(window=60).std() * (252 ** 0.5) * 100
        bench_rolling_vol_90 = benchmark_hist['daily_return'].rolling(window=90).std() * (252 ** 0.5) * 100
        
        # Benchmark drawdown
        bench_cumulative_returns = (1 + benchmark_hist['daily_return']).cumprod()
        bench_max_values = bench_cumulative_returns.cummax()
        bench_drawdown = (bench_cumulative_returns / bench_max_values - 1) * 100
        
        # Create date and value arrays for charts
        # Fix: Check array length before slicing
        if len(hist.index) >= 90:
            vol_dates = hist.index[-90:].strftime('%Y-%m-%d').tolist()
            vol_values_30 = rolling_vol_30.iloc[-90:].round(2).tolist()
            vol_values_60 = rolling_vol_60.iloc[-90:].round(2).tolist()
            vol_values_90 = rolling_vol_90.iloc[-90:].round(2).tolist()
            
            bench_vol_values_30 = bench_rolling_vol_30.iloc[-90:].round(2).tolist() if len(bench_rolling_vol_30) >= 90 else []
            bench_vol_values_60 = bench_rolling_vol_60.iloc[-90:].round(2).tolist() if len(bench_rolling_vol_60) >= 90 else []
            bench_vol_values_90 = bench_rolling_vol_90.iloc[-90:].round(2).tolist() if len(bench_rolling_vol_90) >= 90 else []
            
            drawdown_dates = hist.index[-90:].strftime('%Y-%m-%d').tolist()
            drawdown_values = drawdown.iloc[-90:].round(2).tolist()
            bench_drawdown_values = bench_drawdown.iloc[-90:].round(2).tolist() if len(bench_drawdown) >= 90 else []
        else:
            vol_dates = hist.index.strftime('%Y-%m-%d').tolist()
            vol_values_30 = rolling_vol_30.round(2).tolist()
            vol_values_60 = rolling_vol_60.round(2).tolist()
            vol_values_90 = rolling_vol_90.round(2).tolist()
            
            bench_vol_values_30 = bench_rolling_vol_30.round(2).tolist()
            bench_vol_values_60 = bench_rolling_vol_60.round(2).tolist()
            bench_vol_values_90 = bench_rolling_vol_90.round(2).tolist()
            
            drawdown_dates = hist.index.strftime('%Y-%m-%d').tolist()
            drawdown_values = drawdown.round(2).tolist()
            bench_drawdown_values = bench_drawdown.round(2).tolist()
        
        # Get financial ratios
        info = ticker.info
        financials = ticker.financials
        
        # Try to get balance sheet data
        balance_sheet = ticker.balance_sheet
        
        # Initialize financial health metrics
        profitability = 50
        solvency = 50
        liquidity = 50
        efficiency = 50
        
        # Altman Z-Score (simplified)
        altman_z = 1.8
        
        # Financial ratios over time
        financial_dates = []
        current_ratio = []
        debt_to_equity = []
        interest_coverage = []
        
        # Try to calculate financial health metrics if we have financial data
        if financials is not None and not financials.empty:
            try:
                # Profitability
                profit_margin = info.get('profitMargins', 0)
                return_on_assets = info.get('returnOnAssets', 0)
                return_on_equity = info.get('returnOnEquity', 0)
                
                if profit_margin is not None and return_on_equity is not None and return_on_assets is not None:
                    profitability = ((profit_margin + return_on_equity + return_on_assets) / 3) * 100
                    profitability = min(max(profitability, 0), 100)  # Ensure between 0-100
            except Exception:
                pass
                
            # Try to calculate solvency metrics if we have balance sheet data
            if balance_sheet is not None and not balance_sheet.empty:
                try:
                    # Get the most recent balance sheet data
                    total_assets = balance_sheet.loc['Total Assets'].iloc[0]
                    total_liabilities = balance_sheet.loc['Total Liabilities'].iloc[0]
                    
                    # Calculate debt ratio
                    debt_ratio = total_liabilities / total_assets if total_assets > 0 else 1
                    
                    # Calculate solvency score (0-100, lower debt ratio is better)
                    solvency = (1 - debt_ratio) * 100
                    solvency = min(max(solvency, 0), 100)  # Ensure between 0-100
                    
                    # Calculate liquidity from current ratio
                    current_assets = balance_sheet.loc['Current Assets'].iloc[0] if 'Current Assets' in balance_sheet.index else 0
                    current_liabilities = balance_sheet.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in balance_sheet.index else 0
                    
                    if current_liabilities > 0:
                        current_ratio_value = current_assets / current_liabilities
                        # Convert current ratio to a 0-100 score (1.5 is considered good)
                        liquidity = min(current_ratio_value / 2 * 100, 100)
                    
                    # Calculate efficiency from asset turnover
                    revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else 0
                    asset_turnover = revenue / total_assets if total_assets > 0 else 0
                    
                    # Convert asset turnover to a 0-100 score (0.5 is average)
                    efficiency = min(asset_turnover * 100, 100)
                    
                    # Calculate Altman Z-Score (simplified version)
                    # Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
                    # X1 = Working Capital / Total Assets
                    # X2 = Retained Earnings / Total Assets
                    # X3 = EBIT / Total Assets
                    # X4 = Market Value of Equity / Total Liabilities
                    # X5 = Sales / Total Assets
                    
                    working_capital = current_assets - current_liabilities
                    x1 = working_capital / total_assets if total_assets > 0 else 0
                    
                    retained_earnings = balance_sheet.loc['Retained Earnings'].iloc[0] if 'Retained Earnings' in balance_sheet.index else 0
                    x2 = retained_earnings / total_assets if total_assets > 0 else 0
                    
                    ebit = financials.loc['EBIT'].iloc[0] if 'EBIT' in financials.index else financials.loc['Operating Income'].iloc[0] if 'Operating Income' in financials.index else 0
                    x3 = ebit / total_assets if total_assets > 0 else 0
                    
                    market_cap = info.get('marketCap', 0)
                    x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
                    
                    sales = revenue
                    x5 = sales / total_assets if total_assets > 0 else 0
                    
                    altman_z = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
                    
                    # Get financial ratios over time
                    for i in range(min(len(balance_sheet.columns), 4)):  # Up to 4 quarters/years
                        try:
                            date = balance_sheet.columns[i].strftime('%Y-%m-%d')
                            
                            # Current ratio
                            curr_assets = balance_sheet.loc['Current Assets'].iloc[i] if 'Current Assets' in balance_sheet.index else 0
                            curr_liabilities = balance_sheet.loc['Current Liabilities'].iloc[i] if 'Current Liabilities' in balance_sheet.index else 0
                            curr_ratio = curr_assets / curr_liabilities if curr_liabilities > 0 else 0
                            
                            # Debt to equity
                            total_debt = balance_sheet.loc['Total Debt'].iloc[i] if 'Total Debt' in balance_sheet.index else 0
                            total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[i] if 'Total Stockholder Equity' in balance_sheet.index else 0
                            d2e = total_debt / total_equity if total_equity > 0 else 0
                            
                            # Interest coverage
                            int_expense = financials.loc['Interest Expense'].iloc[i] if 'Interest Expense' in financials.index else 0
                            ebit_val = financials.loc['EBIT'].iloc[i] if 'EBIT' in financials.index else financials.loc['Operating Income'].iloc[i] if 'Operating Income' in financials.index else 0
                            int_cov = ebit_val / abs(int_expense) if int_expense != 0 else 0
                            
                            financial_dates.append(date)
                            current_ratio.append(round(curr_ratio, 2))
                            debt_to_equity.append(round(d2e, 2))
                            interest_coverage.append(round(int_cov, 2))
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Error calculating financial metrics: {e}")
                    pass
        
        # Calculate overall financial health score
        financial_health_score = (profitability + solvency + liquidity + efficiency) / 4
        
        # Determine financial health assessment and color
        if financial_health_score >= 80:
            financial_health_assessment = "Excellent"
            financial_health_color = "#198754"  # Green
        elif financial_health_score >= 60:
            financial_health_assessment = "Good"
            financial_health_color = "#20c997"  # Teal
        elif financial_health_score >= 40:
            financial_health_assessment = "Average"
            financial_health_color = "#ffc107"  # Yellow
        elif financial_health_score >= 20:
            financial_health_assessment = "Poor"
            financial_health_color = "#fd7e14"  # Orange
        else:
            financial_health_assessment = "Very Poor"
            financial_health_color = "#dc3545"  # Red
        
        # Calculate overall risk score (0-100, higher is riskier)
        # Factors: volatility, beta, max drawdown, financial health
        volatility_score = min(volatility * 5, 100)  # 20% volatility would give a score of 100
        beta_score = min(abs(beta - 1) * 50 + 50, 100)  # Beta of 1 gives 50, higher or lower increases risk
        drawdown_score = min(abs(max_drawdown) * 5, 100)  # 20% drawdown would give a score of 100
        
        risk_score = (volatility_score * 0.35 + beta_score * 0.25 + drawdown_score * 0.25 + (100 - financial_health_score) * 0.15)
        
        # Determine risk assessment and color
        if risk_score >= 80:
            risk_assessment = "High Risk"
            risk_color = "#dc3545"  # Red
        elif risk_score >= 60:
            risk_assessment = "Above Average Risk"
            risk_color = "#fd7e14"  # Orange
        elif risk_score >= 40:
            risk_assessment = "Moderate Risk"
            risk_color = "#ffc107"  # Yellow
        elif risk_score >= 20:
            risk_assessment = "Low Risk"
            risk_color = "#0dcaf0"  # Blue
        else:
            risk_assessment = "Very Low Risk"
            risk_color = "#198754"  # Green
            
        # Create risk summary
        risk_summary = f"{symbol} has a {risk_assessment.lower()} profile with {round(volatility, 1)}% volatility and beta of {round(beta, 2)}."
        financial_health_summary = f"The company shows {financial_health_assessment.lower()} financial health with Altman Z-Score of {round(altman_z, 2)}."
            
        # Create risk factors data
        risk_factors = [
            "Volatility", "Beta", "Drawdown", "Financial Health", "Bankruptcy Risk"
        ]
        
        risk_values = [
            round(volatility_score, 1),
            round(beta_score, 1),
            round(drawdown_score, 1),
            round(100 - financial_health_score, 1),
            round(max(0, min(100, 100 - altman_z * 10)), 1) if altman_z != 0 else 50
        ]
        
        # Industry average values (placeholder)
        industry_values = [50, 50, 50, 50, 50]
        
        # Compile financial ratio data for the template
        financial_ratios = {
            'roe': return_on_equity * 100 if return_on_equity is not None else 0,
            'roa': return_on_assets * 100 if return_on_assets is not None else 0,
            'profit_margin': profit_margin * 100 if profit_margin is not None else 0,
            'debt_to_equity': ticker.info.get('debtToEquity', 0) / 100 if ticker.info.get('debtToEquity') is not None else 0,
            'interest_coverage': 0,  # Will be filled later if available
            'debt_ratio': debt_ratio if 'debt_ratio' in locals() else 0,
            'current_ratio': current_ratio_value if 'current_ratio_value' in locals() else 0,
            'quick_ratio': ticker.info.get('quickRatio', 0) if ticker.info.get('quickRatio') is not None else 0,
            'cash_ratio': 0,  # Will be filled later if available
            'asset_turnover': asset_turnover if 'asset_turnover' in locals() else 0,
            'inventory_turnover': 0,  # Will be filled later if available
            'receivables_turnover': 0  # Will be filled later if available
        }
        
        # Compile all the data
        return {
            'risk_score': round(risk_score, 1),
            'risk_category': risk_assessment,
            'risk_color': risk_color,
            'risk_summary': risk_summary,
            'volatility': round(volatility, 2),
            'beta': round(beta, 2),
            'max_drawdown': round(max_drawdown, 2),
            'value_at_risk': round(var_95, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'treynor_ratio': round(treynor_ratio, 2),
            'alpha': round(alpha, 2),
            'information_ratio': round(information_ratio, 2),
            'r_squared': round(r_squared, 2),
            'financial_health_score': round(financial_health_score, 1),
            'financial_health_category': financial_health_assessment,
            'financial_health_color': financial_health_color,
            'financial_health_summary': financial_health_summary,
            'financial_components': {
                'profitability': round(profitability, 1),
                'solvency': round(solvency, 1),
                'liquidity': round(liquidity, 1),
                'efficiency': round(efficiency, 1)
            },
            'altman_z_score': round(altman_z, 2),
            'benchmark': 'SPY',
            'benchmark_volatility': round(benchmark_volatility, 2),
            'financial_ratios': financial_ratios,
            'chart_data': {
                'volatility': {
                    'dates': vol_dates,
                    '30': vol_values_30,
                    '60': vol_values_60,
                    '90': vol_values_90
                },
                'benchmark_volatility': {
                    '30': bench_vol_values_30,
                    '60': bench_vol_values_60,
                    '90': bench_vol_values_90
                },
                'drawdown': {
                    'dates': drawdown_dates,
                    'stock': drawdown_values,
                    'benchmark': bench_drawdown_values
                },
                'radar': {
                    'labels': risk_factors,
                    'stock_values': risk_values,
                    'industry_values': industry_values
                }
            }
        }
    
    except Exception as e:
        print(f"Error getting risk data for {symbol}: {str(e)}")
        traceback.print_exc()
        # Return default risk data
        return {
            'risk_score': 50,
            'risk_category': 'Moderate Risk',
            'risk_color': '#ffc107',
            'risk_summary': 'Insufficient data to assess risk',
            'volatility': 0,
            'beta': 1.0,
            'max_drawdown': 0,
            'value_at_risk': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'treynor_ratio': 0,
            'alpha': 0,
            'information_ratio': 0,
            'r_squared': 0,
            'financial_health_score': 50,
            'financial_health_category': 'Average',
            'financial_health_color': '#ffc107',
            'financial_health_summary': 'Insufficient data to assess financial health',
            'financial_components': {
                'profitability': 50,
                'solvency': 50,
                'liquidity': 50,
                'efficiency': 50
            },
            'altman_z_score': 1.8,
            'benchmark': 'SPY',
            'benchmark_volatility': 0,
            'financial_ratios': {
                'roe': 0,
                'roa': 0,
                'profit_margin': 0,
                'debt_to_equity': 0,
                'interest_coverage': 0,
                'debt_ratio': 0,
                'current_ratio': 0,
                'quick_ratio': 0,
                'cash_ratio': 0,
                'asset_turnover': 0,
                'inventory_turnover': 0,
                'receivables_turnover': 0
            },
            'chart_data': {
                'volatility': {
                    'dates': [],
                    '30': [],
                    '60': [],
                    '90': []
                },
                'benchmark_volatility': {
                    '30': [],
                    '60': [],
                    '90': []
                },
                'drawdown': {
                    'dates': [],
                    'stock': [],
                    'benchmark': []
                },
                'radar': {
                    'labels': ['Volatility', 'Beta', 'Drawdown', 'Financial Health', 'Bankruptcy Risk'],
                    'stock_values': [50, 50, 50, 50, 50],
                    'industry_values': [50, 50, 50, 50, 50]
                }
            }
        }

# --- End Calculation Functions ---

# --- Technical Indicator Calculation Functions ---

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index (RSI)"""
    delta = data.diff()
    gain = delta.mask(delta < 0, 0)
    loss = -delta.mask(delta > 0, 0)
    
    # Use .ewm for smoother RSI commonly used in platforms
    avg_gain = gain.ewm(com=window-1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window-1, min_periods=window).mean()
    
    rs = avg_gain / avg_loss
    # Handle cases where loss is zero (e.g., all gains)
    rsi = np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))
    
    return pd.Series(rsi, index=data.index)

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate Moving Average Convergence Divergence (MACD)"""
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger(data, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=window).mean()
    std = data.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, sma, lower_band # Return middle band (sma) too

def calculate_stochastic(data_df, k_window=14, d_window=3):
    """Calculate Stochastic Oscillator (%K and %D)"""
    low_min = data_df['Low'].rolling(window=k_window).min()
    high_max = data_df['High'].rolling(window=k_window).max()
    # %K = (Current Close - Lowest Low)/(Highest High - Lowest Low) * 100
    k_denominator = (high_max - low_min)
    # Replace 0 denominator with NaN to avoid division by zero, then fill resulting NaN with 50 (neutral)
    k = 100 * ((data_df['Close'] - low_min) / k_denominator.replace(0, np.nan)).fillna(0.5)
    # %D = 3-day SMA of %K
    d = k.rolling(window=d_window).mean()
    return k, d

def calculate_atr(data_df, window=14):
    """Calculate Average True Range (ATR)"""
    high_low = data_df['High'] - data_df['Low']
    high_close = (data_df['High'] - data_df['Close'].shift()).abs()
    low_close = (data_df['Low'] - data_df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    # Use Exponential Moving Average for ATR as is common
    atr = tr.ewm(span=window, adjust=False).mean()
    return atr

def calculate_obv(data_df):
    """Calculate On-Balance Volume (OBV)"""
    obv = (np.sign(data_df['Close'].diff()) * data_df['Volume']).fillna(0).cumsum()
    return obv

def calculate_adx(data_df, window=14):
    """Calculate Average Directional Index (ADX)"""
    df = data_df.copy()
    
    # Calculate True Range
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate +DM and -DM
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].shift().diff(-1)
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0)
    minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0)
    
    # Calculate smoothed values using EWM
    smoothed_tr = tr.ewm(span=window, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(span=window, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(span=window, adjust=False).mean()
    
    # Calculate +DI and -DI
    plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
    minus_di = 100 * (smoothed_minus_dm / smoothed_tr)
    
    # Calculate DX
    dx_nom = (plus_di - minus_di).abs()
    dx_denom = (plus_di + minus_di)
    dx = 100 * (dx_nom / dx_denom)
    
    # Calculate ADX
    adx = dx.ewm(span=window, adjust=False).mean()
    
    return adx, plus_di, minus_di

def calculate_cci(data_df, window=20):
    """Calculate Commodity Channel Index (CCI)"""
    # Create typical price
    tp = (data_df['High'] + data_df['Low'] + data_df['Close']) / 3
    
    # Calculate SMA of typical price
    sma_tp = tp.rolling(window=window).mean()
    
    # Calculate Mean Deviation
    md = tp.rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())
    
    # Calculate CCI
    cci = (tp - sma_tp) / (0.015 * md)
    
    return cci

# --- End Technical Indicator Calculation Functions ---

def get_technical_indicators(symbol, period="1y"):
    """Get technical indicators for a given stock symbol."""
    try:
        # Get historical data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # Calculate various technical indicators
        # RSI (14-day)
        hist['RSI'] = calculate_rsi(hist['Close'])
        
        # MACD
        macd_line, signal_line, histogram = calculate_macd(hist['Close'])
        hist['MACD'] = macd_line
        hist['MACD_Signal'] = signal_line
        hist['MACD_Hist'] = histogram
        
        # Simple Moving Averages
        hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        hist['SMA_200'] = hist['Close'].rolling(window=200).mean()
        
        # Bollinger Bands (20-day, 2 standard deviations)
        upper_band, middle_band, lower_band = calculate_bollinger(hist['Close'])
        hist['BB_Upper'] = upper_band
        hist['BB_Middle'] = middle_band
        hist['BB_Lower'] = lower_band
        
        # Average True Range (14-day)
        hist['ATR'] = calculate_atr(hist)
        
        # Stochastic Oscillator (14-day)
        k, d = calculate_stochastic(hist)
        hist['Stoch_K'] = k
        hist['Stoch_D'] = d
        
        # On-Balance Volume
        hist['OBV'] = calculate_obv(hist)
        
        # ADX (14-day)
        adx, plus_di, minus_di = calculate_adx(hist)
        hist['ADX'] = adx
        hist['Plus_DI'] = plus_di
        hist['Minus_DI'] = minus_di
        
        # CCI (20-day)
        hist['CCI'] = calculate_cci(hist)
        
        # Determine signals
        signals = {}
        latest_close = hist['Close'].iloc[-1]
        
        # RSI Signal
        latest_rsi = hist['RSI'].iloc[-1]
        if latest_rsi < 30:
            signals['RSI'] = {'signal': 'Oversold (Buy)', 'value': f"{latest_rsi:.2f}"}
        elif latest_rsi > 70:
            signals['RSI'] = {'signal': 'Overbought (Sell)', 'value': f"{latest_rsi:.2f}"}
        else:
            signals['RSI'] = {'signal': 'Neutral', 'value': f"{latest_rsi:.2f}"}
        
        # MACD Signal
        latest_macd = hist['MACD'].iloc[-1]
        latest_signal = hist['MACD_Signal'].iloc[-1]
        
        if latest_macd > latest_signal:
            signals['MACD'] = {'signal': 'Bullish', 'value': f"{latest_macd:.2f}"}
        else:
            signals['MACD'] = {'signal': 'Bearish', 'value': f"{latest_macd:.2f}"}
        
        # Moving Average Signal
        sma_20 = hist['SMA_20'].iloc[-1]
        sma_50 = hist['SMA_50'].iloc[-1]
        sma_200 = hist['SMA_200'].iloc[-1]
        
        ma_signals = []
        ma_values = []
        
        if latest_close > sma_20:
            ma_signals.append("Price > SMA(20)")
            ma_values.append(f"SMA(20): {sma_20:.2f}")
        else:
            ma_signals.append("Price < SMA(20)")
            ma_values.append(f"SMA(20): {sma_20:.2f}")
            
        if latest_close > sma_50:
            ma_signals.append("Price > SMA(50)")
            ma_values.append(f"SMA(50): {sma_50:.2f}")
        else:
            ma_signals.append("Price < SMA(50)")
            ma_values.append(f"SMA(50): {sma_50:.2f}")
            
        if latest_close > sma_200:
            ma_signals.append("Price > SMA(200)")
            ma_values.append(f"SMA(200): {sma_200:.2f}")
        else:
            ma_signals.append("Price < SMA(200)")
            ma_values.append(f"SMA(200): {sma_200:.2f}")
        
        if sma_20 > sma_50 and sma_50 > sma_200:
            ma_trend = "Strong Uptrend"
        elif sma_20 < sma_50 and sma_50 < sma_200:
            ma_trend = "Strong Downtrend"
        elif sma_20 > sma_50:
            ma_trend = "Short-term Uptrend"
        else:
            ma_trend = "Short-term Downtrend"
            
        signals['MA'] = {'signal': ma_trend, 'value': ", ".join(ma_values)}
        
        # Bollinger Bands Signal
        latest_upper = hist['BB_Upper'].iloc[-1]
        latest_lower = hist['BB_Lower'].iloc[-1]
        
        if latest_close > latest_upper:
            signals['BB'] = {'signal': 'Above Upper Band (Sell)', 'value': f"Upper: {latest_upper:.2f}"}
        elif latest_close < latest_lower:
            signals['BB'] = {'signal': 'Below Lower Band (Buy)', 'value': f"Lower: {latest_lower:.2f}"}
        else:
            signals['BB'] = {'signal': 'Within Bands', 'value': f"Upper: {latest_upper:.2f}, Lower: {latest_lower:.2f}"}
        
        # ATR doesn't give direct signals but indicates volatility
        latest_atr = hist['ATR'].iloc[-1]
        atr_percent = (latest_atr / latest_close) * 100
        
        if atr_percent > 3:
            signals['ATR'] = {'signal': 'High Volatility', 'value': f"{latest_atr:.2f} ({atr_percent:.2f}%)"}
        elif atr_percent < 1:
            signals['ATR'] = {'signal': 'Low Volatility', 'value': f"{latest_atr:.2f} ({atr_percent:.2f}%)"}
        else:
            signals['ATR'] = {'signal': 'Moderate Volatility', 'value': f"{latest_atr:.2f} ({atr_percent:.2f}%)"}
        
        # Stochastic Signal
        latest_k = hist['Stoch_K'].iloc[-1]
        latest_d = hist['Stoch_D'].iloc[-1]
        
        if latest_k < 20 and latest_d < 20:
            signals['Stochastic'] = {'signal': 'Oversold (Buy)', 'value': f"K: {latest_k:.2f}, D: {latest_d:.2f}"}
        elif latest_k > 80 and latest_d > 80:
            signals['Stochastic'] = {'signal': 'Overbought (Sell)', 'value': f"K: {latest_k:.2f}, D: {latest_d:.2f}"}
        elif latest_k > latest_d:
            signals['Stochastic'] = {'signal': 'Bullish Crossover', 'value': f"K: {latest_k:.2f}, D: {latest_d:.2f}"}
        elif latest_k < latest_d:
            signals['Stochastic'] = {'signal': 'Bearish Crossover', 'value': f"K: {latest_k:.2f}, D: {latest_d:.2f}"}
        else:
            signals['Stochastic'] = {'signal': 'Neutral', 'value': f"K: {latest_k:.2f}, D: {latest_d:.2f}"}
        
        # OBV Signal (look at trend over last 20 days)
        obv_trend = np.polyfit(range(20), hist['OBV'].iloc[-20:].values, 1)[0]
        if obv_trend > 0:
            signals['OBV'] = {'signal': 'Rising (Bullish)', 'value': f"{hist['OBV'].iloc[-1]:.0f}"}
        else:
            signals['OBV'] = {'signal': 'Falling (Bearish)', 'value': f"{hist['OBV'].iloc[-1]:.0f}"}
        
        # ADX Signal
        latest_adx = hist['ADX'].iloc[-1]
        latest_plus_di = hist['Plus_DI'].iloc[-1]
        latest_minus_di = hist['Minus_DI'].iloc[-1]
        
        # Print debug info
        print(f"[DEBUG] ADX value type: {type(latest_adx)}, value: {latest_adx}")
        print(f"[DEBUG] +DI value type: {type(latest_plus_di)}, value: {latest_plus_di}")
        print(f"[DEBUG] -DI value type: {type(latest_minus_di)}, value: {latest_minus_di}")
        
        # Ensure values are numeric
        try:
            latest_adx_val = float(latest_adx)
            latest_plus_di_val = float(latest_plus_di)
            latest_minus_di_val = float(latest_minus_di)
            
            if latest_adx_val > 25:
                if latest_plus_di_val > latest_minus_di_val:
                    signals['ADX'] = {'signal': 'Strong Uptrend', 'value': f"ADX: {latest_adx_val:.2f}, +DI: {latest_plus_di_val:.2f}, -DI: {latest_minus_di_val:.2f}"}
                else:
                    signals['ADX'] = {'signal': 'Strong Downtrend', 'value': f"ADX: {latest_adx_val:.2f}, +DI: {latest_plus_di_val:.2f}, -DI: {latest_minus_di_val:.2f}"}
            else:
                signals['ADX'] = {'signal': 'No Trend', 'value': f"ADX: {latest_adx_val:.2f}, +DI: {latest_plus_di_val:.2f}, -DI: {latest_minus_di_val:.2f}"}
        except (ValueError, TypeError) as e:
            print(f"[ERROR] Error formatting ADX values: {e}")
            signals['ADX'] = {'signal': 'No Data', 'value': 'N/A'}
        
        # CCI Signal
        latest_cci = hist['CCI'].iloc[-1]
        print(f"[DEBUG] CCI value type: {type(latest_cci)}, value: {latest_cci}")
        
        # Ensure CCI value is numeric
        try:
            latest_cci_val = float(latest_cci)
            
            if latest_cci_val > 100:
                signals['CCI'] = {'signal': 'Overbought (Sell)', 'value': f"{latest_cci_val:.2f}"}
            elif latest_cci_val < -100:
                signals['CCI'] = {'signal': 'Oversold (Buy)', 'value': f"{latest_cci_val:.2f}"}
            else:
                signals['CCI'] = {'signal': 'Neutral', 'value': f"{latest_cci_val:.2f}"}
        except (ValueError, TypeError) as e:
            print(f"[ERROR] Error formatting CCI value: {e}")
            signals['CCI'] = {'signal': 'No Data', 'value': 'N/A'}
        
        # Determine overall recommendation
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI
        if 'Oversold' in signals['RSI']['signal']:
            bullish_signals += 1
        elif 'Overbought' in signals['RSI']['signal']:
            bearish_signals += 1
        
        # MACD
        if 'Bullish' in signals['MACD']['signal']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # MA
        if 'Uptrend' in signals['MA']['signal']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # BB
        if 'Buy' in signals['BB']['signal']:
            bullish_signals += 1
        elif 'Sell' in signals['BB']['signal']:
            bearish_signals += 1
        
        # Stochastic
        if 'Buy' in signals['Stochastic']['signal'] or 'Bullish' in signals['Stochastic']['signal']:
            bullish_signals += 1
        elif 'Sell' in signals['Stochastic']['signal'] or 'Bearish' in signals['Stochastic']['signal']:
            bearish_signals += 1
        
        # OBV
        if 'Bullish' in signals['OBV']['signal']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # ADX
        if 'Uptrend' in signals['ADX']['signal']:
            bullish_signals += 1
        elif 'Downtrend' in signals['ADX']['signal']:
            bearish_signals += 1
            
        # CCI
        if 'Buy' in signals['CCI']['signal']:
            bullish_signals += 1
        elif 'Sell' in signals['CCI']['signal']:
            bearish_signals += 1
        
        # Determine recommendation
        total_signals = 8  # Total number of indicators considered for recommendations
        
        if bullish_signals > bearish_signals:
            score = bullish_signals / total_signals * 100
            if score >= 75:
                recommendation = {'label': 'Strong Buy', 'score': score}
            else:
                recommendation = {'label': 'Buy', 'score': score}
        elif bearish_signals > bullish_signals:
            score = bearish_signals / total_signals * 100
            if score >= 75:
                recommendation = {'label': 'Strong Sell', 'score': score}
            else:
                recommendation = {'label': 'Sell', 'score': score}
        else:
            recommendation = {'label': 'Neutral', 'score': 50}
        
        # Format chart data for the last 180 days
        chart_data = {
            'dates': hist.index[-180:].strftime('%Y-%m-%d').tolist(),
            'close': nan_to_null(hist['Close'][-180:].tolist()),
            'volume': nan_to_null(hist['Volume'][-180:].tolist()),
            'rsi': nan_to_null(hist['RSI'][-180:].tolist()),
            'macd_line': nan_to_null(hist['MACD'][-180:].tolist()),
            'macd_signal': nan_to_null(hist['MACD_Signal'][-180:].tolist()),
            'macd_hist': nan_to_null(hist['MACD_Hist'][-180:].tolist()),
            'sma20': nan_to_null(hist['SMA_20'][-180:].tolist()),
            'sma50': nan_to_null(hist['SMA_50'][-180:].tolist()),
            'sma200': nan_to_null(hist['SMA_200'][-180:].tolist()),
            'bb_upper': nan_to_null(hist['BB_Upper'][-180:].tolist()),
            'bb_middle': nan_to_null(hist['BB_Middle'][-180:].tolist()),
            'bb_lower': nan_to_null(hist['BB_Lower'][-180:].tolist()),
            'stoch_k': nan_to_null(hist['Stoch_K'][-180:].tolist()),
            'stoch_d': nan_to_null(hist['Stoch_D'][-180:].tolist()),
            'atr': nan_to_null(hist['ATR'][-180:].tolist()),
            'obv': nan_to_null(hist['OBV'][-180:].tolist()),
            'adx': {
                'adx': nan_to_null(hist['ADX'][-180:].tolist()),
                'plus_di': nan_to_null(hist['Plus_DI'][-180:].tolist()),
                'minus_di': nan_to_null(hist['Minus_DI'][-180:].tolist())
            },
            'cci': nan_to_null(hist['CCI'][-180:].tolist())
        }
        
        return {
            'recommendation': recommendation,
            'score': recommendation['score'],
            'signals': signals,
            'chart_data': chart_data
        }
    
    except Exception as e:
        print(f"Error calculating technical indicators: {e}")
        return {
            'recommendation': {'label': 'Data Error', 'score': 0},
            'score': 0,
            'signals': {
                'RSI': {'signal': 'No Data', 'value': 'N/A'},
                'MACD': {'signal': 'No Data', 'value': 'N/A'},
                'MA': {'signal': 'No Data', 'value': 'N/A'},
                'BB': {'signal': 'No Data', 'value': 'N/A'},
                'ATR': {'signal': 'No Data', 'value': 'N/A'},
                'Stochastic': {'signal': 'No Data', 'value': 'N/A'},
                'OBV': {'signal': 'No Data', 'value': 'N/A'},
                'ADX': {'signal': 'No Data', 'value': 'N/A'},
                'CCI': {'signal': 'No Data', 'value': 'N/A'}
            },
            'chart_data': {
                'dates': [],
                'close': [],
                'volume': [],
                'rsi': [],
                'macd_line': [], 'macd_signal': [], 'macd_hist': [],
                'sma20': [], 'sma50': [], 'sma200': [],
                'bb_upper': [], 'bb_middle': [], 'bb_lower': [],
                'stoch_k': [], 'stoch_d': [],
                'atr': [],
                'obv': [],
                'adx': {'adx': [], 'plus_di': [], 'minus_di': []},
                'cci': []
            }
        }

if __name__ == '__main__':
    app.run(debug=True)
