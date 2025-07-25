from app.alpaca_client import  get_portfolio_status
from app.slack import send_message 
from datetime import datetime

def run_trading_algo():
    message = (
            f"📊 *Running trading algo Check*\n"
            f" *Date:* {datetime.now()}\n"
        )
    send_message("#notifier", message)
    

def check_portfolio():
    try:
        status = get_portfolio_status()
        account = status["account"]

        message = (
            f"📊 *Daily Portfolio Check*\n"
            f" *Date:* {datetime.now()}\n"
            
            f"> 💵 Cash: ${account['cash']}\n"

            f"> 💼 Portfolio Value: ${account['portfolio_value']}\n"
            f"> 🛒 Buying Power: ${account['buying_power']}\n"
            f"> ✅ Status: {account['status']}"
        )

        send_message("#notifier", message)

    except Exception as e:
        send_message("#notifier", f"❌ Error fetching portfolio: {str(e)}")
