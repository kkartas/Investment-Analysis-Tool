# app.py
from flask import Flask, render_template, request, flash
import yfinance as yf
from datetime import datetime, timedelta
from models.stock_analysis import calculate_indicators, get_latest_recommendation
from models.dca_calculations import dca_calculation
from services.data_loader import fetch_stock_data
from models.fundamentals import get_fundamentals
from models.earnings import fetch_earnings
from models.options import get_options_chain
from models.news import get_news

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Needed for flash messages

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

    # Set default dates: end_date is today, start_date is 2 years ago
    default_end_date_dt = datetime.today()
    default_start_date_dt = default_end_date_dt - timedelta(days=730)
    default_end_date = default_end_date_dt.strftime('%d/%m/%Y')
    default_start_date = default_start_date_dt.strftime('%d/%m/%Y')

    if request.method == 'POST':
        symbol = request.form.get('symbol', '').strip()
        start_date_input = request.form.get('start_date') or default_start_date
        end_date_input = request.form.get('end_date') or default_end_date

        # Convert dates from DD/MM/YYYY to YYYY-MM-DD for filtering
        try:
            start_date = datetime.strptime(start_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_input, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            error = "Dates must be in DD/MM/YYYY format."
            return render_template('index.html', error=error,
                                   default_start_date=default_start_date,
                                   default_end_date=default_end_date)

        if not symbol:
            error = "Please enter a valid stock symbol."
        else:
            try:
                # Fetch historical stock data
                data = fetch_stock_data(symbol)
                # Create a ticker object for additional data
                ticker = yf.Ticker(symbol)
            except Exception as e:
                error = f"Failed to fetch data for {symbol}. Error: {str(e)}"
                data = None

            if data is not None:
                # Filter data by the selected date range
                try:
                    data = data.loc[start_date:end_date]
                except Exception as e:
                    error = f"Error filtering data by dates: {str(e)}"

                if data.empty:
                    error = "No data available for the selected date range."
                else:
                    # Technical Analysis
                    data = calculate_indicators(data)
                    latest_data, recommendation = get_latest_recommendation(data)
                    if latest_data is not None:
                        result = {
                            'symbol': symbol,
                            'latest_close': f"{latest_data['Close']:.2f}",
                            'SMA_50': f"{latest_data['SMA_50']:.2f}",
                            'SMA_200': f"{latest_data['SMA_200']:.2f}",
                            'RSI': f"{latest_data['RSI']:.2f}",
                            'MACD': f"{latest_data['MACD']:.2f}",
                            'Signal_Line': f"{latest_data['Signal_Line']:.2f}",
                            'recommendation': recommendation
                        }
                    else:
                        result = {}

                    # Prepare stock chart data for Plotly
                    stock_chart_data = {
                        'dates': data.index.strftime('%d/%m/%Y').tolist(),
                        'close': data['Close'].round(2).tolist()
                    }

                    # DCA Calculator (if parameters provided)
                    if all([request.form.get('initial_investment'),
                            request.form.get('periodic_investment'),
                            request.form.get('duration'),
                            request.form.get('expected_return')]):
                        try:
                            init_inv = float(request.form.get('initial_investment'))
                            period_inv = float(request.form.get('periodic_investment'))
                            dur = int(request.form.get('duration'))
                            exp_return = float(request.form.get('expected_return')) / 100
                            total_inv, future_value, total_profit, data_points = dca_calculation(
                                data, init_inv, period_inv, request.form.get('frequency').lower(), dur, annual_return=exp_return
                            )
                            dca_result = {
                                'total_invested': f"{total_inv:.2f}",
                                'future_value': f"{future_value:.2f}",
                                'total_profit': f"{total_profit:.2f}"
                            }
                            # Prepare DCA chart data
                            dca_chart_data = {
                                'dates': [d.strftime('%d/%m/%Y') for d in data_points['dates']],
                                'invested': data_points['invested'],
                                'value': data_points['value']
                            }
                        except ValueError:
                            error = "Invalid DCA parameters provided."

                    # Fetch additional information
                    try:
                        fundamentals_data = get_fundamentals(ticker)
                    except Exception as e:
                        fundamentals_data = {}
                    
                    try:
                        # Replace 'your_api_key_here' with your actual API key
                        earnings_data = fetch_earnings(symbol, api_key='your_api_key_here')
                    except Exception as e:
                        earnings_data = []
                    
                    try:
                        calls, puts = get_options_chain(ticker)
                        options_chain = {'calls': calls, 'puts': puts} if (calls or puts) else None
                    except Exception as e:
                        options_chain = None

                    try:
                        news_data = get_news(ticker)
                    except Exception as e:
                        news_data = []
    
    return render_template('index.html', result=result, dca_result=dca_result,
                           fundamentals=fundamentals_data, earnings=earnings_data,
                           options_chain=options_chain, news=news_data, error=error,
                           default_start_date=default_start_date,
                           default_end_date=default_end_date,
                           stock_chart_data=stock_chart_data,
                           dca_chart_data=dca_chart_data)

if __name__ == '__main__':
    app.run(debug=True)
