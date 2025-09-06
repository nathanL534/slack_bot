# Market API utilities
from fastapi import APIRouter
from datetime import datetime, time
import pytz

router = APIRouter()


def is_market_open() -> bool:
    """
    Check if US stock market is currently open.
    
    Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
    Does not account for holidays.
    """
    # Get current time in Eastern timezone
    et = pytz.timezone('US/Eastern')
    now_et = datetime.now(et)
    
    # Check if it's a weekday (0=Monday, 6=Sunday)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = time(9, 30)  # 9:30 AM
    market_close = time(16, 0)  # 4:00 PM
    
    current_time = now_et.time()
    
    return market_open <= current_time <= market_close


@router.get("/test")
def test():
    return {"message": "test"}


@router.get("/market-status")
def get_market_status():
    """API endpoint to check market status."""
    return {
        "is_open": is_market_open(),
        "timestamp": datetime.now().isoformat()
    }
