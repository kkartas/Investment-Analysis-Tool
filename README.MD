# Investment Analysis Tool

**Investment Analysis Tool** is a sophisticated, mobile-friendly stock market analysis platform. Leveraging real-time market data and advanced analytics, this platform helps investors make informed decisions through an intuitive, modern interface inspired by leading fintech applications.

## Key Features

### Modern User Interface
- **Responsive Dashboard Layout:** Fully mobile-optimized with a clean, card-based interface that scales beautifully across all devices
- **Interactive Charts:** Advanced data visualization using Chart.js with touch support for mobile users
- **Intuitive Navigation:** Simplified workflow with clear hierarchy and context-aware controls

### Technical Analysis
- **Comprehensive Technical Indicators:**
  - Simple Moving Averages (50 & 200-day)
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
  - Support & Resistance Levels
- **AI-Powered Recommendations:** Intelligent buy/hold/sell signals based on technical patterns
- **Market Sentiment Analysis:** Aggregated analyst recommendations with visual representation

### Investment Tools
- **Enhanced DCA Calculator:** Sophisticated dollar-cost averaging simulation with customizable parameters
- **Risk Assessment:** Volatility analysis and risk metrics for potential investments

### Fundamental Analysis
- **Key Financial Metrics:** Easy access to essential ratios and performance indicators
- **Earnings Reports:** Historical earnings data with surprise factors

### Real-Time Data
- **Live Price Updates:** Current market data for stocks
- **Breaking News Integration:** Latest financial news related to stocks
- **Historical Data Analysis:** Analyze stock performance over various time periods

## Disclaimer

**IMPORTANT:** The Investment Analysis Tool provides information for educational purposes only. None of the content constitutes financial advice or a recommendation to buy, sell, or hold any security.

- The technical indicators and recommendations are mathematical calculations based on historical data and should not be the sole basis for investment decisions
- Historical performance is not indicative of future results
- Always conduct your own research and consult with a qualified financial advisor before making investment decisions
- The creators and maintainers of this tool are not responsible for any investment decisions made based on the information provided

## Technology Stack

- **Frontend:**
  - HTML5, CSS3, JavaScript
  - Bootstrap 5 for responsive layouts
  - Chart.js for interactive visualizations
  - Alpine.js for lightweight reactivity
  - Font Awesome for modern iconography

- **Backend:**
  - Python with Flask framework
  - Pandas for data manipulation
  - NumPy for numerical operations
  - yfinance for market data

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/investment-analysis-tool.git
cd investment-analysis-tool
```

2. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Access the application at http://127.0.0.1:5000

## Usage Guide

### Stock Analysis
1. Enter a stock symbol or company name in the search bar
2. Select from predefined time periods (1M, 3M, 6M, 1Y, 5Y) or use the custom date range picker
3. Explore the technical indicators and AI-generated recommendations
4. Switch between tabs to view fundamental data, earnings, and news

### DCA Calculator
1. Navigate to the DCA Calculator tab
2. Set your initial investment amount
3. Configure periodic investment parameters (amount, frequency)
4. Specify the investment duration
5. Review the projected results and visualization

## License

This project is licensed under the MIT License.

## Acknowledgments

- Data provided by [Yahoo Finance](https://finance.yahoo.com/) through yfinance library
- This tool is for educational purposes only
