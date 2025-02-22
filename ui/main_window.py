# ui/main_window.py

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDateEdit, QComboBox, QSpinBox, QTextEdit,
    QTabWidget, QGroupBox
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QDate
from PyQt5.QtWebEngineWidgets import QWebEngineView
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import yfinance as yf

# Import our application modules
from services.data_loader import fetch_stock_data
from models.stock_analysis import calculate_indicators, get_latest_recommendation
from models.dca_calculations import calculate_average_annual_return, dca_calculation
from models.fundamentals import get_fundamentals
from models.options import get_options_chain
from ui.components import CollapsibleSection

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Investment Analysis Tool")
        self.setWindowIcon(QIcon('resources/icons/app_icon.png'))
        self.resize(1200, 800)
        self.setFont(QFont('Arial', 10))
        self.setStyleSheet("font-size: 12pt;")
        
        self.data = None           # Historical stock data
        self.ticker = None         # yfinance.Ticker object
        self.stock_name = ""
        self.mean_annual_return = None

        # Default date range: 2 years ago to today
        self.default_start_date = datetime.today() - timedelta(days=2*365)
        self.default_end_date = datetime.today()
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top: Stock symbol and date range
        main_layout.addLayout(self.create_data_section())
        main_layout.addSpacing(10)
        
        # Tabs for different investor tools
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Technical Analysis & DCA Calculator
        self.tech_tab = QWidget()
        self.init_tech_tab()
        self.tabs.addTab(self.tech_tab, "Technical Analysis")
        
        # Tab 2: Fundamentals
        self.fund_tab = QWidget()
        self.init_fund_tab()
        self.tabs.addTab(self.fund_tab, "Fundamentals")
        
        # Tab 3: Options Chain
        self.options_tab = QWidget()
        self.init_options_tab()
        self.tabs.addTab(self.options_tab, "Options")
        
        # Tab 4: Dividends
        self.dividends_tab = QWidget()
        self.init_dividends_tab()
        self.tabs.addTab(self.dividends_tab, "Dividends")
        
        # Tab 5: Earnings
        self.earnings_tab = QWidget()
        self.init_earnings_tab()
        self.tabs.addTab(self.earnings_tab, "Earnings")
        
        # Tab 6: Financials
        self.financials_tab = QWidget()
        self.init_financials_tab()
        self.tabs.addTab(self.financials_tab, "Financials")
    
    def create_data_section(self):
        layout = QVBoxLayout()
        group = QGroupBox("Stock Data Input")
        group_layout = QVBoxLayout()
        
        # Stock symbol input and Load button
        sym_layout = QHBoxLayout()
        label = QLabel("Stock Symbol:")
        self.stock_symbol_input = QLineEdit()
        self.stock_symbol_input.setPlaceholderText("e.g., AAPL")
        self.stock_symbol_input.setFixedWidth(200)
        load_button = QPushButton("Load Data")
        load_button.setIcon(QIcon('resources/icons/load_icon.png'))
        load_button.clicked.connect(self.load_data)
        sym_layout.addWidget(label)
        sym_layout.addWidget(self.stock_symbol_input)
        sym_layout.addWidget(load_button)
        group_layout.addLayout(sym_layout)
        
        # Date range selection
        date_layout = QHBoxLayout()
        start_label = QLabel("Start Date:")
        self.start_date_picker = QDateEdit(calendarPopup=True)
        self.start_date_picker.setDate(QDate(self.default_start_date.year, self.default_start_date.month, self.default_start_date.day))
        end_label = QLabel("End Date:")
        self.end_date_picker = QDateEdit(calendarPopup=True)
        self.end_date_picker.setDate(QDate(self.default_end_date.year, self.default_end_date.month, self.default_end_date.day))
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_picker)
        date_layout.addSpacing(20)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_picker)
        group_layout.addLayout(date_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        return layout
    
    # ------------------ Technical Analysis Tab ------------------ #
    def init_tech_tab(self):
        layout = QVBoxLayout(self.tech_tab)
        
        # Upper area: Technical Analysis results (text and interactive chart)
        res_layout = QHBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedWidth(400)
        self.result_text.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        self.plot_view = QWebEngineView()
        res_layout.addWidget(self.result_text)
        res_layout.addWidget(self.plot_view)
        layout.addLayout(res_layout)
        
        # Lower area: DCA Calculator (in a collapsible section)
        dca_widget = QWidget()
        dca_layout = QVBoxLayout(dca_widget)
        init_label = QLabel("Initial Investment ($):")
        self.initial_investment_input = QLineEdit()
        self.initial_investment_input.setPlaceholderText("e.g., 1000")
        dca_layout.addWidget(init_label)
        dca_layout.addWidget(self.initial_investment_input)
        period_label = QLabel("Periodic Investment ($):")
        self.periodic_investment_input = QLineEdit()
        self.periodic_investment_input.setPlaceholderText("e.g., 200")
        dca_layout.addWidget(period_label)
        dca_layout.addWidget(self.periodic_investment_input)
        freq_label = QLabel("Investment Frequency:")
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["Weekly", "Monthly", "Quarterly", "Yearly"])
        dca_layout.addWidget(freq_label)
        dca_layout.addWidget(self.frequency_combo)
        duration_label = QLabel("Duration (Years):")
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 50)
        self.duration_input.setValue(5)
        dca_layout.addWidget(duration_label)
        dca_layout.addWidget(self.duration_input)
        return_label = QLabel("Expected Annual Return (%):")
        self.return_input = QLineEdit()
        self.return_input.setPlaceholderText("e.g., 7")
        dca_layout.addWidget(return_label)
        dca_layout.addWidget(self.return_input)
        calc_button = QPushButton("Calculate DCA")
        calc_button.setIcon(QIcon('resources/icons/calculate_icon.png'))
        calc_button.clicked.connect(self.run_dca_calculation)
        dca_layout.addWidget(calc_button)
        collapsible = CollapsibleSection("DCA (Dollar-Cost Averaging) Calculator", dca_widget)
        layout.addWidget(collapsible)
    
    def run_stock_analysis(self):
        if self.data is None:
            return
        
        # Calculate technical indicators
        self.data = calculate_indicators(self.data)
        latest = self.data.iloc[-1]
        
        # Check for missing critical indicators (SMA_50 and SMA_200)
        import pandas as pd
        missing = []
        for key in ['SMA_50', 'SMA_200']:
            if pd.isna(latest.get(key)):
                missing.append(key)
        if missing:
            QMessageBox.information(
                self, 
                "Partial Data",
                f"Insufficient data to compute: {', '.join(missing)}. Some indicators may be unavailable."
            )
        
        # Determine recommendation if possible
        if pd.isna(latest.get('SMA_50')) or pd.isna(latest.get('SMA_200')):
            recommendation = "N/A"
        else:
            _, recommendation = get_latest_recommendation(self.data)
        
        def fmt(val):
            return f"{val:.2f}" if pd.notna(val) else "N/A"
        
        rec_color = {"Buy": "green", "Hold": "#DAA520", "Sell": "red"}.get(recommendation, "black")
        result_html = f"""
        <b>Technical Analysis for {self.stock_name}:</b><br>
        <b>Latest Close:</b> ${fmt(latest['Close'])}<br>
        <b>50-day SMA:</b> ${fmt(latest.get('SMA_50'))}<br>
        <b>200-day SMA:</b> ${fmt(latest.get('SMA_200'))}<br>
        <b>RSI:</b> {fmt(latest.get('RSI'))}<br>
        <b>MACD:</b> {fmt(latest.get('MACD'))}<br>
        <b>Signal Line:</b> {fmt(latest.get('Signal_Line'))}<br>
        <b>Bollinger MA:</b> ${fmt(latest.get('MA'))}<br>
        <b>Upper Band:</b> ${fmt(latest.get('Upper_Band'))}<br>
        <b>Lower Band:</b> ${fmt(latest.get('Lower_Band'))}<br>
        <b>ATR:</b> {fmt(latest.get('ATR'))}<br>
        <b>Recommendation:</b> <span style="color:{rec_color};">{recommendation}</span>
        """
        self.result_text.setHtml(result_html)
        self.plot_stock_analysis()
    
    def plot_stock_analysis(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['Close'], mode='lines', name='Close'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_50'], mode='lines', name='50-day SMA'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_200'], mode='lines', name='200-day SMA'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['Upper_Band'], mode='lines', name='Upper Band'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['Lower_Band'], mode='lines', name='Lower Band'))
        fig.update_layout(
            title=f"{self.stock_name} Technical Chart",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        fig.update_xaxes(rangeslider_visible=True)
        html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        self.plot_view.setHtml(html)
    
    def run_dca_calculation(self):
        if self.data is None:
            QMessageBox.warning(self, "Data Not Loaded", "Please load stock data first.")
            return
        try:
            initial = float(self.initial_investment_input.text())
            periodic = float(self.periodic_investment_input.text())
            frequency = self.frequency_combo.currentText().lower()
            years = int(self.duration_input.value())
            annual_return = float(self.return_input.text()) / 100
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for DCA.")
            return
        
        total_inv, port_value, profit, dca_points = dca_calculation(
            self.data, initial, periodic, frequency, years, annual_return
        )
        result_html = f"""
        <b>DCA Results for {self.stock_name}:</b><br>
        <b>Total Invested:</b> ${total_inv:,.2f}<br>
        <b>Future Value:</b> ${port_value:,.2f}<br>
        <b>Total Profit:</b> ${profit:,.2f}
        """
        self.result_text.setHtml(result_html)
        self.plot_dca_growth(dca_points)
    
    def plot_dca_growth(self, points):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=points['dates'], y=points['invested'], mode='lines', name='Invested'))
        fig.add_trace(go.Scatter(x=points['dates'], y=points['value'], mode='lines', name='Portfolio Value'))
        fig.update_layout(
            title=f"{self.stock_name} DCA Growth",
            xaxis_title="Time",
            yaxis_title="Amount (USD)",
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        fig.update_xaxes(rangeslider_visible=True)
        html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        self.plot_view.setHtml(html)
    
    # ------------------ Fundamentals Tab ------------------ #
    def init_fund_tab(self):
        layout = QVBoxLayout(self.fund_tab)
        self.fund_text = QTextEdit()
        self.fund_text.setReadOnly(True)
        layout.addWidget(self.fund_text)
    
    def display_fundamentals(self):
        fundamentals = get_fundamentals(self.ticker)
        html = "<h3>Fundamental Data</h3><ul>"
        for key, value in fundamentals.items():
            html += f"<li><b>{key}:</b> {value}</li>"
        html += "</ul>"
        self.fund_text.setHtml(html)
    
    # ------------------ Options Tab ------------------ #
    def init_options_tab(self):
        layout = QVBoxLayout(self.options_tab)
        self.options_text = QTextEdit()
        self.options_text.setReadOnly(True)
        layout.addWidget(self.options_text)
    
    def display_options(self):
        calls, puts = get_options_chain(self.ticker)
        if calls is None or puts is None:
            self.options_text.setHtml("No options data available.")
            return
        html = "<h3>Options Chain (Calls & Puts)</h3>"
        html += "<b>Calls:</b>" + calls.to_html() + "<br><br>"
        html += "<b>Puts:</b>" + puts.to_html()
        self.options_text.setHtml(html)
    
    # ------------------ Dividends Tab ------------------ #
    def init_dividends_tab(self):
        layout = QVBoxLayout(self.dividends_tab)
        self.dividends_text = QTextEdit()
        self.dividends_text.setReadOnly(True)
        layout.addWidget(self.dividends_text)
    
    def display_dividends(self):
        if self.ticker is None:
            self.dividends_text.setHtml("No data available.")
            return
        dividends = self.ticker.dividends
        if dividends.empty:
            self.dividends_text.setHtml("No dividend data available.")
            return
        df = dividends.to_frame(name="Dividend")
        df.index.name = "Date"
        html = "<h3>Dividend History</h3>"
        html += df.to_html()
        self.dividends_text.setHtml(html)
    
    # ------------------ Earnings Tab ------------------ #
    def init_earnings_tab(self):
        layout = QVBoxLayout(self.earnings_tab)
        self.earnings_text = QTextEdit()
        self.earnings_text.setReadOnly(True)
        layout.addWidget(self.earnings_text)
    
    def display_earnings(self):
        if self.ticker is None:
            self.earnings_text.setHtml("No earnings data available.")
            return
        html = "<h3>Earnings Calendar & Historical Earnings</h3>"
        # Upcoming calendar events
        calendar = self.ticker.calendar
        if isinstance(calendar, dict):
            if calendar:
                df_calendar = pd.DataFrame([calendar])
                html += "<b>Upcoming Calendar Events:</b><br>"
                html += df_calendar.to_html() + "<br><br>"
            else:
                html += "<b>Upcoming Calendar Events:</b> N/A<br><br>"
        elif hasattr(calendar, "empty") and not calendar.empty:
            html += "<b>Upcoming Calendar Events:</b><br>"
            html += calendar.to_html() + "<br><br>"
        else:
            html += "<b>Upcoming Calendar Events:</b> N/A<br><br>"
        # Annual earnings using Income Statement: show "Net Income"
        income_stmt = self.ticker.income_stmt
        if income_stmt is not None and not income_stmt.empty:
            if "Net Income" in income_stmt.index:
                net_income_series = income_stmt.loc["Net Income"]
                # Convert the series to a DataFrame for display
                net_income_df = pd.DataFrame(net_income_series).transpose()
                html += "<b>Historical Annual Net Income:</b><br>"
                html += net_income_df.to_html() + "<br><br>"
            else:
                html += "<b>Historical Annual Net Income:</b> Not available<br><br>"
        else:
            html += "<b>Historical Annual Net Income:</b> N/A<br><br>"
        # Quarterly earnings using Quarterly Income Statement: show "Net Income"
        quarterly_income = self.ticker.quarterly_income_stmt
        if quarterly_income is not None and not quarterly_income.empty:
            if "Net Income" in quarterly_income.index:
                q_net_income_series = quarterly_income.loc["Net Income"]
                q_net_income_df = pd.DataFrame(q_net_income_series).transpose()
                html += "<b>Quarterly Net Income:</b><br>"
                html += q_net_income_df.to_html() + "<br><br>"
            else:
                html += "<b>Quarterly Net Income:</b> Not available<br><br>"
        else:
            html += "<b>Quarterly Net Income:</b> N/A<br><br>"
        self.earnings_text.setHtml(html)
    
    # ------------------ Financials Tab ------------------ #
    def init_financials_tab(self):
        layout = QVBoxLayout(self.financials_tab)
        self.financials_combo = QComboBox()
        self.financials_combo.addItems(["Balance Sheet", "Income Statement", "Cash Flow"])
        self.financials_combo.currentIndexChanged.connect(self.display_financials)
        layout.addWidget(self.financials_combo)
        
        self.financials_text = QTextEdit()
        self.financials_text.setReadOnly(True)
        layout.addWidget(self.financials_text)
    
    def display_financials(self):
        if self.ticker is None:
            self.financials_text.setHtml("No financial data available.")
            return
        statement = self.financials_combo.currentText()
        if statement == "Balance Sheet":
            data = self.ticker.balance_sheet
        elif statement == "Income Statement":
            data = self.ticker.financials
        elif statement == "Cash Flow":
            data = self.ticker.cashflow
        else:
            data = None
        
        if data is None or (hasattr(data, "empty") and data.empty):
            self.financials_text.setHtml("No data available for " + statement)
        else:
            html = f"<h3>{statement}</h3>"
            html += data.to_html()
            self.financials_text.setHtml(html)
    
    # ------------------ Data Loading ------------------ #
    def load_data(self):
        symbol = self.stock_symbol_input.text().strip()
        if not symbol:
            QMessageBox.warning(self, "Input Error", "Please enter a stock symbol.")
            return
        try:
            data = fetch_stock_data(symbol)
            self.data = data
            
            # Create a yfinance Ticker object for additional data
            self.ticker = yf.Ticker(symbol)
            self.stock_name = self.ticker.info.get("longName", symbol)
            
            # Adjust date range if necessary
            max_start = data.index.min().date()
            max_end = data.index.max().date()
            sel_start = self.start_date_picker.date().toPyDate()
            sel_end = self.end_date_picker.date().toPyDate()
            if sel_start < max_start or sel_end > max_end:
                QMessageBox.information(
                    self, "Date Adjustment",
                    f"Data available from {max_start} to {max_end}. Adjusting date range."
                )
                sel_start = max(sel_start, max_start)
                sel_end = min(sel_end, max_end)
            tz_info = data.index.tz
            sel_start = pd.Timestamp(sel_start).tz_localize(tz_info)
            sel_end = pd.Timestamp(sel_end).tz_localize(tz_info)
            self.data = data.loc[sel_start:sel_end]
            if self.data.empty:
                QMessageBox.warning(self, "No Data", "No data available for the selected range.")
                return
            
            # Set default expected return from historical data
            self.mean_annual_return = calculate_average_annual_return(self.data)
            self.return_input.setText(f"{self.mean_annual_return * 100:.2f}")
            
            # Run analysis and update all tabs
            self.run_stock_analysis()
            self.display_fundamentals()
            self.display_options()
            self.display_dividends()
            self.display_earnings()
            self.display_financials()
        except Exception as e:
            QMessageBox.critical(self, "Data Load Error", str(e))

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
