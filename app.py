# app.py

from flask import Flask, render_template, request, flash
import yfinance as yf
from datetime import datetime, timedelta
import math
import pandas as pd

# Import custom modules from your project
from models.stock_analysis import calculate_indicators, compute_sharpe_ratio
from models.dca_calculations import dca_calculation, calculate_average_annual_return
from services.data_loader import fetch_stock_data
from models.fundamentals import get_fundamentals
from models.earnings import fetch_earnings
from models.options import get_options_chain

# Import the new function that uses yfinance.Search
from models.news import get_news_by_search

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Needed for flash messages


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


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route for the Investment Analysis Tool.
    GET: Renders the default index page with empty or default data.
    POST: Handles user input for stock symbol, date range, DCA calculations, etc.
    """
    # Initialize variables and defaults
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

    # Set default dates: end_date is today, start_date is 2 years ago
    default_end_date_dt = datetime.today()
    default_start_date_dt = default_end_date_dt - timedelta(days=730)
    default_end_date = default_end_date_dt.strftime('%d/%m/%Y')
    default_start_date = default_start_date_dt.strftime('%d/%m/%Y')

    # Initialize user date inputs with defaults
    start_date_input = default_start_date
    end_date_input = default_end_date

    # Check if user submitted the form
    if request.method == 'POST':
        action = request.form.get("action")  # "load_stock" or "calculate_dca"
        symbol = request.form.get('symbol', '').strip()
        start_date_input = request.form.get('start_date') or default_start_date
        end_date_input = request.form.get('end_date') or default_end_date

        # Validate and parse the date inputs
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
                active_tab=active_tab
            )

        # Validate symbol
        if not symbol:
            error = "Please enter a valid stock symbol."
        else:
            # Attempt to fetch data
            try:
                data = fetch_stock_data(symbol)
                ticker = yf.Ticker(symbol)  # used for fundamentals, earnings, and options
            except Exception as e:
                error = f"Failed to fetch data for {symbol}. Error: {str(e)}"
                data = None

            if data is not None:
                # Filter data by the chosen date range
                try:
                    data = data.loc[start_date:end_date]
                except Exception as e:
                    error = f"Error filtering data by dates: {str(e)}"

                if data.empty:
                    error = "No data available for the selected date range."
                else:
                    # Calculate indicators (SMA, RSI, MACD, Bollinger, ATR, etc.)
                    data = calculate_indicators(data)

                    # Prepare the data for charting
                    stock_chart_data = {
                        'dates': data.index.strftime('%d/%m/%Y').tolist(),
                        'close': [safe_chart_val(val) for val in data['Close'].tolist()],
                        'sma50': [safe_chart_val(val) for val in data.get('SMA_50', []).tolist()],
                        'sma200': [safe_chart_val(val) for val in data.get('SMA_200', []).tolist()],
                        'macd': [safe_chart_val(val) for val in data.get('MACD', []).tolist()],
                        'rsi': [safe_chart_val(val) for val in data.get('RSI', []).tolist()]
                    }

                    # Get the latest row to display (if exists)
                    if not data.empty:
                        latest_data = data.iloc[-1]
                        result = {
                            'symbol': symbol,
                            'latest_close': safe_str(latest_data.get('Close', float('nan'))),
                            'SMA_50': safe_str(latest_data.get('SMA_50', float('nan'))),
                            'SMA_200': safe_str(latest_data.get('SMA_200', float('nan'))),
                            'RSI': safe_str(latest_data.get('RSI', float('nan'))),
                            'MACD': safe_str(latest_data.get('MACD', float('nan'))),
                            'Signal_Line': safe_str(latest_data.get('Signal_Line', float('nan')))
                        }
                        # Compute Sharpe ratio
                        sharpe = compute_sharpe_ratio(data, risk_free_rate=0.02)
                        result['sharpe_ratio'] = sharpe

                    # Handle DCA if needed
                    init_inv_str = request.form.get('initial_investment')
                    period_inv_str = request.form.get('periodic_investment')
                    duration_str = request.form.get('duration')

                    init_inv = float(init_inv_str.strip()) if init_inv_str and init_inv_str.strip() else 1000.0
                    period_inv = float(period_inv_str.strip()) if period_inv_str and period_inv_str.strip() else 200.0
                    dur = int(duration_str.strip()) if duration_str and duration_str.strip() else 5

                    calculated_exp_return = calculate_average_annual_return(data)
                    total_inv, future_value, total_profit, data_points = dca_calculation(
                        data,
                        initial_investment=init_inv,
                        periodic_investment=period_inv,
                        frequency=(request.form.get('frequency') or 'monthly').lower(),
                        years=dur,
                        annual_return=calculated_exp_return
                    )
                    dca_result = {
                        'total_invested': f"{total_inv:,.0f}",
                        'future_value': f"{future_value:,.0f}",
                        'total_profit': f"{total_profit:,.0f}",
                        'expected_return': f"{calculated_exp_return * 100:.2f}"
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

                    # Determine which tab to display after submission
                    if action == "calculate_dca":
                        active_tab = 'dca'
                    else:
                        active_tab = 'stock-data'

                    # Fetch fundamentals
                    try:
                        fundamentals_data = get_fundamentals(ticker)
                    except Exception:
                        fundamentals_data = {}
                    
                    # Fetch earnings
                    try:
                        earnings_data = fetch_earnings(symbol, api_key='your_api_key_here')
                    except Exception as e:
                        print("Earnings fetch exception:", e)
                        earnings_data = []
                    
                    # Fetch options chain
                    try:
                        calls, puts = get_options_chain(ticker)
                        options_chain = {'calls': calls, 'puts': puts} if (calls or puts) else None
                    except Exception as e:
                        print("Options chain exception:", e)
                        options_chain = None

                    # Fetch news using the new Search-based approach
                    try:
                        # Adjust news_count to however many articles you want, e.g., 10
                        news_data = get_news_by_search(symbol, news_count=10)
                    except Exception as e:
                        print("News fetch exception:", e)
                        news_data = []

    # Render the template with all data
    return render_template(
        'index.html',
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
        active_tab=active_tab
    )


if __name__ == '__main__':
    # Debug mode for development; set debug=False or remove for production
    app.run(debug=True)
