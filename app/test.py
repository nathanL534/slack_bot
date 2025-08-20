import yfinance as yf

def get_yf_bars(symbol, days=60):
    df = yf.download(symbol, period=f"{days}d", interval="1d", auto_adjust=True)
    return df

bars = get_yf_bars("AAPL", 5)
print(bars)