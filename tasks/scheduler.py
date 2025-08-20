from app.alpaca_client import  get_portfolio_status
from app.slack import send_message 
from datetime import datetime

def run_trading_algo():
    message = (
            f"📊 *Running trading algo Check*\n"
            f" *Date:* {datetime.now()}\n"
        )
    send_message("#notifier", message)
    

def run_daily_orchestrator():
    """Run the daily watchlist orchestrator and send results to Slack."""
    try:
        from ticker_engine.orchestrator import orchestrate_daily
        
        message = (
            f"🚀 *Starting Daily Watchlist Orchestrator*\n"
            f" *Date:* {datetime.now()}\n"
        )
        send_message("#notifier", message)
        
        # Run the orchestrator
        result = orchestrate_daily()
        
        # Format the results for Slack
        rescored_count = len(result["rescored"])
        promotions_count = len(result["promotions"])
        demotions_count = len(result["demotions"])
        
        # Get top 3 tickers
        top_3 = result["watchlist_top"][:3]
        if top_3:
            top_3_text = " | ".join([f"{sym} {score:.3f}" for sym, score in top_3])
            top_line = f"🔝 *Top 3:* {top_3_text}"
        else:
            top_line = "📭 *No watchlist entries found*"
        
        summary_message = (
            f"✅ *Daily Orchestrator Complete*\n"
            f"{top_line}\n"
            f"> 📊 Rescored: {rescored_count} symbols\n"
            f"> 🔼 Promotions: {promotions_count}\n"
            f"> 🔽 Demotions: {demotions_count}\n"
            f"> 📈 Watchlist size: {len(result['watchlist_top'])}"
        )
        
        send_message("#notifier", summary_message)
        
        return result
        
    except Exception as e:
        error_msg = f"❌ *Daily Orchestrator Failed*\n> Error: {str(e)}"
        send_message("#notifier", error_msg)
        raise


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
