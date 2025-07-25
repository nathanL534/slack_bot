from fastapi import APIRouter, Request, HTTPException
from app.slack import send_message

from app.alpaca_client import get_portfolio_status, get_7_day_average, buy_stock, sell_stock
from app.fmp_client import get_tech_tickers

from tasks.scheduler import run_trading_algo, check_portfolio
import json 





router = APIRouter()
@router.post("/greet")
async def greet():
    send_message(channel= "#notifier", text="Hi")
    return {"message": "sent hi to slack"}


@router.get("/check-weekly-average")
async def check_weekly_avg(ticker: str = "AAPL"):
    today, avg = get_7_day_average(ticker)

    if today is None or avg is None:
        send_message("#notifier", f"⚠️ Failed to fetch 7-day average for {ticker}.")
        return {"error": "Could not retrieve data from Alpaca"}

    if today < avg:
        send_message("#notifier", f"📉 {ticker} is ${today}, below 7-day avg (${avg})")
        return {"message": f"{ticker} is below average"}

    elif today > avg:
        send_message("#notifier", f"📈 {ticker} is ${today}, above 7-day avg (${avg})")
        return {"message": f"{ticker} is above average"}

    else:
        send_message("#notifier", f"➖ {ticker} is ${today}, equal to 7-day avg (${avg})")
        return {"message": f"{ticker} is equal to the 7-day average: ${avg}"}

@router.get("/update_portfolio_status")
async def update_portfolio_status():
    try:
        status = get_portfolio_status()
        account = status["account"]

        message = (
            f"📊 *Portfolio Status*\n"
            f"> 💵 Cash: ${account['cash']}\n"
            f"> 💼 Portfolio Value: ${account['portfolio_value']}\n"
            f"> 🛒 Buying Power: ${account['buying_power']}\n"
            f"> ✅ Status: {account['status']}"
        )

        send_message("#paper-trade-tracker", message)
        return {"message": "Portfolio status sent to Slack", "data": status}
    except Exception as e:
        error_msg = f"❌ Error fetching portfolio status: {str(e)}"
        send_message("#notifier", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    
@router.get("/tech-tickers")
def tech_tickers():
    tickers = get_tech_tickers()
    return tickers


@router.post("/buy-stock")
def api_buy_stock(sym: str, quant: int):
    try:
        order = buy_stock(sym, quant)
        send_message("#notifier", f"🟢 BUY order placed: {quant} share(s) of {sym}")
        return {
            "message": f"✅ Buy order placed for {sym}",
            "order": order._raw
        }
    except Exception as e:
        send_message("#notifier", f"❌ Failed to BUY {sym}: {str(e)}")
        return {"error": str(e)}


@router.post("/sell-stock")
def api_sell_stock(sym: str, quant: int):
    try:
        order = sell_stock(sym, quant)
        send_message("#notifier", f"🔴 SELL order placed: {quant} share(s) of {sym}")
        return {
            "message": f"✅ Sell order placed for {sym}",
            "order": order._raw
        }
    except Exception as e:
        send_message("#notifier", f"❌ Failed to SELL {sym}: {str(e)}")
        return {"error": str(e)}



    
@router.get("/run-morning-trade")
def morning_trade():
    run_trading_algo()
    return {"message": "✅ Morning trade algo triggered"}

@router.get("/run-afternoon-trade")
def afternoon_trade():
    run_trading_algo()
    return {"message": "✅ Afternoon trade algo triggered"}

@router.get("/daily-check")
def daily_check():
    check_portfolio()
    return {"message": "✅ Daily portfolio check complete"}
