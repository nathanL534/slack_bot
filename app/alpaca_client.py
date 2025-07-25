import os
from alpaca_trade_api.rest import REST

API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

alpaca = REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
print("APCA_API_KEY_ID:", os.getenv("APCA_API_KEY_ID"))
print("APCA_API_SECRET_KEY:", os.getenv("APCA_API_SECRET_KEY"))
print("APCA_API_BASE_URL:", os.getenv("APCA_API_BASE_URL"))

def get_portfolio_status():
    account = alpaca.get_account()
    positions = alpaca.list_positions()

    return {
        "account": {
            "cash": account.cash,
            "portfolio_value": account.portfolio_value,
            "buying_power": account.buying_power,
            "status": account.status

        },
        "positions": [
            {
                "symbol": p.symbol,
                "qty": p.qty,
                "market_value": p.market_value,
                "unrealized_pl": p.unrealized_pl,
                "current_price": p.current_price
            } for p in positions
        ]
    }
    
def get_7_day_average(symbol: str):
    bars = alpaca.get_bars(symbol, timeframe="1Day", limit=7)
    closes = [bar.c for bar in bars]
    if not closes:
        return None, None
    avg = round(sum(closes) / len(closes), 2)
    today = round(closes[-1], 2)
    return today, avg


def buy_stock(symbol: str, quantity = 1):
    try:
        order = alpaca.submit_order(
            symbol= symbol,
            qty = quantity,
            side = "buy",
            type="market",
            time_in_force="gtc"
            
        )
        print(f"✅ BUY order placed for {quantity} shares of {symbol}")
        return order
    except Exception as e:
        print(f"❌ Failed to place BUY order for {symbol}: {e}")
        raise
        

    
def sell_stock(symbol: str, quantity = 1):
    try:
        order = alpaca.submit_order(
            symbol= symbol,
            qty = quantity,
            side = "sell",
            type="market",
            time_in_force="gtc"
            
        )
        print(f"✅ Sold order placed for {quantity} shares of {symbol}")
        return order
    except Exception as e:
        print(f"❌ Failed to place Selk order for {symbol}: {e}")
        raise
    
