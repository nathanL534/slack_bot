


from app.alpaca_client import get_portfolio_status, sell_stock
from app.slack import send_message

from ticker_engine.scorer import swing_score

from app.db import get_latest_score






def check_exits():
    portfolio: dict = get_portfolio_status()
    positions = portfolio["positions"]
    
    
    for p in positions:
        symbol = p["symbol"]
        # defensive casts: Alpaca sometimes returns strings
        try:
            qty = int(float(p.get("qty", 0)))
        except Exception:
            qty = 0

        try:
            unrealized_plpc = float(p.get("unrealized_plpc", 0))
        except Exception:
            unrealized_plpc = 0.0

        score = get_latest_score(symbol)
        if score is None:
            score = swing_score(symbol=symbol)

        # skip empty positions
        if qty <= 0:
            continue

        # full exit: low score or losing too much
        if score < 0.45 or unrealized_plpc < -0.08:
            reason = f"low_score={score:.2f}" if score < 0.45 else f"loss_pct={unrealized_plpc:.2f}"
            try:
                order = sell_stock(symbol, qty)
                send_message("#notifier", f"Sold {qty} {symbol} — reason: {reason} — order: {getattr(order, 'id', order)}")
            except Exception as e:
                send_message("#notifier", f"Failed to sell {qty} {symbol} — reason: {reason} — error: {e}")

        # partial profit taking
        if unrealized_plpc > 0.10:
            partial_qty = max(1, int(qty * 2 / 5))
            try:
                order = sell_stock(symbol, partial_qty)
                send_message("#notifier", f"Partially sold {partial_qty} {symbol} (take profit) — unrealized_pct={unrealized_plpc:.2f} — order: {getattr(order, 'id', order)}")
            except Exception as e:
                send_message("#notifier", f"Failed partial sell {partial_qty} {symbol} — error: {e}")
            
            
            
            
            
        
            
            
        
        
        
        
        
        
    
    