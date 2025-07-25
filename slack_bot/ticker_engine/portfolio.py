from ticker_engine.ticker import Ticker
import json
from datetime import datetime
class PortfolioManager:
    
    def __init__(self):
        self.holdings: dict[str, Ticker] = {}
        
    def add(self, ticker:Ticker):
        self.holdings[ticker.symbol] = ticker
    def remove(self, symbol ):
        if symbol in self.holdings:
            del self.holdings[symbol]
            
    def get(self, symbol):
        if symbol in self.holdings:
            return self.holdings[symbol]
        
    def get_all(self):
        return list(self.holdings.values())
    
    def increment_time_held(self):
        for ticker in self.holdings.values():
            ticker.time_held += 1
    
    
    def save_to_json(self, filename="portfolio.json"):
        data = {sym: t.to_dict() for sym, t in self.holdings.items()}
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
            
    def load_from_json(self, filename = "portfolio.json"):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                self.holdings = {
                    sym: Ticker.from_dict(t) for sym, t in data.items()
                }
                
        except FileNotFoundError:
            self.holdings = {}
            
    def sync_with_alpaca(self, alpaca_positions: list):
        for pos in alpaca_positions:
            symbol = pos["symbol"]
            if symbol not in self.holdings:
                ticker = Ticker(
                symbol=symbol,
                score=0,  # you can update this after scoring
                date_added=datetime.now(),
                time_held=0  # or estimate based on date_bought
                )
                self.add(ticker)
            else:
                #TODO add something to update score or whatever
                pass 
                
            
    