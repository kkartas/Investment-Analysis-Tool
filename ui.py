from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QComboBox, QSpinBox, QMessageBox, QDateEdit, QSizePolicy, QFrame, QToolButton, QGroupBox
)
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtWebEngineWidgets import QWebEngineView
from datetime import datetime, timedelta
import yfinance as yf
from dca_calculations import calculate_average_interest
import plotly.graph_objs as go
import plotly.io as pio


class CollapsibleSection(QWidget):
    def __init__(self, title, content_widget, parent=None):
        super(CollapsibleSection, self).__init__(parent)

        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { text-align: left; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_toggled)

        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setMaximumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        content_layout = QVBoxLayout()
        content_layout.addWidget(content_widget)
        self.content_area.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def on_toggled(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_area.setMaximumHeight(16777215)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_area.setMaximumHeight(0)


class InvestmentToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Investment Analysis Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('resources/icons/app_icon.png'))

        # Set font scaling for higher DPI screens
        self.setFont(QFont('Arial', 10))
        self.setStyleSheet("font-size: 12pt;")

        self.data = None  # To store loaded data
        self.mean_annual_return = None  # To store calculated mean annual return
        self.default_start_date = datetime.today() - timedelta(days=2*365)  # Default to 2 years ago
        self.default_end_date = datetime.today()
        self.stock_name = ""  # To store stock name

        self.init_ui()

    def init_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create and add sections
        main_layout.addLayout(self.create_data_source_and_date_section())
        main_layout.addSpacing(20)
        main_layout.addWidget(self.create_dca_section())  # Now using collapsible section
        main_layout.addSpacing(20)
        main_layout.addLayout(self.create_result_section())

    def create_data_source_and_date_section(self):
        layout = QVBoxLayout()

        # Data Source & Date Range GroupBox
        data_source_group = QGroupBox("Time Period")
        data_source_layout = QVBoxLayout()

        # Stock Symbol Input
        symbol_layout = QHBoxLayout()
        stock_symbol_label = QLabel("Stock Symbol:")
        self.stock_symbol_input = QLineEdit()
        self.stock_symbol_input.setPlaceholderText("Enter Stock Symbol")
        self.stock_symbol_input.setFixedWidth(200)

        # Load Button
        load_button = QPushButton("Load Data")
        load_button.setIcon(QIcon('resources/icons/load_icon.png'))
        load_button.clicked.connect(self.load_data)

        symbol_layout.addWidget(stock_symbol_label)
        symbol_layout.addWidget(self.stock_symbol_input)
        symbol_layout.addWidget(load_button)

        data_source_layout.addLayout(symbol_layout)

        # Date Range Selection
        date_range_layout = QHBoxLayout()
        start_date_label = QLabel("Start Date:")
        self.start_date_picker = QDateEdit()
        self.start_date_picker.setCalendarPopup(True)
        self.start_date_picker.setDate(QDate(self.default_start_date.year, self.default_start_date.month, self.default_start_date.day))

        end_date_label = QLabel("End Date:")
        self.end_date_picker = QDateEdit()
        self.end_date_picker.setCalendarPopup(True)
        self.end_date_picker.setDate(QDate(self.default_end_date.year, self.default_end_date.month, self.default_end_date.day))

        # Align date pickers to the left half
        date_range_layout.addWidget(start_date_label)
        date_range_layout.addWidget(self.start_date_picker)
        date_range_layout.addSpacing(20)
        date_range_layout.addWidget(end_date_label)
        date_range_layout.addWidget(self.end_date_picker)
        date_range_layout.addStretch()  # Add stretch to push the widgets to the left half

        data_source_layout.addLayout(date_range_layout)

        data_source_group.setLayout(data_source_layout)
        layout.addWidget(data_source_group)

        return layout

    def load_data(self):
        start_date = self.start_date_picker.date().toPyDate()
        end_date = self.end_date_picker.date().toPyDate()

        stock_symbol = self.stock_symbol_input.text().strip()
        if not stock_symbol:
            QMessageBox.warning(self, "Input Error", "Please enter a stock symbol.")
            return

        from load import fetch_yfinance_data

        self.data, error_message = fetch_yfinance_data(stock_symbol)
        if self.data is None:
            QMessageBox.critical(self, "Error", f"Failed to fetch data for {stock_symbol}. {error_message}")
            return

        try:
            # Fetch the stock name and store it
            ticker = yf.Ticker(stock_symbol)
            self.stock_name = ticker.info.get('longName', stock_symbol)

            max_available_start = self.data.index.min().date()
            max_available_end = self.data.index.max().date()

            # Check if the user's selected dates are within the available data range
            if start_date < max_available_start or end_date > max_available_end:
                QMessageBox.information(self, "Date Range Adjustment",
                                        f"The data for {self.stock_name} is only available from {max_available_start} "
                                        f"to {max_available_end}. The period has been adjusted accordingly.")
                start_date = max(max_available_start, start_date)
                end_date = min(max_available_end, end_date)

            self.data = self.data.loc[start_date:end_date]

            # Calculate and set the mean annual return
            self.mean_annual_return = calculate_average_interest(self.data)
            self.return_input.setText(f"{self.mean_annual_return * 100:.2f}")

            # Automatically run stock analysis after data is loaded
            self.run_stock_analysis()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing data for {stock_symbol}.\n\nError details: {str(e)}")

    def create_dca_section(self):
        # Content of the DCA section
        dca_content = QWidget()
        dca_layout = QVBoxLayout()

        initial_investment_label = QLabel("Initial Investment ($):")
        self.initial_investment_input = QLineEdit()
        self.initial_investment_input.setPlaceholderText("e.g., 1000")
        dca_layout.addWidget(initial_investment_label)
        dca_layout.addWidget(self.initial_investment_input)

        periodic_investment_label = QLabel("Periodic Investment ($):")
        self.periodic_investment_input = QLineEdit()
        self.periodic_investment_input.setPlaceholderText("e.g., 200")
        dca_layout.addWidget(periodic_investment_label)
        dca_layout.addWidget(self.periodic_investment_input)

        period_label = QLabel("Investment Frequency:")
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Weekly", "Monthly", "Quarterly", "Yearly"])
        dca_layout.addWidget(period_label)
        dca_layout.addWidget(self.period_combo)

        duration_label = QLabel("Investment Duration (Years):")
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

        calculate_button = QPushButton("Calculate DCA")
        calculate_button.setIcon(QIcon('resources/icons/calculate_icon.png'))
        calculate_button.clicked.connect(self.run_dca_calculation)
        dca_layout.addWidget(calculate_button)

        dca_content.setLayout(dca_layout)

        # Create collapsible section
        dca_section = CollapsibleSection("DCA (Dollar-Cost Averaging) Calculator", dca_content)

        return dca_section

    def create_result_section(self):
        layout = QHBoxLayout()

        # Text Result Display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedWidth(400)
        self.result_text.setStyleSheet("background-color: #f0f0f0; padding: 10px;")

        # WebEngineView for Plotly
        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.result_text)
        layout.addWidget(self.plot_view)

        return layout

    def run_stock_analysis(self):
        from stock_analysis import calculate_indicators, get_latest_recommendation

        self.data = calculate_indicators(self.data)
        latest_data, recommendation = get_latest_recommendation(self.data)

        # Determine color and shadow based on recommendation
        recommendation_color = {
            "Buy": "green",
            "Hold": "#DAA520",  # Darker gold color for visibility
            "Sell": "red"
        }.get(recommendation, "black")
        text_shadow = "text-shadow: 1px 1px 2px black;"

        result_text = f"""
<b>Stock Analysis Results for {self.stock_name}:</b><br>
<b>Latest Close:</b> ${latest_data['Close']:.2f}<br>
<b>50-day SMA:</b> ${latest_data['SMA_50']:.2f}<br>
<b>200-day SMA:</b> ${latest_data['SMA_200']:.2f}<br>
<b>RSI:</b> {latest_data['RSI']:.2f}<br>
<b>MACD:</b> {latest_data['MACD']:.2f}<br>
<b>Signal Line:</b> {latest_data['Signal_Line']:.2f}<br>
<b>Recommendation:</b> <span style="color:{recommendation_color}; {text_shadow}">{recommendation}</span>
"""
        self.result_text.setHtml(result_text)

        self.plot_stock_analysis()

    def plot_stock_analysis(self):
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['Close'], mode='lines', name='Close Price'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_50'], mode='lines', name='50-day SMA'))
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data['SMA_200'], mode='lines', name='200-day SMA'))

        fig.update_layout(
            title=f"{self.stock_name} Stock Analysis",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white",
        )
        fig.update_xaxes(rangeslider_visible=True)
        fig.update_yaxes(fixedrange=False)  # Allow y-axis to scale

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
<b>DCA Calculation Results for {self.stock_name}:</b><br>
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

        fig.update_layout(
            title=f"{self.stock_name} DCA Investment Growth",
            xaxis_title="Time",
            yaxis_title="Amount (USD)",
            template="plotly_white",
        )
        fig.update_xaxes(rangeslider_visible=True)
        fig.update_yaxes(fixedrange=False)  # Enable Y-axis auto-scaling

        # Generate HTML content with Plotly's JavaScript included
        html_content = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        self.plot_view.setHtml(html_content)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InvestmentToolApp()
    window.show()
    sys.exit(app.exec_())
