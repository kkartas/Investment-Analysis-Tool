import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QGroupBox, QTextEdit, QComboBox, QSpinBox, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objs as go
import plotly.io as pio
import pandas as pd
from dca_calculations import calculate_average_interest

class InvestmentToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Investment Analysis Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('resources/icons/app_icon.png'))

        self.data = None  # To store loaded data
        self.mean_annual_return = None  # To store calculated mean annual return

        self.init_ui()

    def init_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create and add sections
        main_layout.addLayout(self.create_data_source_section())
        main_layout.addSpacing(20)
        main_layout.addLayout(self.create_dca_section())
        main_layout.addSpacing(20)
        main_layout.addLayout(self.create_result_section())

    def create_data_source_section(self):
        layout = QHBoxLayout()

        # Data Source GroupBox
        data_source_group = QGroupBox("Data Source")
        data_source_layout = QHBoxLayout()

        # Radio Buttons
        self.yfinance_radio = QRadioButton("Fetch from yfinance")
        self.csv_radio = QRadioButton("Load CSV File")
        self.yfinance_radio.setChecked(True)

        # Stock Symbol Input
        self.stock_symbol_input = QLineEdit()
        self.stock_symbol_input.setPlaceholderText("Enter Stock Symbol (e.g., AAPL)")
        self.stock_symbol_input.setFixedWidth(200)

        # Load Button
        load_button = QPushButton("Load Data")
        load_button.setIcon(QIcon('resources/icons/load_icon.png'))
        load_button.clicked.connect(self.load_data)

        # Add widgets to layout
        data_source_layout.addWidget(self.yfinance_radio)
        data_source_layout.addWidget(self.csv_radio)
        data_source_layout.addWidget(self.stock_symbol_input)
        data_source_layout.addWidget(load_button)

        data_source_group.setLayout(data_source_layout)
        layout.addWidget(data_source_group)

        return layout

    def create_dca_section(self):
        layout = QVBoxLayout()

        # DCA GroupBox
        dca_group = QGroupBox("DCA (Dollar-Cost Averaging) Calculator")
        dca_layout = QVBoxLayout()

        form_layout = QVBoxLayout()
        initial_investment_label = QLabel("Initial Investment ($):")
        self.initial_investment_input = QLineEdit()
        self.initial_investment_input.setPlaceholderText("e.g., 1000")
        form_layout.addWidget(initial_investment_label)
        form_layout.addWidget(self.initial_investment_input)

        periodic_investment_label = QLabel("Periodic Investment ($):")
        self.periodic_investment_input = QLineEdit()
        self.periodic_investment_input.setPlaceholderText("e.g., 200")
        form_layout.addWidget(periodic_investment_label)
        form_layout.addWidget(self.periodic_investment_input)

        period_label = QLabel("Investment Frequency:")
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Weekly", "Monthly", "Quarterly", "Yearly"])
        form_layout.addWidget(period_label)
        form_layout.addWidget(self.period_combo)

        duration_label = QLabel("Investment Duration (Years):")
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 50)
        self.duration_input.setValue(5)
        form_layout.addWidget(duration_label)
        form_layout.addWidget(self.duration_input)

        return_label = QLabel("Expected Annual Return (%):")
        self.return_input = QLineEdit()
        self.return_input.setPlaceholderText("e.g., 7")
        form_layout.addWidget(return_label)
        form_layout.addWidget(self.return_input)

        calculate_button = QPushButton("Calculate DCA")
        calculate_button.setIcon(QIcon('resources/icons/calculate_icon.png'))
        calculate_button.clicked.connect(self.run_dca_calculation)
        form_layout.addWidget(calculate_button)

        dca_layout.addLayout(form_layout)
        dca_group.setLayout(dca_layout)
        layout.addWidget(dca_group)

        return layout

    def create_result_section(self):
        layout = QHBoxLayout()

        # Text Result Display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedWidth(400)
        self.result_text.setStyleSheet("background-color: #f0f0f0; padding: 10px;")

        # WebEngineView for Plotly
        self.plot_view = QWebEngineView()
        
        layout.addWidget(self.result_text)
        layout.addWidget(self.plot_view)

        return layout

    def load_data(self):
        if self.yfinance_radio.isChecked():
            stock_symbol = self.stock_symbol_input.text().strip()
            if not stock_symbol:
                QMessageBox.warning(self, "Input Error", "Please enter a stock symbol.")
                return
            from load import fetch_yfinance_data
            self.data = fetch_yfinance_data(stock_symbol)
        else:
            from load import load_file
            self.data = load_file()

        if self.data is not None:
            QMessageBox.information(self, "Success", "Data loaded successfully!")

            # Calculate and set the mean annual return
            self.mean_annual_return = calculate_average_interest(self.data)
            self.return_input.setText(f"{self.mean_annual_return * 100:.2f}")

            # Automatically run stock analysis after data is loaded
            self.run_stock_analysis()
        else:
            QMessageBox.critical(self, "Error", "Failed to load data.")

    def run_stock_analysis(self):
        from stock_analysis import calculate_indicators, get_latest_recommendation

        self.data = calculate_indicators(self.data)
        latest_data, recommendation = get_latest_recommendation(self.data)

        result_text = f"""
<b>Stock Analysis Results:</b><br>
<b>Latest Close:</b> ${latest_data['Close']:.2f}<br>
<b>50-day SMA:</b> ${latest_data['SMA_50']:.2f}<br>
<b>200-day SMA:</b> ${latest_data['SMA_200']:.2f}<br>
<b>RSI:</b> {latest_data['RSI']:.2f}<br>
<b>MACD:</b> {latest_data['MACD']:.2f}<br>
<b>Signal Line:</b> {latest_data['Signal_Line']:.2f}<br>
<b>Recommendation:</b> {recommendation}
"""
        self.result_text.setHtml(result_text)

        self.plot_stock_analysis()

    def plot_stock_analysis(self):
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['Close'], mode='lines', name='Close Price'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_50'], mode='lines', name='50-day SMA'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_200'], mode='lines', name='200-day SMA'))

        fig.update_layout(title="Stock Analysis", xaxis_title="Date", yaxis_title="Price (USD)", template="plotly_white")
        fig.update_xaxes(rangeslider_visible=True)

        # Generate HTML content with Plotly's JavaScript included
        html_content = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
       
        self.plot_view.setHtml(html_content)

    def run_dca_calculation(self):
        try:
            initial_investment = float(self.initial_investment_input.text())
            periodic_investment = float(self.periodic_investment_input.text())
            period = self.period_combo.currentText().lower()  # Changed to lowercase for consistency
            years = int(self.duration_input.value())
            annual_return = float(self.return_input.text()) / 100
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
            return

        from dca_calculations import dca_calculation

        total_invested, future_value, total_profit, data_points = dca_calculation(
            self.data,  # Pass self.data to use the loaded data for calculations
            initial_investment,
            periodic_investment,
            period,
            years,
            average_interest=annual_return
        )

        result_text = f"""
<b>DCA Calculation Results:</b><br>
<b>Total Invested:</b> ${total_invested:,.2f}<br>
<b>Future Value:</b> ${future_value:,.2f}<br>
<b>Total Profit:</b> ${total_profit:,.2f}
"""
        self.result_text.setHtml(result_text)

        self.plot_dca_growth(data_points)

    def plot_dca_growth(self, data_points):
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=data_points['dates'], y=data_points['invested'], mode='lines', name='Total Invested'))
        fig.add_trace(go.Scatter(x=data_points['dates'], y=data_points['value'], mode='lines', name='Portfolio Value'))

        fig.update_layout(title="DCA Investment Growth Over Time", xaxis_title="Time", yaxis_title="Amount (USD)", template="plotly_white")
        fig.update_xaxes(rangeslider_visible=True)

        # Generate HTML content with Plotly's JavaScript included
        html_content = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        
        self.plot_view.setHtml(html_content)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InvestmentToolApp()
    window.show()
    sys.exit(app.exec_())
