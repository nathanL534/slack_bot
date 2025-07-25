from datetime import datetime

class Ticker:
    def __init__(self, symbol, score=0, date_added = None, time_held = 0):
        self.symbol = symbol
        self.score = score
        self.date_added = date_added or datetime.now()
        self.time_held = time_held

    
    def __lt__(self, other: "Ticker"):
        return self.score > other.score
    
    def to_dict(self):
        return{
            "symbol": self.symbol,
            "score": self.score,
            "date_added": self.date_added.isoformat(),
            "time_held": self.time_held
            
        }
        
    @staticmethod
    def from_dict(data):
        return Ticker(
            symbol=data["symbol"],
            score=data["score"],
            date_added=datetime.fromisoformat(data["date_added"]),
            time_held=data.get("time_held", 0)
        )
    
    
    