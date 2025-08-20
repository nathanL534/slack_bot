# app/main.py
from fastapi import FastAPI
from app.routes import router as routes_router
from app.market_data.twelvedata import router as twelvedata_router
from app.watchlist import router as watchlist_router

app = FastAPI()
app.include_router(routes_router)
app.include_router(twelvedata_router)
app.include_router(watchlist_router)
