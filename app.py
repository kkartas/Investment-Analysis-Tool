# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import yfinance as yf

# Import modules
from services.data_loader import fetch_stock_data
from models.stock_analysis import calculate_indicators, get_latest_recommendation
from models.dca_calculations import calculate_average_annual_return, dca_calculation
from models.fundamentals import get_fundamentals
from models.options import get_options_chain

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    analysis = {}
    fundamentals = {}
    options_chain = {}
    error = None
    symbol = ""

    if request.method == 'POST':
        symbol = request.form.get("symbol")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        try:
            data = fetch_stock_data(symbol)
            # Optionally filter data by date range
            data = data.loc[start_date:end_date]
            if data.empty:
                error = "No data available for the selected date range."
            else:
                # Run technical analysis
                data = calculate_indicators(data)
                latest = data.iloc[-1]
                _, recommendation = get_latest_recommendation(data)
                analysis = {
                    "latest_close": latest["Close"],
                    "sma_50": latest.get("SMA_50"),
                    "sma_200": latest.get("SMA_200"),
                    "rsi": latest.get("RSI"),
                    "macd": latest.get("MACD"),
                    "signal_line": latest.get("Signal_Line"),
                    "upper_band": latest.get("Upper_Band"),
                    "lower_band": latest.get("Lower_Band"),
                    "atr": latest.get("ATR"),
                    "recommendation": recommendation
                }
                # Get fundamentals
                ticker = yf.Ticker(symbol)
                fundamentals = get_fundamentals(ticker)
                # Get options chain
                calls, puts = get_options_chain(ticker)
                options_chain = {
                    "calls": calls.to_html() if calls is not None else "N/A",
                    "puts": puts.to_html() if puts is not None else "N/A"
                }
        except Exception as e:
            error = str(e)

    return render_template("index.html", symbol=symbol, analysis=analysis,
                           fundamentals=fundamentals, options_chain=options_chain,
                           error=error)

if __name__ == '__main__':
    app.run(debug=True)
