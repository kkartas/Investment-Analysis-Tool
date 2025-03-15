def get_fundamentals(ticker):
    """
    Returns a dictionary of key fundamental data from a yfinance.Ticker object.
    Processes the raw data and formats it to match the template's expected format.
    """
    try:
        info = ticker.info
        
        # Format dividend yield as percentage if available
        dividend_yield = info.get("dividendYield", None)
        if dividend_yield is not None and dividend_yield != "N/A":
            dividend_yield = round(float(dividend_yield) * 100, 2)
        
        # Format market cap with proper precision
        market_cap = info.get("marketCap", "N/A")
        if market_cap != "N/A" and market_cap is not None:
            if market_cap >= 1_000_000_000:
                market_cap = f"{market_cap / 1_000_000_000:.2f}B"
            elif market_cap >= 1_000_000:
                market_cap = f"{market_cap / 1_000_000:.2f}M"
            else:
                market_cap = f"{market_cap:,.0f}"
        
        # Get additional financial ratios from balance sheet and financials if available
        try:
            balance_sheet = ticker.balance_sheet
            financials = ticker.financials
            
            # Calculate ROE (Return on Equity) if possible
            roe = None
            if not balance_sheet.empty and not financials.empty:
                if 'Total Stockholder Equity' in balance_sheet.index and 'Net Income' in financials.index:
                    equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
                    net_income = financials.loc['Net Income'].iloc[0]
                    if equity != 0 and equity is not None and net_income is not None:
                        roe = round(net_income / equity * 100, 2)
            
            # Calculate ROA (Return on Assets) if possible
            roa = None
            if not balance_sheet.empty and not financials.empty:
                if 'Total Assets' in balance_sheet.index and 'Net Income' in financials.index:
                    assets = balance_sheet.loc['Total Assets'].iloc[0]
                    net_income = financials.loc['Net Income'].iloc[0]
                    if assets != 0 and assets is not None and net_income is not None:
                        roa = round(net_income / assets * 100, 2)
            
            # Calculate Debt to Equity ratio if possible
            debt_to_equity = None
            if not balance_sheet.empty:
                if 'Total Debt' in balance_sheet.index and 'Total Stockholder Equity' in balance_sheet.index:
                    debt = balance_sheet.loc['Total Debt'].iloc[0]
                    equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
                    if equity != 0 and equity is not None and debt is not None:
                        debt_to_equity = round(debt / equity, 2)
            
            # Calculate Current Ratio if possible
            current_ratio = None
            if not balance_sheet.empty:
                if 'Current Assets' in balance_sheet.index and 'Current Liabilities' in balance_sheet.index:
                    current_assets = balance_sheet.loc['Current Assets'].iloc[0]
                    current_liabilities = balance_sheet.loc['Current Liabilities'].iloc[0]
                    if current_liabilities != 0 and current_liabilities is not None and current_assets is not None:
                        current_ratio = round(current_assets / current_liabilities, 2)
                        
        except Exception as e:
            print(f"Error calculating financial ratios: {e}")
            roe = None
            roa = None
            debt_to_equity = None
            current_ratio = None
        
        # Format the data to match the template's expected structure
        fundamentals = {
            "market_cap": market_cap,
            "pe_ratio": info.get("trailingPE", "N/A"),
            "eps": info.get("trailingEps", "N/A"),
            "dividend_yield": dividend_yield,
            "week_52_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "week_52_low": info.get("fiftyTwoWeekLow", "N/A"),
            "roe": roe,
            "roa": roa,
            "profit_margin": round(info.get("profitMargins", 0) * 100, 2) if info.get("profitMargins") is not None else "N/A",
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "price_to_book": info.get("priceToBook", "N/A")
        }
        
        return fundamentals
        
    except Exception as e:
        print(f"Error in get_fundamentals: {e}")
        return {}
