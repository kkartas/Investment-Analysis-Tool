# models/dividends.py

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def get_dividend_history(ticker_symbol, period="5y"):
    """
    Get dividend history for a stock.
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
        period (str): Period to fetch data for (1m, 3m, 6m, 1y, 2y, 5y, 10y, max)
    
    Returns:
        dict: Dividend history data and statistics
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get dividend data
        dividends = ticker.dividends
        
        if dividends.empty:
            return {
                "has_dividends": False,
                "message": "No dividend history found for this stock."
            }
        
        # Get info for additional metrics
        info = ticker.info
        
        # Convert Series to DataFrame with date index
        df = dividends.reset_index()
        df.columns = ['Date', 'Dividend']
        
        # Filter by period if specified
        if period != "max":
            # Calculate start date based on period
            end_date = datetime.now()
            
            if period == "1m":
                start_date = end_date - timedelta(days=30)
            elif period == "3m":
                start_date = end_date - timedelta(days=90)
            elif period == "6m":
                start_date = end_date - timedelta(days=180)
            elif period == "1y":
                start_date = end_date - timedelta(days=365)
            elif period == "2y":
                start_date = end_date - timedelta(days=730)
            elif period == "5y":
                start_date = end_date - timedelta(days=1825)
            elif period == "10y":
                start_date = end_date - timedelta(days=3650)
                
            df = df[df['Date'] >= pd.Timestamp(start_date)]
        
        if df.empty:
            return {
                "has_dividends": False,
                "message": f"No dividend history found for this stock in the selected period ({period})."
            }
        
        # Create chart data
        chart_data = {
            'dates': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'dividends': df['Dividend'].tolist()
        }
        
        # Calculate dividend statistics
        current_dividend = df['Dividend'].iloc[-1] if not df.empty else 0
        
        # Calculate annual dividend (sum of last 4 quarters or 12 months)
        recent_year = df[df['Date'] >= (datetime.now() - timedelta(days=365))]
        annual_dividend = recent_year['Dividend'].sum()
        
        # If no dividends in the last year but has historical dividends
        if annual_dividend == 0 and not df.empty:
            # Try to extrapolate from the most recent dividends
            most_recent = df.iloc[-4:] if len(df) >= 4 else df
            annual_dividend = most_recent['Dividend'].sum() * (4 / len(most_recent))
        
        # Get current price from info
        current_price = info.get('currentPrice', 0)
        
        # Calculate dividend yield
        dividend_yield = (annual_dividend / current_price * 100) if current_price > 0 else 0
        
        # Calculate dividend growth
        if len(df) >= 8:  # Need at least 2 years of quarterly dividends
            # Get first and last year's dividends
            recent_dividends = df.iloc[-4:]['Dividend'].sum()
            previous_dividends = df.iloc[-8:-4]['Dividend'].sum()
            
            dividend_growth = ((recent_dividends / previous_dividends) - 1) * 100 if previous_dividends > 0 else 0
        else:
            dividend_growth = 0
        
        # Get payment frequency
        if len(df) >= 2:
            # Calculate average days between payments
            df['NextDate'] = df['Date'].shift(-1)
            df = df[:-1]  # Remove last row which has NaN for NextDate
            df['Days'] = (df['Date'] - df['NextDate']).abs().dt.days
            
            avg_days = df['Days'].mean()
            
            if avg_days <= 35:
                frequency = "Monthly"
            elif avg_days <= 70:
                frequency = "Bi-Monthly"
            elif avg_days <= 100:
                frequency = "Quarterly"
            elif avg_days <= 190:
                frequency = "Semi-Annually"
            else:
                frequency = "Annually"
        else:
            frequency = "Unknown"
        
        # Get ex-dividend date and payment date if available
        ex_dividend_date = info.get('exDividendDate', None)
        if ex_dividend_date:
            ex_dividend_date = datetime.fromtimestamp(ex_dividend_date).strftime('%Y-%m-%d')
        
        # Calculate dividend metrics
        payout_ratio = info.get('payoutRatio', 0) * 100  # Convert to percentage
        
        # Calculate years of dividend growth if possible
        years_data = df.copy()
        years_data['Year'] = years_data['Date'].dt.year
        annual_sums = years_data.groupby('Year')['Dividend'].sum()
        
        years_of_growth = 0
        if len(annual_sums) >= 2:
            for i in range(1, len(annual_sums)):
                if annual_sums.iloc[i] > annual_sums.iloc[i-1]:
                    years_of_growth += 1
                else:
                    break
        
        # Format table data
        table_data = []
        for _, row in df.iterrows():
            table_data.append({
                'date': row['Date'].strftime('%Y-%m-%d'),
                'amount': round(row['Dividend'], 4)
            })
            
        # Sort in reverse chronological order
        table_data.reverse()
        
        result = {
            "has_dividends": True,
            "chart_data": chart_data,
            "table_data": table_data,
            "stats": {
                "current_dividend": round(current_dividend, 4),
                "annual_dividend": round(annual_dividend, 4),
                "dividend_yield": round(dividend_yield, 2),
                "dividend_growth": round(dividend_growth, 2),
                "frequency": frequency,
                "ex_dividend_date": ex_dividend_date,
                "payout_ratio": round(payout_ratio, 2),
                "years_of_growth": years_of_growth
            }
        }
        
        return result
        
    except Exception as e:
        print(f"Error getting dividend history for {ticker_symbol}: {e}")
        return {
            "has_dividends": False,
            "message": f"Error retrieving dividend data: {str(e)}"
        }

def calculate_dividend_growth_metrics(ticker_symbol):
    """
    Calculate dividend growth metrics including:
    - 1-year, 3-year, 5-year, and 10-year dividend growth rates
    - Dividend streak (consecutive years of dividend increases)
    - Dividend safety score
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
    
    Returns:
        dict: Dividend growth metrics
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get dividend data
        dividends = ticker.dividends
        
        if dividends.empty:
            return {
                "has_metrics": False,
                "message": "No dividend history found for this stock."
            }
        
        # Convert Series to DataFrame with date index
        df = dividends.reset_index()
        df.columns = ['Date', 'Dividend']
        
        # Group by year to calculate annual dividend
        df['Year'] = df['Date'].dt.year
        annual_dividends = df.groupby('Year')['Dividend'].sum()
        
        # Calculate growth rates
        growth_rates = {}
        current_year = datetime.now().year
        
        # Calculate 1-year growth rate
        if current_year - 1 in annual_dividends.index and current_year - 2 in annual_dividends.index:
            growth_rates['1yr'] = ((annual_dividends[current_year - 1] / annual_dividends[current_year - 2]) - 1) * 100
        else:
            growth_rates['1yr'] = None
            
        # Calculate 3-year CAGR
        if current_year - 1 in annual_dividends.index and current_year - 4 in annual_dividends.index:
            growth_rates['3yr'] = (pow(annual_dividends[current_year - 1] / annual_dividends[current_year - 4], 1/3) - 1) * 100
        else:
            growth_rates['3yr'] = None
            
        # Calculate 5-year CAGR
        if current_year - 1 in annual_dividends.index and current_year - 6 in annual_dividends.index:
            growth_rates['5yr'] = (pow(annual_dividends[current_year - 1] / annual_dividends[current_year - 6], 1/5) - 1) * 100
        else:
            growth_rates['5yr'] = None
            
        # Calculate 10-year CAGR
        if current_year - 1 in annual_dividends.index and current_year - 11 in annual_dividends.index:
            growth_rates['10yr'] = (pow(annual_dividends[current_year - 1] / annual_dividends[current_year - 11], 1/10) - 1) * 100
        else:
            growth_rates['10yr'] = None
        
        # Calculate dividend streak
        streak = 0
        years = sorted(annual_dividends.index, reverse=True)
        
        for i in range(len(years) - 1):
            if annual_dividends[years[i]] > annual_dividends[years[i+1]]:
                streak += 1
            else:
                break
                
        # Get additional data for safety score
        info = ticker.info
        payout_ratio = info.get('payoutRatio', 0) * 100  # Convert to percentage
        
        # Calculate dividend safety score (0-100)
        safety_score = 50  # Start with neutral score
        
        # Factors that increase safety:
        # 1. Low payout ratio
        if payout_ratio < 30:
            safety_score += 15
        elif payout_ratio < 50:
            safety_score += 10
        elif payout_ratio < 70:
            safety_score += 5
        elif payout_ratio > 90:
            safety_score -= 15
            
        # 2. Dividend streak
        if streak >= 25:
            safety_score += 20
        elif streak >= 10:
            safety_score += 15
        elif streak >= 5:
            safety_score += 10
        
        # 3. Consistent growth
        if growth_rates['5yr'] and growth_rates['5yr'] > 0:
            safety_score += 10
            
        # Cap score at 100
        safety_score = min(100, max(0, safety_score))
        
        return {
            "has_metrics": True,
            "growth_rates": {
                "1yr": round(growth_rates['1yr'], 2) if growth_rates['1yr'] is not None else None,
                "3yr": round(growth_rates['3yr'], 2) if growth_rates['3yr'] is not None else None,
                "5yr": round(growth_rates['5yr'], 2) if growth_rates['5yr'] is not None else None,
                "10yr": round(growth_rates['10yr'], 2) if growth_rates['10yr'] is not None else None
            },
            "streak": streak,
            "safety_score": safety_score
        }
        
    except Exception as e:
        print(f"Error calculating dividend growth metrics for {ticker_symbol}: {e}")
        return {
            "has_metrics": False,
            "message": f"Error calculating dividend metrics: {str(e)}"
        } 