import yfinance as yf


def get_weekly_average(ticker: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="7d", interval="1d")
    if hist.empty:
        return None, None

    closing_prices = hist["Close"].tolist()
    today_price = closing_prices[-1]
    
    avg = sum(closing_prices) / len(closing_prices)
    
    return round(today_price, 2), round(avg, 2)