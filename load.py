# load.py

import pandas as pd
import yfinance as yf
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def fetch_yfinance_data(symbol):
    try:
        data = yf.download(symbol, start="2000-01-01")
        if data.empty:
            QMessageBox.critical(None, "Data Error", f"No data found for symbol: {symbol}")
            return None
        data.reset_index(inplace=True)
        data['Date'] = pd.to_datetime(data['Date'])
        data.set_index('Date', inplace=True)
        return data
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to fetch data: {e}")
        return None

def load_file():
    file_dialog = QFileDialog()
    file_path, _ = file_dialog.getOpenFileName(None, "Select Data File", "", "CSV Files (*.csv)")
    if file_path:
        try:
            data = pd.read_csv(file_path)
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
            return data
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load file: {e}")
            return None
    else:
        return None
