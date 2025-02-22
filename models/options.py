# models/options.py
def get_options_chain(ticker, expiry=None):
    """
    Returns a tuple (calls, puts) of options chain data as list of dicts.
    If no expiry is provided, uses the first available expiry.
    """
    try:
        expiries = ticker.options
        if not expiries:
            return None, None
        if expiry is None:
            expiry = expiries[0]
        chain = ticker.option_chain(expiry)
        return chain.calls.to_dict('records'), chain.puts.to_dict('records')
    except Exception as e:
        print("Options chain error:", e)
        return None, None
