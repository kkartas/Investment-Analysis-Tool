
# Investment Analysis Tool

## Overview

The Investment Analysis Tool is an advanced Python application designed for individual investors and financial analysts to analyze stock market data, perform detailed technical analysis, and simulate investment strategies using Dollar-Cost Averaging (DCA). This tool leverages the power of real-time and historical data from Yahoo Finance, offering insightful visualizations and comprehensive investment analysis.

## Features

### 1. **Stock Data Fetching**
   - **Real-Time and Historical Data**: The application fetches stock data directly from Yahoo Finance using the `yfinance` API. Users can specify the stock symbol and the date range to retrieve relevant data.
   - **Caching Mechanism**: To optimize performance and reduce load on Yahoo Finance, the tool uses `requests-cache` to cache data locally, making subsequent requests faster.

### 2. **Technical Analysis**
   - **Simple Moving Averages (SMA)**: The tool calculates the 50-day and 200-day Simple Moving Averages, which are widely used to identify trends in stock prices.
   - **Relative Strength Index (RSI)**: RSI is calculated to measure the speed and change of price movements. It helps determine whether a stock is overbought or oversold.
   - **Moving Average Convergence Divergence (MACD)**: The MACD indicator is used to identify changes in the strength, direction, momentum, and duration of a trend in a stock's price.
   - **Signal Line**: The tool also calculates the Signal Line, which is a 9-day EMA of the MACD and is used to identify buy or sell signals.

### 3. **DCA (Dollar-Cost Averaging) Calculator**
   - **Investment Strategy Simulation**: Users can simulate a DCA strategy by entering their initial investment, periodic investment amount, investment frequency (weekly, monthly, quarterly, yearly), and expected annual return.
   - **Dynamic Calculations**: The tool calculates the total invested amount, future value of the investment, and total profit based on the input parameters.
   - **Interactive Visualization**: The DCA results are visualized with interactive Plotly charts, allowing users to explore the growth of their investments over time.

### 4. **Interactive Plots**
   - **Technical Analysis Visualization**: The tool provides interactive charts that visualize the stock's closing price, SMA, RSI, MACD, and Signal Line. These charts help users understand the stock's performance and technical indicators.
   - **DCA Growth Visualization**: The application visualizes the growth of investments over time, allowing users to see how their periodic investments accumulate and grow with compounding returns.

### 5. **Customizable Date Range**
   - Users can specify the start and end dates for data analysis, allowing for flexible and targeted analysis based on the user's needs.

## Installation

### Prerequisites

- Python 3.7 or higher

### Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/kkartas/investment-analysis-tool.git
    cd investment-analysis-tool
    ```

2. **Install the required dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the application:**

    ```bash
    python main.py
    ```

## Usage

### Main Features

#### 1. **Fetching Stock Data**
   - Enter a stock symbol (e.g., `AAPL` for Apple Inc.) in the "Stock Symbol" input box.
   - Specify the date range using the start and end date pickers.
   - Click "Load Data" to fetch and analyze the stock data from Yahoo Finance.

#### 2. **Technical Analysis**
   - After loading the data, the application automatically performs technical analysis.
   - The tool calculates SMA, RSI, MACD, and the Signal Line.
   - The results are displayed in the "Stock Analysis Results" section, along with a buy, hold, or sell recommendation based on the calculated indicators.

#### 3. **DCA Calculator**
   - Enter the initial investment amount, periodic investment amount, and choose the investment frequency.
   - Specify the expected annual return percentage.
   - Click "Calculate DCA" to simulate the investment strategy.
   - The tool calculates the future value of the investments and displays the results along with an interactive growth chart.

### User Interface

- **Stock Symbol**: Input the stock symbol to fetch and analyze data.
- **Date Range**: Use the date pickers to specify the analysis period.
- **DCA Parameters**: Enter details such as initial investment, periodic investment, frequency, and expected annual return for the DCA simulation.
- **Analysis Results**: View technical analysis results and DCA simulation results with interactive plots.

## Technical Analysis Explained

- **Simple Moving Average (SMA)**: The SMA is a commonly used indicator in technical analysis that helps smooth out price data by creating a constantly updated average price. The tool calculates both 50-day and 200-day SMAs.
  - *50-day SMA*: Often used to gauge short-term momentum.
  - *200-day SMA*: Typically used to identify long-term trends.

- **Relative Strength Index (RSI)**: The RSI is a momentum oscillator that measures the speed and change of price movements. It ranges from 0 to 100, with values above 70 indicating overbought conditions and values below 30 indicating oversold conditions.

- **Moving Average Convergence Divergence (MACD)**: MACD is a trend-following momentum indicator that shows the relationship between two moving averages of a security’s price. It is calculated by subtracting the 26-period EMA from the 12-period EMA.
  - *Signal Line*: A 9-day EMA of the MACD, used to identify buy and sell signals.

## Project Structure

```plaintext
├── dca_calculations.py  # Contains functions for DCA calculations
├── load.py              # Handles data fetching from Yahoo Finance
├── main.py              # Entry point to run the application
├── stock_analysis.py    # Implements technical analysis calculations
├── ui.py                # Defines the user interface using PyQt5
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## Acknowledgments

- [Yahoo Finance](https://finance.yahoo.com) for providing financial data.
- [yfinance](https://pypi.org/project/yfinance/) for the API used to fetch stock data.
- [Plotly](https://plotly.com/python/) for interactive graphing capabilities.
- [PyQt5](https://pypi.org/project/PyQt5/) for the GUI framework.
