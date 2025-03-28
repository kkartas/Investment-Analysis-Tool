# models/risk_assessment.py

import yfinance as yf
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta

def assess_risk(ticker_symbol, benchmark_ticker='^GSPC', period='1y'):
    """
    Assess the risk profile of a stock compared to a benchmark index.
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
        benchmark_ticker (str): Benchmark ticker symbol (default: S&P 500)
        period (str): Period to analyze (1m, 3m, 6m, 1y, 3y, 5y, 10y, max)
        
    Returns:
        dict: Risk assessment data
    """
    try:
        # Get historical data for the ticker and benchmark
        ticker = yf.Ticker(ticker_symbol)
        ticker_history = ticker.history(period=period)
        
        benchmark = yf.Ticker(benchmark_ticker)
        benchmark_history = benchmark.history(period=period)
        
        if ticker_history.empty or benchmark_history.empty:
            return {
                "success": False,
                "message": "Insufficient historical data"
            }
            
        # Ensure dates align
        common_dates = ticker_history.index.intersection(benchmark_history.index)
        ticker_history = ticker_history.loc[common_dates]
        benchmark_history = benchmark_history.loc[common_dates]
        
        if ticker_history.empty or benchmark_history.empty:
            return {
                "success": False,
                "message": "No common dates between ticker and benchmark"
            }
            
        # Calculate daily returns
        ticker_returns = ticker_history['Close'].pct_change().dropna()
        benchmark_returns = benchmark_history['Close'].pct_change().dropna()
        
        # Ensure returns align
        common_dates = ticker_returns.index.intersection(benchmark_returns.index)
        ticker_returns = ticker_returns.loc[common_dates]
        benchmark_returns = benchmark_returns.loc[common_dates]
        
        # Calculate risk metrics
        volatility = ticker_returns.std() * np.sqrt(252)  # Annualized volatility
        benchmark_volatility = benchmark_returns.std() * np.sqrt(252)
        
        # Calculate beta
        covariance = ticker_returns.cov(benchmark_returns)
        benchmark_variance = benchmark_returns.var()
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        
        # Calculate alpha (annualized)
        # Use Capital Asset Pricing Model: Alpha = Realized Return - [Risk-Free Rate + Beta * (Benchmark Return - Risk-Free Rate)]
        risk_free_rate = 0.02  # Assumption: 2% risk-free rate
        daily_risk_free = risk_free_rate / 252
        
        ticker_mean_return = ticker_returns.mean()
        benchmark_mean_return = benchmark_returns.mean()
        
        expected_return = daily_risk_free + beta * (benchmark_mean_return - daily_risk_free)
        alpha = (ticker_mean_return - expected_return) * 252  # Annualized alpha
        
        # Calculate Sharpe Ratio
        sharpe_ratio = (ticker_returns.mean() - daily_risk_free) / ticker_returns.std() * np.sqrt(252)
        
        # Calculate Sortino Ratio (only considers downside deviation)
        downside_returns = ticker_returns[ticker_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        sortino_ratio = (ticker_returns.mean() - daily_risk_free) / downside_deviation * np.sqrt(252) if len(downside_returns) > 0 else np.nan
        
        # Calculate Value at Risk (VaR) - 95% confidence level
        var_95 = np.percentile(ticker_returns, 5) * 100
        
        # Calculate Conditional VaR (CVaR) / Expected Shortfall
        cvar_95 = ticker_returns[ticker_returns <= np.percentile(ticker_returns, 5)].mean() * 100
        
        # Calculate Maximum Drawdown
        cumulative_returns = (1 + ticker_returns).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns / running_max - 1) * 100
        max_drawdown = drawdown.min()
        
        # Calculate Skewness and Kurtosis
        skewness = stats.skew(ticker_returns)
        kurtosis = stats.kurtosis(ticker_returns)
        
        # Calculate Tracking Error (vs. benchmark)
        tracking_difference = ticker_returns - benchmark_returns
        tracking_error = tracking_difference.std() * np.sqrt(252)
        
        # Calculate Information Ratio
        information_ratio = (ticker_returns.mean() - benchmark_returns.mean()) / tracking_difference.std() * np.sqrt(252)
        
        # Calculate Treynor Ratio
        treynor_ratio = (ticker_returns.mean() - daily_risk_free) / beta * np.sqrt(252) if beta != 0 else np.nan
        
        # Calculate Downside Capture Ratio
        negative_benchmark = benchmark_returns[benchmark_returns < 0]
        if len(negative_benchmark) > 0:
            benchmark_downside_avg = negative_benchmark.mean()
            stock_downside_avg = ticker_returns.loc[negative_benchmark.index].mean()
            downside_capture = (stock_downside_avg / benchmark_downside_avg) * 100 if benchmark_downside_avg != 0 else np.nan
        else:
            downside_capture = np.nan
            
        # Calculate Upside Capture Ratio
        positive_benchmark = benchmark_returns[benchmark_returns > 0]
        if len(positive_benchmark) > 0:
            benchmark_upside_avg = positive_benchmark.mean()
            stock_upside_avg = ticker_returns.loc[positive_benchmark.index].mean()
            upside_capture = (stock_upside_avg / benchmark_upside_avg) * 100 if benchmark_upside_avg != 0 else np.nan
        else:
            upside_capture = np.nan
            
        # Calculate Jensens Alpha (another way to calculate alpha)
        jensens_alpha = (ticker_returns.mean() - (daily_risk_free + beta * (benchmark_returns.mean() - daily_risk_free))) * 252
        
        # Create rolling volatility and beta for charts
        window = min(60, len(ticker_returns)) if len(ticker_returns) >= 21 else len(ticker_returns)
        rolling_volatility = ticker_returns.rolling(window=window).std() * np.sqrt(252)
        
        rolling_covariance = ticker_returns.rolling(window=window).cov(benchmark_returns)
        rolling_benchmark_variance = benchmark_returns.rolling(window=window).var()
        rolling_beta = rolling_covariance / rolling_benchmark_variance
        
        # Calculate CAPM expected returns
        capm_expected_return = risk_free_rate + beta * (benchmark_mean_return * 252 - risk_free_rate)
        
        # Calculate R-squared
        correlation = ticker_returns.corr(benchmark_returns)
        r_squared = correlation ** 2
        
        # Format dates for charts
        dates = [date.strftime('%Y-%m-%d') for date in ticker_returns.index]
        
        # Create a risk score (0-100)
        # Higher score = higher risk
        risk_score = calculate_risk_score(volatility, beta, max_drawdown, var_95, skewness, kurtosis)
        
        # Determine risk category
        risk_category = get_risk_category(risk_score)

        # Format data for charts
        chart_data = {
            "dates": dates,
            "rolling_volatility": rolling_volatility.tolist(),
            "rolling_beta": rolling_beta.tolist(),
            "drawdowns": drawdown.tolist(),
            "ticker_cumulative_returns": cumulative_returns.tolist(),
            "benchmark_cumulative_returns": (1 + benchmark_returns).cumprod().tolist()
        }
        
        # Assemble risk metrics
        risk_metrics = {
            "volatility": round(volatility * 100, 2),
            "benchmark_volatility": round(benchmark_volatility * 100, 2),
            "beta": round(beta, 2),
            "alpha": round(alpha * 100, 2),
            "jensens_alpha": round(jensens_alpha * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2) if not np.isnan(sortino_ratio) else None,
            "var_95": round(var_95, 2),
            "cvar_95": round(cvar_95, 2),
            "max_drawdown": round(max_drawdown, 2),
            "skewness": round(skewness, 2),
            "kurtosis": round(kurtosis, 2),
            "tracking_error": round(tracking_error * 100, 2),
            "information_ratio": round(information_ratio, 2),
            "treynor_ratio": round(treynor_ratio, 2) if not np.isnan(treynor_ratio) else None,
            "downside_capture": round(downside_capture, 2) if not np.isnan(downside_capture) else None,
            "upside_capture": round(upside_capture, 2) if not np.isnan(upside_capture) else None,
            "r_squared": round(r_squared, 2),
            "capm_expected_return": round(capm_expected_return * 100, 2),
            "risk_score": round(risk_score, 0),
            "risk_category": risk_category
        }
        
        return {
            "success": True,
            "risk_metrics": risk_metrics,
            "chart_data": chart_data
        }
            
    except Exception as e:
        print(f"Error assessing risk: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def calculate_risk_score(volatility, beta, max_drawdown, var_95, skewness, kurtosis):
    """
    Calculate a risk score (0-100) based on multiple risk factors.
    Higher score = higher risk.
    
    Parameters:
        volatility (float): Annualized volatility
        beta (float): Beta vs. benchmark
        max_drawdown (float): Maximum drawdown percentage
        var_95 (float): Value at Risk (95% confidence)
        skewness (float): Return distribution skewness
        kurtosis (float): Return distribution kurtosis
        
    Returns:
        float: Risk score (0-100)
    """
    # Assign scores for individual components
    # Volatility: 0-30 points (higher volatility = higher score)
    vol_score = min(30, max(0, 30 * (volatility / 0.5)))
    
    # Beta: 0-20 points (higher beta = higher score)
    beta_score = min(20, max(0, 10 * (beta if beta > 0 else 2)))
    
    # Max Drawdown: 0-20 points (larger drawdown = higher score)
    drawdown_score = min(20, max(0, 20 * (abs(max_drawdown) / 50)))
    
    # VaR: 0-15 points (more negative VaR = higher score)
    var_score = min(15, max(0, 15 * (abs(var_95) / 5)))
    
    # Skewness: 0-10 points (negative skew = higher score)
    skew_score = min(10, max(0, 5 * (1 - skewness if skewness < 0 else 0)))
    
    # Kurtosis: 0-5 points (higher kurtosis = higher score)
    kurt_score = min(5, max(0, 5 * (kurtosis / 5 if kurtosis > 0 else 0)))
    
    # Total score
    total_score = vol_score + beta_score + drawdown_score + var_score + skew_score + kurt_score
    
    # Scale to 0-100
    return min(100, total_score)

def get_risk_category(risk_score):
    """
    Determine the risk category based on the risk score.
    
    Parameters:
        risk_score (float): Risk score (0-100)
    
    Returns:
        str: Risk category
    """
    if risk_score < 20:
        return "Very Low Risk"
    elif risk_score < 40:
        return "Low Risk"
    elif risk_score < 60:
        return "Moderate Risk"
    elif risk_score < 80:
        return "High Risk"
    else:
        return "Very High Risk"

def compare_risk_metrics(ticker_symbols, benchmark_ticker='^GSPC', period='1y'):
    """
    Compare risk metrics for multiple stocks.
    
    Parameters:
        ticker_symbols (list): List of stock ticker symbols
        benchmark_ticker (str): Benchmark ticker symbol
        period (str): Period to analyze
        
    Returns:
        dict: Comparison of risk metrics
    """
    try:
        results = {}
        
        for symbol in ticker_symbols:
            risk_data = assess_risk(symbol, benchmark_ticker, period)
            if risk_data["success"]:
                results[symbol] = risk_data["risk_metrics"]
                
        if not results:
            return {
                "success": False,
                "message": "Failed to retrieve risk metrics for any ticker"
            }
            
        # Create comparison dataframe
        metrics_to_compare = [
            "volatility", "beta", "alpha", "sharpe_ratio", "sortino_ratio", 
            "var_95", "max_drawdown", "information_ratio", "risk_score"
        ]
        
        comparison_data = {}
        for metric in metrics_to_compare:
            comparison_data[metric] = {symbol: results[symbol].get(metric) for symbol in results}
            
        # Calculate relative rankings
        rankings = {}
        for metric in metrics_to_compare:
            # For metrics where higher is better
            higher_is_better = metric in ["alpha", "sharpe_ratio", "sortino_ratio", "information_ratio"]
            
            # Extract values for this metric
            values = [results[symbol].get(metric) for symbol in results if results[symbol].get(metric) is not None]
            
            if not values:
                continue
                
            # Rank the symbols for this metric
            for symbol in results:
                if results[symbol].get(metric) is None:
                    continue
                    
                if not rankings.get(symbol):
                    rankings[symbol] = {}
                    
                # Count how many symbols have better values for this metric
                count_better = sum(1 for s in results if results[s].get(metric) is not None and 
                                 ((higher_is_better and results[s].get(metric) > results[symbol].get(metric)) or
                                  (not higher_is_better and results[s].get(metric) < results[symbol].get(metric))))
                
                # Calculate percentile rank
                percentile = (len(values) - count_better) / len(values) * 100
                rankings[symbol][metric] = round(percentile, 0)
        
        return {
            "success": True,
            "metrics": results,
            "comparison": comparison_data,
            "rankings": rankings
        }
        
    except Exception as e:
        print(f"Error comparing risk metrics: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def calculate_financial_health_score(ticker_symbol):
    """
    Calculate a financial health score based on key financial ratios.
    
    Parameters:
        ticker_symbol (str): Stock ticker symbol
        
    Returns:
        dict: Financial health assessment
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get financial data
        info = ticker.info
        balance_sheet = ticker.balance_sheet
        income_stmt = ticker.income_stmt
        cash_flow = ticker.cashflow
        
        if not info:
            return {
                "success": False,
                "message": "Failed to retrieve financial information"
            }
            
        # Initialize scores
        profitability_score = 0
        liquidity_score = 0
        solvency_score = 0
        efficiency_score = 0
        growth_score = 0
        
        # Calculate profitability metrics
        profit_margins = info.get('profitMargins', 0)
        operating_margins = info.get('operatingMargins', 0)
        return_on_equity = info.get('returnOnEquity', 0)
        return_on_assets = info.get('returnOnAssets', 0)
        
        # Calculate liquidity metrics
        current_ratio = info.get('currentRatio', 0)
        quick_ratio = info.get('quickRatio', 0)
        
        # Calculate solvency metrics
        debt_to_equity = info.get('debtToEquity', 0)
        interest_coverage = info.get('interestCoverage', 0) if 'interestCoverage' in info else None
        
        # Calculate efficiency metrics
        asset_turnover = None
        inventory_turnover = None
        
        if not balance_sheet.empty and not income_stmt.empty:
            try:
                total_assets = balance_sheet.loc['Total Assets'].iloc[0]
                total_revenue = income_stmt.loc['Total Revenue'].iloc[0]
                if total_assets > 0:
                    asset_turnover = total_revenue / total_assets
            except:
                pass
        
        # Calculate growth metrics
        revenue_growth = info.get('revenueGrowth', 0)
        earnings_growth = info.get('earningsGrowth', 0)
        
        # Score profitability (0-25 points)
        if profit_margins:
            profitability_score += min(7, max(0, profit_margins * 100))
        if operating_margins:
            profitability_score += min(6, max(0, operating_margins * 100))
        if return_on_equity:
            profitability_score += min(6, max(0, return_on_equity * 25))
        if return_on_assets:
            profitability_score += min(6, max(0, return_on_assets * 50))
            
        # Score liquidity (0-20 points)
        if current_ratio:
            liquidity_score += min(10, max(0, current_ratio * 5))
        if quick_ratio:
            liquidity_score += min(10, max(0, quick_ratio * 10))
            
        # Score solvency (0-20 points)
        if debt_to_equity is not None:
            # Lower debt to equity is better
            if debt_to_equity <= 0:
                solvency_score += 10
            else:
                solvency_score += min(10, max(0, 10 - (debt_to_equity / 100)))
        if interest_coverage:
            solvency_score += min(10, max(0, interest_coverage))
            
        # Score efficiency (0-15 points)
        if asset_turnover:
            efficiency_score += min(15, max(0, asset_turnover * 15))
            
        # Score growth (0-20 points)
        if revenue_growth:
            growth_score += min(10, max(0, revenue_growth * 50))
        if earnings_growth:
            growth_score += min(10, max(0, earnings_growth * 50))
            
        # Calculate total score
        total_score = profitability_score + liquidity_score + solvency_score + efficiency_score + growth_score
        
        # Determine health category
        if total_score >= 80:
            health_category = "Excellent"
        elif total_score >= 65:
            health_category = "Good"
        elif total_score >= 50:
            health_category = "Moderate"
        elif total_score >= 35:
            health_category = "Weak"
        else:
            health_category = "Poor"
            
        # Create Z-Score (Altman Z-Score for bankruptcy risk)
        z_score = None
        z_score_interpretation = None
        
        if not balance_sheet.empty and not income_stmt.empty:
            try:
                working_capital = balance_sheet.loc['Current Assets'].iloc[0] - balance_sheet.loc['Current Liabilities'].iloc[0]
                total_assets = balance_sheet.loc['Total Assets'].iloc[0]
                retained_earnings = balance_sheet.loc['Retained Earnings'].iloc[0] if 'Retained Earnings' in balance_sheet.index else 0
                ebit = income_stmt.loc['EBIT'].iloc[0] if 'EBIT' in income_stmt.index else income_stmt.loc['Operating Income'].iloc[0]
                market_cap = info.get('marketCap', 0)
                book_value_liabilities = balance_sheet.loc['Total Liabilities'].iloc[0]
                sales = income_stmt.loc['Total Revenue'].iloc[0]
                
                # Calculate Altman Z-Score
                a = working_capital / total_assets
                b = retained_earnings / total_assets
                c = ebit / total_assets
                d = market_cap / book_value_liabilities
                e = sales / total_assets
                
                z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
                
                # Interpret Z-Score
                if z_score > 2.99:
                    z_score_interpretation = "Safe Zone - Low probability of financial distress"
                elif z_score > 1.81:
                    z_score_interpretation = "Grey Zone - Medium risk of financial distress"
                else:
                    z_score_interpretation = "Distress Zone - High risk of financial distress"
            except Exception as e:
                print(f"Error calculating Z-Score: {e}")
        
        # Format metrics for response
        metrics = {
            "profitability": {
                "profit_margin": round(profit_margins * 100, 2) if profit_margins else None,
                "operating_margin": round(operating_margins * 100, 2) if operating_margins else None,
                "roe": round(return_on_equity * 100, 2) if return_on_equity else None,
                "roa": round(return_on_assets * 100, 2) if return_on_assets else None
            },
            "liquidity": {
                "current_ratio": round(current_ratio, 2) if current_ratio else None,
                "quick_ratio": round(quick_ratio, 2) if quick_ratio else None
            },
            "solvency": {
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "interest_coverage": round(interest_coverage, 2) if interest_coverage else None
            },
            "efficiency": {
                "asset_turnover": round(asset_turnover, 2) if asset_turnover else None
            },
            "growth": {
                "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else None,
                "earnings_growth": round(earnings_growth * 100, 2) if earnings_growth else None
            }
        }
        
        # Create final assessment
        assessment = {
            "success": True,
            "financial_health_score": round(total_score, 0),
            "health_category": health_category,
            "z_score": round(z_score, 2) if z_score is not None else None,
            "z_score_interpretation": z_score_interpretation,
            "metrics": metrics,
            "sub_scores": {
                "profitability": round(profitability_score, 0),
                "liquidity": round(liquidity_score, 0),
                "solvency": round(solvency_score, 0),
                "efficiency": round(efficiency_score, 0),
                "growth": round(growth_score, 0)
            }
        }
        
        return assessment
        
    except Exception as e:
        print(f"Error calculating financial health: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        } 