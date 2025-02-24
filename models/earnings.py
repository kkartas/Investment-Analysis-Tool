# models/earnings.py

import yfinance as yf
import pandas as pd

def get_earnings(symbol: str):
    """
    Fetch revenue & net income from yfinance for a given symbol using Ticker.income_stmt.

    Ticker.income_stmt can return:
      - A dictionary with keys ["annual", "quarterly"] -> DataFrames
      - Sometimes a single DataFrame
      - Sometimes None

    We'll handle these cases carefully to avoid "truth value of a DataFrame is ambiguous."

    Returns a list of dicts, each like:
      {
        "period": str,   # e.g. "2022-12-31"
        "type": "Annual" or "Quarterly",
        "revenue": <float or 'N/A'>,
        "net_income": <float or 'N/A'>
      }
    """

    results = []
    try:
        ticker = yf.Ticker(symbol)

        data = ticker.income_stmt  # Could be a dict or DataFrame or None

        if data is None:
            # No data at all
            return results

        # If it's a DataFrame
        if isinstance(data, pd.DataFrame):
            # You could parse it as a single statement here
            if data.empty:
                return results
            # If you know how many columns or rows to expect, parse it.
            # E.g. we might do something simpler or just skip.
            # For a single DF approach, you might need to see exactly what's returned.
            # Example: interpret it as 'annual' data
            for col in data.columns:
                revenue = data.loc["TotalRevenue", col] if "TotalRevenue" in data.index else float('nan')
                net_income = data.loc["NetIncome", col] if "NetIncome" in data.index else float('nan')
                results.append({
                    "period": str(col),
                    "type": "Annual/SingleDF",
                    "revenue": revenue if pd.notna(revenue) else "N/A",
                    "net_income": net_income if pd.notna(net_income) else "N/A"
                })
            return results

        # Otherwise, assume it's a dictionary with keys: "annual", "quarterly"
        if not isinstance(data, dict):
            # If we get here, it's something unexpected. We'll just stop.
            return results

        # 1) Annual
        df_annual = data.get("annual")
        if df_annual is not None and not df_annual.empty:
            for col in df_annual.columns:
                revenue = df_annual.loc["TotalRevenue", col] if "TotalRevenue" in df_annual.index else float('nan')
                net_income = df_annual.loc["NetIncome", col] if "NetIncome" in df_annual.index else float('nan')
                results.append({
                    "period": str(col),
                    "type": "Annual",
                    "revenue": revenue if pd.notna(revenue) else "N/A",
                    "net_income": net_income if pd.notna(net_income) else "N/A"
                })

        # 2) Quarterly
        df_quarterly = data.get("quarterly")
        if df_quarterly is not None and not df_quarterly.empty:
            for col in df_quarterly.columns:
                revenue = df_quarterly.loc["TotalRevenue", col] if "TotalRevenue" in df_quarterly.index else float('nan')
                net_income = df_quarterly.loc["NetIncome", col] if "NetIncome" in df_quarterly.index else float('nan')
                results.append({
                    "period": str(col),
                    "type": "Quarterly",
                    "revenue": revenue if pd.notna(revenue) else "N/A",
                    "net_income": net_income if pd.notna(net_income) else "N/A"
                })

    except Exception as e:
        print(f"Error fetching income_stmt for {symbol}: {e}")

    return results
