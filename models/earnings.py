# models/earnings.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

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

def get_earnings_surprises_with_price_reaction(symbol, max_quarters=8):
    """
    Get detailed earnings surprise data with price reactions around earnings announcements.
    
    Parameters:
        symbol (str): Stock ticker symbol
        max_quarters (int): Maximum number of quarters to return
        
    Returns:
        dict: Dictionary containing earnings surprise data and price reactions
    """
    try:
        # Get basic earnings data
        basic_earnings = get_earnings(symbol)
        
        if not basic_earnings:
            return {
                "success": False,
                "message": "No earnings data found"
            }
            
        # Get historical price data (we'll need enough history)
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="5y")  # 5 years should cover most earnings history
        
        if history.empty:
            return {
                "success": False,
                "message": "No historical price data found"
            }
            
        # List to hold our enhanced earnings data
        enhanced_earnings = []
        
        for earning in basic_earnings:
            if len(enhanced_earnings) >= max_quarters:
                break
                
            # Skip future earnings (no price reaction yet)
            if "Upcoming" in earning.get('quarter', ''):
                enhanced_earnings.append(earning)
                continue
                
            try:
                # Convert date string to datetime
                earnings_date = datetime.strptime(earning['date'], '%d/%m/%Y').date()
                
                # Find price reactions for this earnings date
                price_reaction = calculate_price_reaction(history, earnings_date)
                
                if price_reaction:
                    # Add price reaction data to the earnings data
                    enhanced_earning = earning.copy()
                    enhanced_earning.update(price_reaction)
                    enhanced_earnings.append(enhanced_earning)
                else:
                    # No price reaction data, just add the original earnings data
                    enhanced_earnings.append(earning)
                    
            except Exception as e:
                print(f"Error calculating price reaction for {earnings_date}: {e}")
                enhanced_earnings.append(earning)
        
        # Prepare the data for visualization
        chart_data = prepare_earnings_chart_data(enhanced_earnings)
        
        return {
            "success": True,
            "earnings_data": enhanced_earnings,
            "chart_data": chart_data
        }
        
    except Exception as e:
        print(f"Error in get_earnings_surprises_with_price_reaction: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def calculate_price_reaction(price_history, earnings_date):
    """
    Calculate stock price reaction around an earnings announcement
    
    Parameters:
        price_history (pd.DataFrame): Historical price data
        earnings_date (datetime.date): Date of earnings announcement
        
    Returns:
        dict: Dictionary containing price reaction data
    """
    try:
        # Convert earnings_date to the same format as price_history index
        earnings_datetime = pd.Timestamp(earnings_date)
        
        # Get 10 days before and after earnings
        before_days = 10
        after_days = 10
        
        # Find the closest trading day to earnings_date
        # Most earnings releases are after market close, so next day often has bigger reaction
        closest_idx = None
        min_distance = float('inf')
        
        for idx, date in enumerate(price_history.index):
            distance = abs((date - earnings_datetime).days)
            if distance < min_distance:
                min_distance = distance
                closest_idx = idx
                
        if closest_idx is None or min_distance > 5:  # If more than 5 days off, probably missing the data
            return None
            
        # The earnings date in trading days
        earnings_idx = closest_idx
        
        # Get prices around earnings
        start_idx = max(0, earnings_idx - before_days)
        end_idx = min(len(price_history) - 1, earnings_idx + after_days)
        
        if start_idx >= end_idx:
            return None
            
        # Get price data
        earnings_window = price_history.iloc[start_idx:end_idx + 1]
        
        if earnings_window.empty:
            return None
            
        # Calculate returns
        earnings_prices = earnings_window['Close'].to_dict()
        
        # Base price (day before earnings or closest available)
        base_date = price_history.index[earnings_idx - 1] if earnings_idx > 0 else price_history.index[earnings_idx]
        base_price = price_history.loc[base_date, 'Close']
        
        # Get reaction on day of/after earnings (assuming after-hours announcement)
        # and following days
        day_of_earnings = price_history.index[earnings_idx]
        day_after_earnings = price_history.index[earnings_idx + 1] if earnings_idx + 1 < len(price_history) else day_of_earnings
        
        day_of_price = price_history.loc[day_of_earnings, 'Close']
        day_after_price = price_history.loc[day_after_earnings, 'Close'] if day_after_earnings != day_of_earnings else day_of_price
        
        # Calculate percentage changes
        day_of_change = ((day_of_price / base_price) - 1) * 100
        day_after_change = ((day_after_price / base_price) - 1) * 100
        
        # Calculate 5-day and 10-day changes
        idx_5day = min(earnings_idx + 5, len(price_history) - 1)
        idx_10day = min(earnings_idx + 10, len(price_history) - 1)
        
        day_5_price = price_history.iloc[idx_5day]['Close']
        day_10_price = price_history.iloc[idx_10day]['Close']
        
        day_5_change = ((day_5_price / base_price) - 1) * 100
        day_10_change = ((day_10_price / base_price) - 1) * 100
        
        # Format dates as strings for response
        base_date_str = base_date.strftime('%Y-%m-%d')
        earnings_date_str = day_of_earnings.strftime('%Y-%m-%d')
        
        # Format price timeseries for chart (convert to relative change from base price)
        price_change_series = {}
        day_count = 0
        
        for date, price in earnings_prices.items():
            # Calculate days relative to earnings announcement (-10 to +10)
            days_from_earnings = (date - price_history.index[earnings_idx]).days
            
            # Calculate percentage change from base price
            pct_change = ((price / base_price) - 1) * 100
            
            # Store with relative day as key
            price_change_series[days_from_earnings] = round(pct_change, 2)
            
        return {
            "reaction_data": {
                "base_date": base_date_str,
                "earnings_date": earnings_date_str,
                "day_of_change": round(day_of_change, 2),
                "day_after_change": round(day_after_change, 2),
                "day_5_change": round(day_5_change, 2),
                "day_10_change": round(day_10_change, 2)
            },
            "price_change_series": price_change_series
        }
        
    except Exception as e:
        print(f"Error calculating price reaction: {e}")
        return None

def prepare_earnings_chart_data(earnings_data):
    """
    Prepare earnings data for visualization
    
    Parameters:
        earnings_data (list): List of earnings data dictionaries
        
    Returns:
        dict: Formatted data for charts
    """
    # Reverse list to have oldest first (for chart display)
    earnings_data_reversed = list(reversed(earnings_data))
    
    # Extract data for charts
    quarters = []
    surprises = []
    actuals = []
    estimates = []
    day_after_changes = []
    day_5_changes = []
    
    for entry in earnings_data_reversed:
        # Get quarter name
        quarters.append(entry.get('quarter', 'N/A'))
        
        # Get EPS data
        estimates.append(entry.get('eps_estimate'))
        actuals.append(entry.get('eps_actual'))
        
        # Get surprise percentage
        surprises.append(entry.get('surprise', 0))
        
        # Get price reaction data if available
        reaction_data = entry.get('reaction_data', {})
        day_after_changes.append(reaction_data.get('day_after_change'))
        day_5_changes.append(reaction_data.get('day_5_change'))
    
    # Prepare combined chart data
    chart_data = {
        "quarters": quarters,
        "eps_data": {
            "estimates": estimates,
            "actuals": actuals,
            "surprises": surprises
        },
        "price_reaction": {
            "day_after": day_after_changes,
            "day_5": day_5_changes
        }
    }
    
    # Prepare price reaction time series data (if available)
    price_series_data = {}
    days = list(range(-10, 11))  # -10 to +10 days
    
    for i, entry in enumerate(earnings_data_reversed):
        if 'price_change_series' in entry:
            series = []
            for day in days:
                series.append(entry['price_change_series'].get(day, None))
            
            price_series_data[quarters[i]] = series
    
    if price_series_data:
        chart_data["price_series"] = {
            "days": days,
            "series_data": price_series_data
        }
    
    return chart_data

def get_earnings_trend(symbol, years=3):
    """
    Analyze the earnings growth trend over time.
    
    Parameters:
        symbol (str): Stock ticker symbol
        years (int): Number of years to analyze
        
    Returns:
        dict: Dictionary containing earnings trend analysis
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Get quarterly earnings data
        earnings = ticker.quarterly_earnings
        
        if earnings is None or earnings.empty:
            return {
                "success": False,
                "message": "No quarterly earnings data found"
            }
            
        # Create a DataFrame from the earnings data
        df = earnings.reset_index()
        df.columns = ['Quarter', 'Revenue', 'Earnings']
        
        # Sort by quarter (oldest first)
        df = df.sort_values('Quarter')
        
        # Limit to the specified number of years (4 quarters per year)
        max_quarters = years * 4
        if len(df) > max_quarters:
            df = df.tail(max_quarters)
            
        # Calculate quarter-over-quarter growth rates
        df['Revenue_QoQ'] = df['Revenue'].pct_change() * 100
        df['Earnings_QoQ'] = df['Earnings'].pct_change() * 100
        
        # Calculate year-over-year growth rates (comparing with same quarter previous year)
        if len(df) >= 4:
            df['Revenue_YoY'] = (df['Revenue'] / df['Revenue'].shift(4) - 1) * 100
            df['Earnings_YoY'] = (df['Earnings'] / df['Earnings'].shift(4) - 1) * 100
            
        # Calculate trailing twelve months (TTM) values
        df['Revenue_TTM'] = df['Revenue'].rolling(4).sum()
        df['Earnings_TTM'] = df['Earnings'].rolling(4).sum()
        
        # Calculate TTM growth rates
        df['Revenue_TTM_YoY'] = (df['Revenue_TTM'] / df['Revenue_TTM'].shift(4) - 1) * 100 if len(df) >= 8 else None
        df['Earnings_TTM_YoY'] = (df['Earnings_TTM'] / df['Earnings_TTM'].shift(4) - 1) * 100 if len(df) >= 8 else None
        
        # Format data for charts
        quarters = [str(q) for q in df['Quarter'].tolist()]
        
        chart_data = {
            "quarters": quarters,
            "revenue": df['Revenue'].tolist(),
            "earnings": df['Earnings'].tolist(),
            "revenue_qoq": df['Revenue_QoQ'].tolist(),
            "earnings_qoq": df['Earnings_QoQ'].tolist()
        }
        
        # Add YoY data if available
        if 'Revenue_YoY' in df.columns:
            chart_data["revenue_yoy"] = df['Revenue_YoY'].tolist()
            chart_data["earnings_yoy"] = df['Earnings_YoY'].tolist()
            
        # Add TTM data
        chart_data["revenue_ttm"] = df['Revenue_TTM'].tolist()
        chart_data["earnings_ttm"] = df['Earnings_TTM'].tolist()
        
        # Add TTM YoY growth if available
        if 'Revenue_TTM_YoY' in df.columns:
            chart_data["revenue_ttm_yoy"] = df['Revenue_TTM_YoY'].tolist()
            chart_data["earnings_ttm_yoy"] = df['Earnings_TTM_YoY'].tolist()
            
        # Calculate average growth rates
        avg_earnings_qoq = df['Earnings_QoQ'].mean() if not df['Earnings_QoQ'].isnull().all() else None
        avg_revenue_qoq = df['Revenue_QoQ'].mean() if not df['Revenue_QoQ'].isnull().all() else None
        
        avg_earnings_yoy = df['Earnings_YoY'].mean() if 'Earnings_YoY' in df.columns and not df['Earnings_YoY'].isnull().all() else None
        avg_revenue_yoy = df['Revenue_YoY'].mean() if 'Revenue_YoY' in df.columns and not df['Revenue_YoY'].isnull().all() else None
        
        # Analyze earnings consistency
        beats = 0
        misses = 0
        
        # Get earnings surprise data
        surprise_data = get_earnings(symbol)
        
        for item in surprise_data:
            if item.get('surprise') is not None:
                if item['surprise'] > 0:
                    beats += 1
                elif item['surprise'] < 0:
                    misses += 1
                    
        total_reports = beats + misses
        beat_rate = (beats / total_reports * 100) if total_reports > 0 else 0
        
        return {
            "success": True,
            "chart_data": chart_data,
            "summary": {
                "avg_earnings_qoq": round(avg_earnings_qoq, 2) if avg_earnings_qoq is not None else None,
                "avg_revenue_qoq": round(avg_revenue_qoq, 2) if avg_revenue_qoq is not None else None,
                "avg_earnings_yoy": round(avg_earnings_yoy, 2) if avg_earnings_yoy is not None else None,
                "avg_revenue_yoy": round(avg_revenue_yoy, 2) if avg_revenue_yoy is not None else None,
                "consistency": {
                    "beats": beats,
                    "misses": misses,
                    "beat_rate": round(beat_rate, 2)
                }
            }
        }
        
    except Exception as e:
        print(f"Error analyzing earnings trend: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }
