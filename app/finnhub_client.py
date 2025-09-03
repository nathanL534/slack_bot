import os
import requests
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


def get_tech_tickers(limit=100):
    """
    Get technology stocks from US exchanges using Finnhub API.
    Returns a list of stock symbols.
    """
    # Get US stock symbols
    url = "https://finnhub.io/api/v1/stock/symbol"
    params = {
        "exchange": "US",
        "token": FINNHUB_API_KEY
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Finnhub request failed: {response.text}")
    
    data = response.json()
    
    # Filter for tech-related stocks (you can expand this list)
    tech_keywords = ['TECH', 'SOFTWARE', 'COMPUTER', 'INTERNET', 'CLOUD', 'AI', 'DIGITAL']
    tech_symbols = []
    
    for stock in data:
        symbol = stock.get('symbol', '')
        description = stock.get('description', '').upper()
        
        # Basic filtering for tech stocks
        if any(keyword in description for keyword in tech_keywords):
            tech_symbols.append(symbol)
            if len(tech_symbols) >= limit:
                break
    
    # If we don't get enough from keyword filtering, add some well-known tech stocks
    if len(tech_symbols) < 20:
        known_tech_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'CRM', 'ORCL', 'ADBE', 'NOW', 'INTC', 'AMD', 'QCOM', 'AVGO',
            'SHOP', 'SNOW', 'PLTR', 'ROKU', 'ZM', 'DOCU', 'TWLO', 'OKTA'
        ]
        
        for symbol in known_tech_stocks:
            if symbol not in tech_symbols:
                tech_symbols.append(symbol)
                if len(tech_symbols) >= limit:
                    break
    
    return tech_symbols[:limit]
