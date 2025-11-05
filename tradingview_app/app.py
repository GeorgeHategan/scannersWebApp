from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import duckdb
import os
from datetime import datetime

app = FastAPI(title="Market Microstructure Analysis Platform")

# Add CORS middleware for web deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths - Handle both local development and production
DB_PATH = os.getenv("DATABASE_PATH", "../taq_data.duckdb")
if not os.path.exists(DB_PATH):
    # Try alternative paths for deployment
    alternative_paths = ["./taq_data.duckdb", "taq_data.duckdb", "../taq_data.duckdb"]
    for path in alternative_paths:
        if os.path.exists(path):
            DB_PATH = path
            break

templates = Jinja2Templates(directory="templates")

# Serve static files (TradingView JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------
# 📈 Frontend route
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("index.html", {"request": request, "symbol": symbol})


@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {"status": "ok", "message": "Server is working!"}


@app.get("/spread")
def spread_page(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("spread_new.html", {"request": request, "symbol": symbol})

@app.get("/vwap")
def vwap_page(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("vwap.html", {"request": request, "symbol": symbol})


@app.get("/volume")
def volume_page(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("volume.html", {"request": request, "symbol": symbol})


@app.get("/liquidity")
def liquidity_page(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("liquidity.html", {"request": request, "symbol": symbol})


@app.get("/flow")
def flow_page(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("flow.html", {"request": request, "symbol": symbol})


# -----------------------------
# 🔍 Data API for chart
# -----------------------------
@app.get("/api/history")
def get_history(symbol: str, resolution: str = "60", from_: int = 0, to: int = 9999999999):
    """TradingView-compatible UDF datafeed endpoint"""
    con = duckdb.connect(DB_PATH)
    
    # Your data is for AAPL on 2020-01-28
    query = f"""
        SELECT 
            TimeBarStart,
            FirstTradePrice as open,
            HighTradePrice as high,
            LowTradePrice as low,
            LastTradePrice as close,
            Volume as volume,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    # Convert time format to timestamps for TradingView
    # Your data is for 2020-01-28, so we'll create proper timestamps
    timestamps = []
    for time_str in df["TimeBarStart"]:
        # Convert "HH:MM" format to timestamp for 2020-01-28
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    # Handle NaN values by replacing with None or previous valid value
    df = df.ffill()  # Forward fill NaN values
    df = df.fillna(0)  # Fill any remaining NaN with 0

    return {
        "s": "ok",
        "t": timestamps,
        "o": df["open"].tolist(),
        "h": df["high"].tolist(),
        "l": df["low"].tolist(),
        "c": df["close"].tolist(),
        "v": df["volume"].tolist(),
    }


# -----------------------------
# � Spread data endpoint
# -----------------------------
@app.get("/api/spread")
def get_spread_data(symbol: str):
    """Get min and max spread data for overlay"""
    con = duckdb.connect(DB_PATH)
    
    query = f"""
        SELECT 
            TimeBarStart,
            MinSpread,
            MaxSpread,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    # Convert time format to timestamps for TradingView
    timestamps = []
    for time_str in df["TimeBarStart"]:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    # Handle NaN values in spread data
    df = df.ffill()  # Forward fill NaN values
    df = df.fillna(0)  # Fill any remaining NaN with 0

    return {
        "s": "ok",
        "t": timestamps,
        "min_spread": df["MinSpread"].tolist(),
        "max_spread": df["MaxSpread"].tolist(),
    }


# -----------------------------
# � VWAP and other indicators endpoint
# -----------------------------
@app.get("/api/indicators")
def get_indicators(symbol: str):
    """Get VWAP and other technical indicators for overlay"""
    con = duckdb.connect(DB_PATH)
    
    query = f"""
        SELECT 
            TimeBarStart,
            VolumeWeightPrice as vwap,
            TradeAtBid,
            TradeAtAsk,
            TotalTrades,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    # Handle NaN values
    df = df.ffill()
    df = df.fillna(0)

    # Convert time format to timestamps
    timestamps = []
    for time_str in df["TimeBarStart"]:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    return {
        "s": "ok",
        "t": timestamps,
        "vwap": df["vwap"].tolist(),
        "trade_at_bid": df["TradeAtBid"].tolist(),
        "trade_at_ask": df["TradeAtAsk"].tolist(),
        "total_trades": df["TotalTrades"].tolist(),
    }


# -----------------------------
# Symbol search endpoint (optional)
# -----------------------------
@app.get("/api/volume")
def get_volume_data(symbol: str):
    con = duckdb.connect(DB_PATH)
    query = f"""
        SELECT
            TimeBarStart,
            Volume,
            TotalTrades,
            UptickVolume,
            DowntickVolume,
            RepeatUptickVolume,
            RepeatDowntickVolume,
            UnknownTickVolume,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    df = df.ffill().fillna(0)
    timestamps = []
    for time_str in df["TimeBarStart"]:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    return {
        "s": "ok",
        "t": timestamps,
        "volume": df["Volume"].tolist(),
        "total_trades": df["TotalTrades"].tolist(),
        "uptick_volume": df["UptickVolume"].tolist(),
        "downtick_volume": df["DowntickVolume"].tolist(),
        "repeat_uptick": df["RepeatUptickVolume"].tolist(),
        "repeat_downtick": df["RepeatDowntickVolume"].tolist(),
        "unknown_tick": df["UnknownTickVolume"].tolist(),
    }


@app.get("/api/liquidity")
def get_liquidity_data(symbol: str):
    con = duckdb.connect(DB_PATH)
    query = f"""
        SELECT
            TimeBarStart,
            OpenBidSize,
            OpenAskSize,
            CloseBidSize,
            CloseAskSize,
            NBBOQuoteCount,
            TimeWeightBid,
            TimeWeightAsk,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    df = df.ffill().fillna(0)
    timestamps = []
    for time_str in df["TimeBarStart"]:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    return {
        "s": "ok",
        "t": timestamps,
        "open_bid_size": df["OpenBidSize"].tolist(),
        "open_ask_size": df["OpenAskSize"].tolist(),
        "close_bid_size": df["CloseBidSize"].tolist(),
        "close_ask_size": df["CloseAskSize"].tolist(),
        "nbbo_quote_count": df["NBBOQuoteCount"].tolist(),
        "time_weight_bid": df["TimeWeightBid"].tolist(),
        "time_weight_ask": df["TimeWeightAsk"].tolist(),
    }


@app.get("/api/flow")
def get_flow_data(symbol: str):
    con = duckdb.connect(DB_PATH)
    query = f"""
        SELECT
            TimeBarStart,
            TradeAtBid,
            TradeAtBidMid,
            TradeAtMid,
            TradeAtMidAsk,
            TradeAtAsk,
            TradeAtCrossOrLocked,
            TradeToMidVolWeight,
            TradeToMidVolWeightRelative,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}'
        ORDER BY TimeBarStart
    """
    df = con.execute(query).df()

    if df.empty:
        return {"s": "no_data"}

    df = df.ffill().fillna(0)
    timestamps = []
    for time_str in df["TimeBarStart"]:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(2020, 1, 28, hour, minute)
        timestamps.append(int(dt.timestamp()))

    return {
        "s": "ok",
        "t": timestamps,
        "trade_at_bid": df["TradeAtBid"].tolist(),
        "trade_at_bid_mid": df["TradeAtBidMid"].tolist(),
        "trade_at_mid": df["TradeAtMid"].tolist(),
        "trade_at_mid_ask": df["TradeAtMidAsk"].tolist(),
        "trade_at_ask": df["TradeAtAsk"].tolist(),
        "trade_at_cross": df["TradeAtCrossOrLocked"].tolist(),
        "trade_to_mid_weight": df["TradeToMidVolWeight"].tolist(),
        "trade_to_mid_relative": df["TradeToMidVolWeightRelative"].tolist(),
    }


@app.get("/api/symbols")
def search_symbol(symbol: str):
    con = duckdb.connect(DB_PATH)
    result = con.execute(f"""
        SELECT DISTINCT Ticker FROM taq_1min
        WHERE UPPER(Ticker) LIKE UPPER('%{symbol}%')
        LIMIT 20
    """).fetchall()
    return [r[0] for r in result]