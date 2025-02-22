def get_options_chain(ticker, expiry=None):
    """
    Returns a tuple (calls, puts) of options chain data.
    If no expiry is provided, uses the first available expiry.
    """
    try:
        if expiry is None:
            expiries = ticker.options
            if not expiries:
                return None, None
            expiry = expiries[0]
        chain = ticker.option_chain(expiry)
        return chain.calls, chain.puts
    except Exception:
        return None, None
