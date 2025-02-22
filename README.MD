# Investment Analysis Tool

The **Investment Analysis Tool** is an advanced Python application designed for individual investors and financial analysts. It leverages real-time and historical data from Yahoo Finance to perform in-depth technical analysis, simulate investment strategies, and display key financial metrics. The tool now includes additional features such as an earnings display (using income statements), financial statements, dividend history, and options chain data—all in one modern, tabbed interface.

## Features

- **Technical Analysis & DCA Calculator**
  - Calculates key technical indicators:
    - 50-day & 200-day Simple Moving Averages (SMA)
    - Relative Strength Index (RSI)
    - Moving Average Convergence Divergence (MACD) and Signal Line
    - Bollinger Bands (20-day Moving Average ± 2 standard deviations)
    - Average True Range (ATR)
  - Provides a buy/hold/sell recommendation based on indicator values.
  - Interactive Plotly chart displaying price trends and technical indicators.
  - Dollar-Cost Averaging (DCA) simulation with customizable investment parameters.

- **Fundamentals**
  - Displays fundamental data extracted from Yahoo Finance, including key ratios and metrics.
  
- **Options Chain**
  - Retrieves and displays options chain data (calls and puts) for the selected stock.

- **Dividends**
  - Presents a historical dividend history in an easy-to-read table format.

- **Earnings**
  - Shows upcoming calendar events from the earnings calendar.
  - Displays historical annual and quarterly net income using income statement data (replacing deprecated earnings API).

- **Financials**
  - Lets the user switch between viewing the Balance Sheet, Income Statement, and Cash Flow Statement.

## Installation

### Prerequisites

- Python 3.7 or higher

### Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/investment-analysis-tool.git
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

1. **Load Stock Data**
   - Enter a valid stock symbol (e.g., `AAPL`).
   - Choose a date range using the provided date pickers.
   - Click the **Load Data** button to fetch historical price data from Yahoo Finance.

2. **Technical Analysis & DCA Calculator**
   - View calculated technical indicators and a recommendation based on the latest available data.
   - Use the integrated DCA calculator by entering your initial and periodic investments, investment frequency, and expected annual return.
   - Interactive charts update dynamically based on the loaded data and calculations.

3. **Fundamentals**
   - Review key financial ratios and fundamental metrics provided by Yahoo Finance.

4. **Options Chain**
   - Examine current options chain data (both calls and puts) for the selected stock.

5. **Dividends**
   - View historical dividend payouts in a tabulated format.

6. **Earnings**
   - Check upcoming calendar events related to earnings.
   - See historical annual and quarterly net income (extracted from income statements).

7. **Financials**
   - Toggle between the Balance Sheet, Income Statement, and Cash Flow Statement to review detailed financial data.

## Project Structure

```plaintext
investment-analysis-tool/
├── main.py                     # Entry point for the application
├── README.md                   # Project documentation
├── requirements.txt            # Required Python packages
├── models/
│   ├── __init__.py
│   ├── dca_calculations.py     # Dollar-Cost Averaging simulation functions
│   ├── stock_analysis.py       # Technical indicator calculations and recommendations
│   ├── fundamentals.py         # Fundamental data extraction from Yahoo Finance
│   ├── options.py              # Options chain data extraction
│   └── ...                     # Other modules as needed
├── services/
│   ├── __init__.py
│   └── data_loader.py          # Fetches historical stock data with caching
└── ui/
    ├── __init__.py
    ├── components.py           # Reusable UI components (e.g., collapsible sections)
    └── main_window.py          # Main application window (tabbed interface)
```

## Future Enhancements

- Integration of additional investor tools (e.g., earnings forecasts, dividend yield analysis, portfolio performance tracking).
- Improved error handling and logging for a production environment.
- Enhanced UI/UX design with responsive layout adjustments for mobile devices.
- Options to export charts and data for further analysis.

## Contributing

Contributions are welcome! Feel free to fork the repository and submit pull requests for additional features, bug fixes, or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
