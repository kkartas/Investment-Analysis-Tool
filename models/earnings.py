# models/earnings.py

import yfinance as yf
import pandas as pd
from datetime import datetime, date

def get_earnings(symbol):
    """
    Fetches earnings data for a given stock symbol
    Returns a list of dictionaries with keys: quarter, date, eps_estimate, eps_actual, surprise
    """
    try:
        ticker = yf.Ticker(symbol)
        results = []
        today = date.today()
        
        # Try to get earnings dates data first (most detailed)
        try:
            earnings_dates = ticker.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                for index, row in earnings_dates.iterrows():
                    # Format the date as DD/MM/YYYY
                    date_str = index.strftime('%d/%m/%Y') if not pd.isna(index) else 'N/A'
                    
                    # Build quarter string based on date
                    quarter_str = 'Q' + str((index.month-1)//3 + 1) + ' ' + str(index.year)
                    
                    # Check if this is a future earnings date
                    is_future = False
                    if not pd.isna(index):
                        earnings_date = index.date()
                        is_future = earnings_date >= today
                        if is_future:
                            quarter_str = f'Upcoming: {quarter_str}'
                    
                    # Extract EPS data
                    eps_estimate = None if pd.isna(row.get('EPS Estimate', None)) else round(float(row['EPS Estimate']), 2)
                    eps_actual = None if pd.isna(row.get('Reported EPS', None)) else round(float(row['Reported EPS']), 2)
                    
                    # If future date, we expect actual to be None
                    if is_future:
                        eps_actual = None
                    
                    # Calculate surprise percentage
                    surprise = None
                    if eps_estimate is not None and eps_actual is not None:
                        if eps_estimate != 0:
                            surprise = round(((eps_actual - eps_estimate) / abs(eps_estimate)) * 100, 2)
                        else:
                            surprise = 0 if eps_actual == 0 else 100
                    
                    results.append({
                        'quarter': quarter_str,
                        'date': date_str,
                        'eps_estimate': eps_estimate,
                        'eps_actual': eps_actual,
                        'surprise': surprise
                    })
        except Exception as e:
            print(f"Error fetching earnings dates: {e}")
        
        # If no earnings dates found, try basic earnings data
        if not results:
            try:
                earnings = ticker.earnings
                if earnings is not None and not earnings.empty:
                    for year, row in earnings.iterrows():
                        # Format year as a string
                        quarter_str = f'Q4 {year}'
                        date_str = f'31/12/{year}'  # Approximate date
                        
                        # Extract EPS
                        eps_actual = None if pd.isna(row.get('EPS', None)) else round(float(row['EPS']), 2)
                        
                        results.append({
                            'quarter': quarter_str,
                            'date': date_str,
                            'eps_estimate': None,
                            'eps_actual': eps_actual,
                            'surprise': None
                        })
            except Exception as e:
                print(f"Error fetching basic earnings: {e}")
        
        # Try to get next earnings date from calendar
        try:
            calendar = ticker.calendar
            if calendar is not None and not calendar.empty and 'Earnings Date' in calendar.columns:
                next_date = calendar['Earnings Date'].iloc[0]
                if not pd.isna(next_date):
                    # Check if this is a future date
                    earnings_date = next_date.date()
                    if earnings_date >= today:
                        # Format the date as DD/MM/YYYY
                        date_str = next_date.strftime('%d/%m/%Y')
                        
                        # Build quarter string based on date
                        quarter_str = f'Upcoming: Q{(next_date.month-1)//3 + 1} {next_date.year}'
                        
                        # Get EPS estimate if available
                        eps_estimate = None
                        if 'EPS Estimate' in calendar.columns and not pd.isna(calendar['EPS Estimate'].iloc[0]):
                            eps_estimate = round(float(calendar['EPS Estimate'].iloc[0]), 2)
                        
                        # Check if we already have this date in results
                        date_exists = False
                        for item in results:
                            try:
                                item_date = datetime.strptime(item['date'], '%d/%m/%Y').date()
                                if item_date == earnings_date:
                                    date_exists = True
                                    break
                            except:
                                pass
                        
                        if not date_exists:
                            results.append({
                                'quarter': quarter_str,
                                'date': date_str,
                                'eps_estimate': eps_estimate,
                                'eps_actual': None,
                                'surprise': None
                            })
        except Exception as e:
            print(f"Error fetching next earnings date: {e}")
        
        # Sort by date (most recent first)
        results.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y') if x['date'] != 'N/A' else datetime.min, reverse=True)
        
        return results
    except Exception as e:
        print(f"Error in get_earnings: {e}")
        return []
