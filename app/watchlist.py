"""
Watchlist API endpoints for managing stock watchlists in Supabase.

Provides CRUD operations for watchlists and ticker management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime

from . import db

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


# Pydantic models for request/response
class WatchlistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class TickerAdd(BaseModel):
    symbol: str
    notes: Optional[str] = None


class WatchlistTicker(BaseModel):
    id: int
    symbol: str
    notes: Optional[str]
    added_at: datetime


@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlists():
    """Get all watchlists for the user."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlists").select("*").execute()
        return result.data
    except Exception as e:
        logging.exception("Failed to fetch watchlists")
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlists: {str(e)}")


@router.post("/", response_model=WatchlistResponse)
async def create_watchlist(watchlist: WatchlistCreate):
    """Create a new watchlist."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlists").insert({
            "name": watchlist.name,
            "description": watchlist.description,
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create watchlist")
        
        return result.data[0]
    except Exception as e:
        logging.exception("Failed to create watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to create watchlist: {str(e)}")


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(watchlist_id: int):
    """Get a specific watchlist by ID."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlists").select("*").eq("id", watchlist_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to fetch watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlist: {str(e)}")


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(watchlist_id: int, watchlist: WatchlistCreate):
    """Update a watchlist."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlists").update({
            "name": watchlist.name,
            "description": watchlist.description,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", watchlist_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to update watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to update watchlist: {str(e)}")


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: int):
    """Delete a watchlist and all its tickers."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        # First delete all tickers in the watchlist
        db.supabase.table("watchlist_tickers").delete().eq("watchlist_id", watchlist_id).execute()
        
        # Then delete the watchlist
        result = db.supabase.table("watchlists").delete().eq("id", watchlist_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        return {"message": "Watchlist deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to delete watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to delete watchlist: {str(e)}")


@router.get("/{watchlist_id}/tickers", response_model=List[WatchlistTicker])
async def get_watchlist_tickers(watchlist_id: int):
    """Get all tickers in a watchlist."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlist_tickers").select("*").eq("watchlist_id", watchlist_id).execute()
        return result.data
    except Exception as e:
        logging.exception("Failed to fetch watchlist tickers")
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlist tickers: {str(e)}")


@router.post("/{watchlist_id}/tickers", response_model=WatchlistTicker)
async def add_ticker_to_watchlist(watchlist_id: int, ticker: TickerAdd):
    """Add a ticker to a watchlist."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        # Check if watchlist exists
        watchlist_result = db.supabase.table("watchlists").select("id").eq("id", watchlist_id).execute()
        if not watchlist_result.data:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        # Check if ticker already exists in watchlist
        existing = db.supabase.table("watchlist_tickers").select("id").eq("watchlist_id", watchlist_id).eq("symbol", ticker.symbol.upper()).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ticker already in watchlist")
        
        # Add ticker to watchlist
        result = db.supabase.table("watchlist_tickers").insert({
            "watchlist_id": watchlist_id,
            "symbol": ticker.symbol.upper(),
            "notes": ticker.notes,
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to add ticker to watchlist")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to add ticker to watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to add ticker to watchlist: {str(e)}")


@router.delete("/{watchlist_id}/tickers/{symbol}")
async def remove_ticker_from_watchlist(watchlist_id: int, symbol: str):
    """Remove a ticker from a watchlist."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlist_tickers").delete().eq("watchlist_id", watchlist_id).eq("symbol", symbol.upper()).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Ticker not found in watchlist")
        
        return {"message": f"Ticker {symbol.upper()} removed from watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to remove ticker from watchlist")
        raise HTTPException(status_code=500, detail=f"Failed to remove ticker from watchlist: {str(e)}")


@router.get("/search")
async def search_watchlists(q: str = Query(..., description="Search term for watchlist name or description")):
    """Search watchlists by name or description."""
    if not db.is_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        result = db.supabase.table("watchlists").select("*").or_(f"name.ilike.%{q}%,description.ilike.%{q}%").execute()
        return result.data
    except Exception as e:
        logging.exception("Failed to search watchlists")
        raise HTTPException(status_code=500, detail=f"Failed to search watchlists: {str(e)}")
