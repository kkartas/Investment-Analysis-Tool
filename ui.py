import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import yfinance as yf

from dca_calculations import dca_calculation, calculate_average_interest
from stock_analysis import calculate_indicators, get_latest_recommendation

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse and touchpad scrolling
        self.scrollable_frame.bind("<Enter>", self._bind_mouse_wheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mouse_wheel)

    def _bind_mouse_wheel(self, event):
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.bind_all("<Button-4>", self._on_mouse_wheel)  # For Linux
        self.bind_all("<Button-5>", self._on_mouse_wheel)  # For Linux

    def _unbind_mouse_wheel(self, event):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")  # For Linux
        self.unbind_all("<Button-5>")  # For Linux

    def _on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.yview_scroll(-1, "units")

class InvestmentToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Investment Tool")
        self.root.state('zoomed')  # Open in full screen
        self.data = None
        self.use_custom_interest = False

        self.create_widgets()

    def create_widgets(self):
        self.frame = ScrollableFrame(self.root)
        self.frame.pack(fill="both", expand=True)

        # Radio buttons for choosing data source
        self.data_source_var = tk.StringVar(value='yfinance')
        self.yfinance_radio = ttk.Radiobutton(self.frame.scrollable_frame, text="Fetch from yfinance", variable=self.data_source_var, value='yfinance')
        self.yfinance_radio.grid(row=0, column=0, pady=10, sticky=tk.W)
        self.csv_radio = ttk.Radiobutton(self.frame.scrollable_frame, text="Load CSV File", variable=self.data_source_var, value='csv')
        self.csv_radio.grid(row=1, column=0, pady=10, sticky=tk.W)

        self.stock_symbol_label = ttk.Label(self.frame.scrollable_frame, text="Stock Symbol (if using yfinance):")
        self.stock_symbol_label.grid(row=2, column=0, pady=5, sticky=tk.W)
        self.stock_symbol_entry = ttk.Entry(self.frame.scrollable_frame)
        self.stock_symbol_entry.grid(row=2, column=1, pady=5)

        self.load_button = ttk.Button(self.frame.scrollable_frame, text="Load Data", command=self.load_data)
        self.load_button.grid(row=3, column=0, pady=10)

        self.analysis_button = ttk.Button(self.frame.scrollable_frame, text="Run Stock Analysis", command=self.run_stock_analysis, state=tk.DISABLED)
        self.analysis_button.grid(row=4, column=0, pady=10)

        self.savings_plan_var = tk.BooleanVar()
        self.savings_plan_checkbox = ttk.Checkbutton(self.frame.scrollable_frame, text="Create a Savings Plan", variable=self.savings_plan_var, command=self.toggle_dca_options)
        self.savings_plan_checkbox.grid(row=5, column=0, pady=10)
        self.savings_plan_checkbox.config(state=tk.NORMAL)  # Always enabled

        self.dca_frame = ttk.LabelFrame(self.frame.scrollable_frame, text="DCA Savings Plan Options", padding="10")
        self.dca_frame.grid(row=6, column=0, pady=10, sticky=(tk.W, tk.E))
        self.dca_frame.grid_remove()  # Initially hide the DCA options

        self.initial_label = ttk.Label(self.dca_frame, text="Initial Investment:")
        self.initial_label.grid(row=0, column=0, pady=5, sticky=tk.W)
        self.initial_entry = ttk.Entry(self.dca_frame)
        self.initial_entry.grid(row=0, column=1, pady=5)

        self.periodic_label = ttk.Label(self.dca_frame, text="Periodic Investment:")
        self.periodic_label.grid(row=1, column=0, pady=5, sticky=tk.W)
        self.periodic_entry = ttk.Entry(self.dca_frame)
        self.periodic_entry.grid(row=1, column=1, pady=5)

        self.period_label = ttk.Label(self.dca_frame, text="Investment Period:")
        self.period_label.grid(row=2, column=0, pady=5, sticky=tk.W)
        self.period_var = tk.StringVar(value='daily')
        self.daily_radio = ttk.Radiobutton(self.dca_frame, text="Daily", variable=self.period_var, value='daily')
        self.daily_radio.grid(row=2, column=1, pady=5, sticky=tk.W)
        self.monthly_radio = ttk.Radiobutton(self.dca_frame, text="Monthly", variable=self.period_var, value='monthly')
        self.monthly_radio.grid(row=2, column=2, pady=5, sticky=tk.W)
        self.yearly_radio = ttk.Radiobutton(self.dca_frame, text="Yearly", variable=self.period_var, value='yearly')
        self.yearly_radio.grid(row=2, column=3, pady=5, sticky=tk.W)

        self.total_years_label = ttk.Label(self.dca_frame, text="Total Years:")
        self.total_years_label.grid(row=3, column=0, pady=5, sticky=tk.W)
        self.total_years_entry = ttk.Entry(self.dca_frame)
        self.total_years_entry.grid(row=3, column=1, pady=5)

        self.custom_interest_var = tk.BooleanVar()
        self.custom_interest_checkbox = ttk.Checkbutton(self.dca_frame, text="Use Custom Annual Interest Rate", variable=self.custom_interest_var, command=self.toggle_custom_interest)
        self.custom_interest_checkbox.grid(row=4, column=0, pady=10, sticky=tk.W)

        self.custom_interest_frame = ttk.LabelFrame(self.dca_frame, text="Custom Interest Rate", padding="10")
        self.custom_interest_frame.grid(row=5, column=0, pady=10, sticky=(tk.W, tk.E))
        self.custom_interest_frame.grid_remove()  # Initially hide the custom interest options

        self.custom_interest_label = ttk.Label(self.custom_interest_frame, text="Annual Interest Rate (%):")
        self.custom_interest_label.grid(row=0, column=0, pady=5, sticky=tk.W)
        self.custom_interest_entry = ttk.Entry(self.custom_interest_frame)
        self.custom_interest_entry.grid(row=0, column=1, pady=5)

        self.reinvest_var = tk.BooleanVar(value=True)
        self.reinvest_checkbox = ttk.Checkbutton(self.dca_frame, text="Reinvest Interest Profit", variable=self.reinvest_var)
        self.reinvest_checkbox.grid(row=6, column=0, pady=10, sticky=tk.W)
        self.reinvest_checkbox.grid_remove()  # Hide initially, shown only if custom interest rate is used

        self.calculate_button = ttk.Button(self.dca_frame, text="Calculate Savings Plan", command=self.run_dca)
        self.calculate_button.grid(row=7, column=0, columnspan=2, pady=10)

        self.result_frame = ttk.LabelFrame(self.frame.scrollable_frame, text="Results", padding="10")
        self.result_frame.grid(row=8, column=0, pady=10, sticky=(tk.W, tk.E))

        self.result_text = tk.Text(self.result_frame, height=15, width=80, state=tk.DISABLED, font=("Helvetica", 12))
        self.result_text.pack(pady=10)

        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, self.result_frame)
        self.canvas.get_tk_widget().pack()

        # Clear All Button
        self.clear_button = ttk.Button(self.frame.scrollable_frame, text="Clear All", command=self.clear_all)
        self.clear_button.grid(row=9, column=0, pady=10, sticky=tk.E)

    def toggle_custom_interest(self):
        if self.custom_interest_var.get():
            self.custom_interest_frame.grid()  # Show the custom interest options
            self.reinvest_checkbox.grid()  # Show the reinvest checkbox
        else:
            self.custom_interest_frame.grid_remove()  # Hide the custom interest options
            self.reinvest_checkbox.grid_remove()  # Hide the reinvest checkbox

    def load_data(self):
        data_source = self.data_source_var.get()
        if data_source == 'yfinance':
            stock_symbol = self.stock_symbol_entry.get()
            if not stock_symbol:
                messagebox.showerror("Error", "Please enter a stock symbol.")
                return
            self.data = self.fetch_yfinance_data(stock_symbol)
        elif data_source == 'csv':
            self.load_file()

        if self.data is not None:
            messagebox.showinfo("Data Loaded", "Data loaded successfully!")
            self.analysis_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", "Failed to load data. Please try again.")

    def fetch_yfinance_data(self, symbol):
        try:
            data = yf.download(symbol, start="2000-01-01")
            if data.empty:
                messagebox.showerror("Error", "No data found for the symbol provided.")
                return None
            data.reset_index(inplace=True)
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
            return data
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data from yfinance: {e}")
            return None

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.data = pd.read_csv(file_path)

            # Ensure the Date column is parsed and set as the index
            self.data['Date'] = pd.to_datetime(self.data['Date'])
            self.data.set_index('Date', inplace=True)

    def run_stock_analysis(self):
        if self.data is not None:
            calculate_indicators(self.data)
            self.display_analysis_results()
        else:
            messagebox.showerror("Error", "No data loaded. Please load a CSV file first.")

    def display_analysis_results(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)

        latest_data, recommendation = get_latest_recommendation(self.data)

        result_text = (
            f"Latest Close: {latest_data['Close']:.2f}\n"
            f"50-day SMA: {latest_data['SMA_50']:.2f}\n"
            f"200-day SMA: {latest_data['SMA_200']:.2f}\n"
            f"RSI: {latest_data['RSI']:.2f}\n"
            f"MACD: {latest_data['MACD']:.2f}\n"
            f"Signal Line: {latest_data['Signal_Line']:.2f}\n"
            f"Recommendation: {recommendation}"
        )
        
        self.result_text.insert(tk.END, result_text)
        self.result_text.config(state=tk.DISABLED)

        self.plot_analysis()

    def plot_analysis(self):
        self.figure.clear()

        filtered_data = self.data.dropna(subset=['SMA_50', 'SMA_200', 'RSI', 'MACD', 'Signal_Line'])
        ax1, ax2, ax3 = self.figure.subplots(3, 1, sharex=True)

        ax1.plot(filtered_data.index, filtered_data['Close'], label='Close Price')
        ax1.plot(filtered_data.index, filtered_data['SMA_50'], label='50-day SMA', linestyle='--')
        ax1.plot(filtered_data.index, filtered_data['SMA_200'], label='200-day SMA', linestyle='--')
        ax1.set_title('Price and Moving Averages')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)

        ax2.plot(filtered_data.index, filtered_data['RSI'], label='RSI')
        ax2.axhline(70, color='red', linestyle='--')
        ax2.axhline(30, color='green', linestyle='--')
        ax2.set_title('Relative Strength Index (RSI)')
        ax2.set_ylabel('RSI')
        ax2.legend()
        ax2.grid(True)

        ax3.plot(filtered_data.index, filtered_data['MACD'], label='MACD')
        ax3.plot(filtered_data.index, filtered_data['Signal_Line'], label='Signal Line', linestyle='--')
        ax3.set_title('MACD and Signal Line')
        ax3.set_ylabel('MACD')
        ax3.legend()
        ax3.grid(True)

        self.canvas.draw()

    def toggle_dca_options(self):
        if self.savings_plan_var.get():
            self.dca_frame.grid()  # Show the DCA options
            if self.data is not None:
                average_interest = calculate_average_interest(self.data)
                messagebox.showinfo("Average Annual Interest", f"The average annual interest calculated from the data is {average_interest:.2%}.")
                self.custom_interest_entry.delete(0, tk.END)
                self.custom_interest_entry.insert(0, f"{average_interest * 100:.2f}")
                self.custom_interest_checkbox.config(state=tk.DISABLED)
                self.reinvest_checkbox.grid_remove()  # Hide reinvest checkbox when using calculated interest
            else:
                self.custom_interest_checkbox.config(state=tk.NORMAL)
        else:
            self.dca_frame.grid_remove()  # Hide the DCA options

    def run_dca(self):
        if self.custom_interest_var.get():
            try:
                custom_interest_rate = float(self.custom_interest_entry.get()) / 100
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid numeric interest rate.")
                return
            reinvest = self.reinvest_var.get()
        elif self.data is not None:
            custom_interest_rate = calculate_average_interest(self.data)
            reinvest = True  # Automatically reinvest when using calculated interest
        else:
            messagebox.showerror("Error", "No data loaded or custom interest rate provided.")
            return

        try:
            initial_investment = float(self.initial_entry.get())
            periodic_investment = float(self.periodic_entry.get())
            period = self.period_var.get()
            years = int(self.total_years_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for investments.")
            return

        total_invested, future_value, total_profit, _, _, future_values, invested_values = dca_calculation(
            self.data if self.data is not None else pd.DataFrame(), 
            initial_investment, 
            periodic_investment, 
            period, 
            years, 
            average_interest=custom_interest_rate, 
            reinvest=reinvest
        )

        self.display_dca_results(total_invested, future_value, total_profit)
        self.plot_dca_results(future_values, invested_values, years)

    def display_dca_results(self, total_invested, future_value, total_profit):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, f"\n\nDCA Savings Plan:\n")
        result_text = (
            f"Total Invested: ${total_invested:,.2f}\n"
            f"Future Value: ${future_value:,.2f}\n"
            f"Total Profit: ${total_profit:,.2f}\n"
        )
        self.result_text.insert(tk.END, result_text)
        self.result_text.config(state=tk.DISABLED)

    def plot_dca_results(self, future_values, invested_values, years):
        total_periods = len(future_values) - 1
        years_labels = np.linspace(0, years, num=total_periods + 1)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(years_labels, future_values, label='Future Value')
        ax.plot(years_labels, invested_values, label='Total Invested', linestyle='--')
        ax.set_title('DCA Investment Growth')
        ax.set_xlabel('Years')
        ax.set_ylabel('Money ($)')
        ax.legend()
        ax.grid(True)
        self.canvas.draw()

    def clear_all(self):
        self.data = None
        self.analysis_button.config(state=tk.DISABLED)
        self.initial_entry.delete(0, tk.END)
        self.periodic_entry.delete(0, tk.END)
        self.total_years_entry.delete(0, tk.END)
        self.custom_interest_entry.delete(0, tk.END)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.figure.clear()
        self.canvas.draw()
        self.custom_interest_checkbox.config(state=tk.NORMAL)
        self.reinvest_checkbox.grid_remove()  # Hide the reinvest checkbox

if __name__ == "__main__":
    root = tk.Tk()
    app = InvestmentToolApp(root)
    root.mainloop()
