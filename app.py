# app.py

from flask import Flask, render_template, request, flash, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import math
import pandas as pd

# Your existing imports for the rest of the app
from models.stock_analysis import calculate_indicators, get_latest_recommendation
from models.dca_calculations import dca_calculation, calculate_average_annual_return
from services.data_loader import fetch_stock_data
from models.fundamentals import get_fundamentals
from models.earnings import fetch_earnings
from models.options import get_options_chain
from models.news import get_news_by_search  # or your original get_news
from models.recommendations import get_market_recommendation
from models.search import search_tickers

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
    e.g. GET /search_tickers?query=appl
    Returns JSON array of matches:
      [
        {symbol: "AAPL", shortname: "Apple Inc.", longname: "...", exch: "NMS", type: "Equity"},
        ...
      ]
    """
    query = request.args.get('query', '').strip()
    results = search_tickers(query, max_results=10)
    return jsonify(results)


@app.route('/', methods=['GET', 'POST'])
def index():
    result = {}
    dca_result = {}
    fundamentals_data = {}
    earnings_data = []
    options_chain = None
    news_data = []
    error = None
    stock_chart_data = {}
    dca_chart_data = {}
    active_tab = 'stock-data'  # default tab

    # Default date range
    default_end_date_dt = datetime.today()
    default_start_date_dt = default_end_date_dt - timedelta(days=730)
    default_end_date = default_end_date_dt.strftime('%d/%m/%Y')
    default_start_date = default_start_date_dt.strftime('%d/%m/%Y')

    start_date_input = default_start_date
    end_date_input = default_end_date

    if request.method == 'POST':
        action = request.form.get("action")  # "load_stock" or "calculate_dca"
        symbol = request.form.get('symbol', '').strip()
        start_date_input = request.form.get('start_date') or default_start_date
        end_date_input = request.form.get('end_date') or default_end_date

        try:
            start_date = datetime.strptime(start_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            error = "Dates must be in DD/MM/YYYY format."
            return render_template('index.html',
                                   error=error,
                                   default_start_date=start_date_input,
                                   default_end_date=end_date_input,
                                   active_tab=active_tab)

        if not symbol:
            error = "Please enter a valid stock symbol."
        else:
            try:
                data = fetch_stock_data(symbol)
                ticker = yf.Ticker(symbol)
            except Exception as e:
                error = f"Failed to fetch data for {symbol}. Error: {str(e)}"
                data = None

            if data is not None:
                try:
                    data = data.loc[start_date:end_date]
                except Exception as e:
                    error = f"Error filtering data by dates: {str(e)}"

                if data.empty:
                    error = "No data available for the selected date range."
                else:
                    data = calculate_indicators(data)
                    latest_row, our_rec = get_latest_recommendation(data)
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
                        # Market recommendation
                        market_label, market_counts = get_market_recommendation(ticker)

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
                            'market_recommendation_counts': market_counts
                        }

                    # Handle DCA
                    init_inv_str = request.form.get('initial_investment')
                    period_inv_str = request.form.get('periodic_investment')
                    duration_str = request.form.get('duration')

                    init_inv = float(init_inv_str.strip()) if init_inv_str and init_inv_str.strip() else 1000.0
                    period_inv = float(period_inv_str.strip()) if period_inv_str and period_inv_str.strip() else 200.0
                    dur = int(duration_str.strip()) if duration_str and duration_str.strip() else 5

                    calc_return = calculate_average_annual_return(data)
                    total_inv, future_value, total_profit, data_points = dca_calculation(
                        data, init_inv, period_inv,
                        (request.form.get('frequency') or 'monthly').lower(),
                        dur, calc_return
                    )
                    dca_result = {
                        'total_invested': f"{total_inv:,.0f}",
                        'future_value': f"{future_value:,.0f}",
                        'total_profit': f"{total_profit:,.0f}",
                        'expected_return': f"{calc_return * 100:.2f}"
                    }

                    # Build DCA chart
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

                    # Which tab
                    if action == "calculate_dca":
                        active_tab = 'dca'
                    else:
                        active_tab = 'stock-data'

                    # Fundamentals
                    try:
                        fundamentals_data = get_fundamentals(ticker)
                    except Exception:
                        fundamentals_data = {}
                    
                    # Earnings
                    try:
                        earnings_data = fetch_earnings(symbol, api_key='your_api_key_here')
                    except Exception as e:
                        print("Earnings fetch exception:", e)
                        earnings_data = []
                    
                    # Options
                    try:
                        calls, puts = get_options_chain(ticker)
                        options_chain = {'calls': calls, 'puts': puts} if (calls or puts) else None
                    except Exception as e:
                        print("Options chain exception:", e)
                        options_chain = None

                    # News
                    try:
                        news_data = get_news_by_search(symbol, news_count=8)
                    except Exception as e:
                        print("News fetch exception:", e)
                        news_data = []

    return render_template('index.html',
                           result=result,
                           dca_result=dca_result,
                           fundamentals=fundamentals_data,
                           earnings=earnings_data,
                           options_chain=options_chain,
                           news=news_data,
                           error=error,
                           default_start_date=start_date_input,
                           default_end_date=end_date_input,
                           stock_chart_data=stock_chart_data,
                           dca_chart_data=dca_chart_data,
                           active_tab=active_tab)


if __name__ == '__main__':
    app.run(debug=True)
