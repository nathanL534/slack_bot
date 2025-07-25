import os
import requests
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")


def get_tech_tickers(limit=100):
    url = f"https://financialmodelingprep.com/api/v3/stock-screener"
    params = {
        "sector": "Technology",
        "exchange": "NASDAQ",
        "limit": limit,
        "apikey": FMP_API_KEY
    }
    

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"FMP request failed: {response.text}")

    data = response.json()
    return [entry["symbol"] for entry in data]