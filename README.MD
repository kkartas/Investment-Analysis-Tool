# Investment Analysis Tool

The **Investment Analysis Tool** is an advanced Python application designed for individual investors and financial analysts. Built with a modern, fintech-inspired user interface, the tool leverages real-time and historical data from Yahoo Finance to perform in-depth technical analysis, simulate investment strategies using Dollar-Cost Averaging (DCA), and display key financial metrics. The app is built as a Progressive Web App (PWA) using Flask, Bootstrap 5, Chart.js, and Flatpickr.

## Features

### Technical Analysis
- **Integrated Indicators Chart:**  
  The main chart displays the stock’s Close Price along with key technical indicators:
  - 50-day Simple Moving Average (SMA)
  - 200-day Simple Moving Average (SMA)
  - Moving Average Convergence Divergence (MACD)
  - Relative Strength Index (RSI)
  
  The chart uses dual y-axes to clearly display price-based values and momentum indicators. Missing data (for example, if the date range is too short for SMA200) is displayed as "N/A" while still plotting available data.

### Dollar-Cost Averaging (DCA) Calculator
- **Predefined Values & Dynamic Calculation:**  
  When stock data is loaded, default values (e.g. \$1,000 initial, \$200 periodic, 5 years duration) are set and a DCA simulation is automatically calculated using the stock’s historical expected annual return.  
- **Yearly Aggregated Results:**  
  The DCA chart aggregates the simulation into yearly labels (e.g. 2025, 2026, etc.) on the x-axis.
- **Formatted Results:**  
  The results (Total Invested, Future Value, Total Profit) are formatted without decimals and with thousand separators for improved readability.

### Additional Modules
- **Fundamentals:**  
  Displays key fundamental data extracted from Yahoo Finance.
- **Earnings Calendar:**  
  Fetches upcoming earnings events using a third-party API (requires a valid API key). Returns an empty list if no data is available.
- **Options Chain:**  
  Retrieves and displays current options chain data (calls and puts) for the selected stock.
- **News:**  
  Displays up to 10 recent news items related to the stock with title, publisher, and publication date formatted as DD/MM/YYYY HH:MM.

### Modern UI & PWA
- **Fintech-Inspired Design:**  
  Uses a clean, card-based layout, modern sans-serif fonts (e.g. Inter from Google Fonts), and a refined color palette.
- **Responsive Tabbed Navigation:**  
  Users can switch seamlessly between Stock Data (with technical analysis), DCA Calculator, Fundamentals, Earnings, Options Chain, and News.
- **Progressive Web App (PWA):**  
  The application includes a manifest and service worker for caching assets and offline support.

### Performance Improvements
- **Data Caching:**  
  Historical stock data is cached (using `requests_cache`) for one hour to improve performance on repeated queries.

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

3. **Configure API Keys:**
    - Update the earnings API key in the `app.py` file (replace `'your_api_key_here'` with your valid API key).

4. **Run the application:**
    ```bash
    python app.py
    ```

## Usage

1. **Load Stock Data:**
   - Enter a valid stock symbol (e.g. `AAPL`).
   - Choose a date range using the modern date picker (default is 2 years ago until today).
   - Click **Load Stock Data** to fetch historical data. The technical analysis chart will display available indicators, with missing values shown as "N/A".

2. **DCA Calculator:**
   - With the stock data loaded, default DCA values are pre-populated.
   - Click **Calculate DCA** to simulate an investment strategy. The DCA chart aggregates the simulation by year, and the results are displayed without decimals and with thousand separators.

3. **Additional Modules:**
   - **Fundamentals:** View key ratios and financial metrics.
   - **Earnings:** See upcoming earnings events (requires valid API key).
   - **Options Chain:** Examine current options chain data.
   - **News:** Read the latest news items related to the stock.

## Project Structure

```plaintext
investment-analysis-tool/
├── app.py                      # Main Flask application entry point
├── README.MD                   # Project documentation
├── requirements.txt            # Required Python packages
├── static/
│   ├── styles.css              # Custom CSS with modern styling
│   ├── manifest.json           # PWA manifest
│   └── sw.js                   # Service worker for caching assets
├── models/
│   ├── __init__.py             # Module initialization file
│   ├── stock_analysis.py       # Technical indicator calculations
│   ├── dca_calculations.py     # Dollar-Cost Averaging simulation functions
│   ├── fundamentals.py         # Fundamental data extraction
│   ├── earnings.py             # Earnings calendar integration
│   ├── options.py              # Options chain data extraction
│   └── news.py                 # News retrieval and formatting
└── services/
    ├── __init__.py             # Module initialization file
    └── data_loader.py          # Data fetching and caching using yfinance

## Future Enhancements

- **Enhanced Recommendation Engine:**  
  Develop a more sophisticated algorithm to provide buy/hold/sell recommendations based on the technical indicators.
- **Export Options:**  
  Allow users to export charts and data for further analysis.
- **Portfolio Tracking:**  
  Integrate additional tools for portfolio performance analysis and risk assessment.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for bug fixes or additional features. When contributing, follow these guidelines:
- Ensure your code is well-documented.
- Include tests for any new functionality.
- Follow the existing coding style and structure.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
