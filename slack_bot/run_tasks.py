from dotenv import load_dotenv
import os

# ✅ Load .env first
load_dotenv()

# ✅ Confirm it's loading


# ✅ Now import modules that use those env vars
from tasks.scheduler import run_trading_algo, check_portfolio
import sys


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else None
    if task == "morning_trade":
        print("🔁 Running 10AM trading algorithm...")


    elif task == "afternoon_trade":
        print("🔁 Running 3PM trading algorithm...")


    elif task == "daily_check":
        print("📊 Running daily portfolio check...")
        check_portfolio()

    else:
        print("❌ Invalid task. Use one of: morning_trade, afternoon_trade, daily_check")

if __name__ == "__main__":
    main()
    