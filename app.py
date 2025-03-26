# app.py

from flask import Flask, render_template, request, flash, jsonify, redirect, url_for
import yfinance as yf
from datetime import datetime, timedelta
import math
import pandas as pd

from models.stock_analysis import calculate_indicators, get_latest_recommendation
from models.dca_calculations import dca_calculation, calculate_average_annual_return
from services.data_loader import fetch_stock_data
from models.fundamentals import get_fundamentals
from models.news import get_news_by_search
from models.recommendations import get_market_recommendation
from models.search import search_tickers
from models.earnings import get_earnings

app = Flask(__name__)
app.secret_key = 'your-secret-key'


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


if __name__ == '__main__':
    app.run(debug=True)
