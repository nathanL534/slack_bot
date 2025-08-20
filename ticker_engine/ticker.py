from datetime import datetime

class Ticker:
    def __init__(self, symbol, score=0, date_added = None, time_held = 0, date_bought = None):
        self.symbol = symbol
        self.score = score
        self.date_added = date_added or datetime.now()
        self.time_held = time_held
        self.date_bought = date_bought

    
    def __lt__(self, other: "Ticker"):
        return self.score > other.score
    
    def to_dict(self):
        return{
            "symbol": self.symbol,
            "score": self.score,
            "date_added": self.date_added.isoformat(),
            "time_held": self.time_held,
            "date_bought": self.date_bought.isoformat() if self.date_bought else None
        }
        
    @staticmethod
    def from_dict(data):
        return Ticker(
            symbol=data["symbol"],
            score=data["score"],
            date_added=datetime.fromisoformat(data["date_added"]),
            time_held=data.get("time_held", 0),
            date_bought=datetime.fromisoformat(data["date_bought"]) if data["date_bought"] else None,
        )
    
    
    