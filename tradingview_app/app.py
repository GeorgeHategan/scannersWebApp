from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import duckdb
import os
from datetime import datetime
import random
import time

app = FastAPI(title="Market Microstructure Analysis Platform")

# Add CORS middleware for web deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
USE_MOTHERDUCK = os.getenv("USE_MOTHERDUCK", "false").lower() == "true"
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
DATABASE_NAME = os.getenv("DATABASE_NAME", "marketflow")
LOCAL_DB_PATH = os.getenv("LOCAL_DATABASE_PATH", "../taq_data.duckdb")

def get_database_connection():
    """Get database connection - MotherDuck for production, local for development"""
    if USE_MOTHERDUCK and MOTHERDUCK_TOKEN:
        # Connect to MotherDuck cloud database
        connection_string = f"md:{DATABASE_NAME}?motherduck_token={MOTHERDUCK_TOKEN}"
        print(f"🦆 Connecting to MotherDuck database: {DATABASE_NAME}")
        return duckdb.connect(connection_string)
    else:
        # Fallback to local database for development
        if os.path.exists(LOCAL_DB_PATH):
            print(f"📁 Using local database: {LOCAL_DB_PATH}")
            return duckdb.connect(LOCAL_DB_PATH)
        else:
            print("⚠️ No database available, using sample data")
            return None

templates = Jinja2Templates(directory="templates")

# Serve static files (TradingView JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")


def generate_sample_data():
    """Generate sample market data for demonstration"""
    import random
    import time
    
    base_price = 150.0
    timestamps = []
    prices = []
    volumes = []
    
    current_time = int(time.time()) - 86400  # 24 hours ago
    
    for i in range(100):  # Generate 100 data points
        timestamps.append(current_time + i * 300)  # 5-minute intervals
        price_change = random.uniform(-2.0, 2.0)
        base_price = max(base_price + price_change, 100.0)  # Minimum $100
        prices.append(round(base_price, 2))
        volumes.append(random.randint(1000, 50000))
    
    return {
        't': timestamps,
        'o': prices,
        'h': [p + random.uniform(0, 2) for p in prices],
        'l': [p - random.uniform(0, 2) for p in prices],
        'c': prices,
        'v': volumes
    }

# -----------------------------
# 📈 Frontend route
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, symbol: str = "AAPL"):
    return templates.TemplateResponse("index.html", {"request": request, "symbol": symbol})


@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {"status": "ok", "message": "Market Analysis Platform is working!", "version": "1.0.1"}


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
    """Get OHLC data for TradingView"""
    try:
        con = get_database_connection()
        if not con:
            # Return sample data if no database available
            return generate_sample_data()
        
        query = """
        SELECT
            CAST(EXTRACT(EPOCH FROM TimeBarStart) AS INTEGER) as t,
            CAST(Open AS DOUBLE) as o,
            CAST(High AS DOUBLE) as h, 
            CAST(Low AS DOUBLE) as l,
            CAST(Close AS DOUBLE) as c,
            CAST(Volume AS INTEGER) as v
        FROM taq_1min 
        WHERE Ticker = ?
        ORDER BY TimeBarStart
        LIMIT 1000
        """
        
        result = con.execute(query, [symbol]).fetchall()
        con.close()
        
        if not result:
            return {"s": "no_data"}
        
        # Convert to TradingView format
        data = {
            't': [r[0] for r in result],
            'o': [r[1] for r in result],
            'h': [r[2] for r in result],
            'l': [r[3] for r in result],
            'c': [r[4] for r in result],
            'v': [r[5] for r in result],
            's': 'ok'
        }
        return data
        
    except Exception as e:
        print(f"Error in get_history: {e}")
        return generate_sample_data()


# -----------------------------
# � Spread data endpoint
# -----------------------------
@app.get("/api/spread")
def get_spread_data(symbol: str):
    """Get min and max spread data for overlay"""
    try:
        con = get_database_connection()
        if not con:
            # Return sample spread data
            return {"s": "ok", "min_spread": [0.01, 0.015, 0.012], "max_spread": [0.02, 0.025, 0.022]}
        
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
        for idx, row in df.iterrows():
            time_str = row["TimeBarStart"]
            date_val = row["Date"]
            hour, minute = map(int, time_str.split(':'))
            # Use the actual date from the database
            year, month, day = map(int, date_val.split('-'))
            dt = datetime(year, month, day, hour, minute)
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
        
    except Exception as e:
        print(f"Error in get_spread_data: {e}")
        # Return sample spread data
        return {"s": "ok", "min_spread": [0.01, 0.015, 0.012], "max_spread": [0.02, 0.025, 0.022]}


# -----------------------------
# � VWAP and other indicators endpoint
# -----------------------------
@app.get("/api/indicators")
def get_indicators(symbol: str):
    """Get VWAP and other technical indicators for overlay"""
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "vwap": [150.5, 151.2, 150.8], "total_trades": [100, 120, 95]}
        
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
        for idx, row in df.iterrows():
            time_str = row["TimeBarStart"]
            date_val = row["Date"]
            hour, minute = map(int, time_str.split(':'))
            year, month, day = map(int, date_val.split('-'))
            dt = datetime(year, month, day, hour, minute)
            timestamps.append(int(dt.timestamp()))

        return {
            "s": "ok",
            "t": timestamps,
            "vwap": df["vwap"].tolist(),
            "trade_at_bid": df["TradeAtBid"].tolist(),
            "trade_at_ask": df["TradeAtAsk"].tolist(),
            "total_trades": df["TotalTrades"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_indicators: {e}")
        return {"s": "ok", "vwap": [150.5, 151.2, 150.8], "total_trades": [100, 120, 95]}


# -----------------------------
# Symbol search endpoint (optional)
# -----------------------------
@app.get("/api/volume")
def get_volume_data(symbol: str):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "volume": [1000, 1200, 950], "total_trades": [50, 60, 45]}
        
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
        for idx, row in df.iterrows():
            time_str = row["TimeBarStart"]
            date_val = row["Date"]
            hour, minute = map(int, time_str.split(':'))
            year, month, day = map(int, date_val.split('-'))
            dt = datetime(year, month, day, hour, minute)
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
        
    except Exception as e:
        print(f"Error in get_volume_data: {e}")
        return {"s": "ok", "volume": [1000, 1200, 950], "total_trades": [50, 60, 45]}


@app.get("/api/liquidity")
def get_liquidity_data(symbol: str):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "open_bid_size": [100, 150, 200], "open_ask_size": [120, 180, 220]}
        
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
        for idx, row in df.iterrows():
            time_str = row["TimeBarStart"]
            date_val = row["Date"]
            hour, minute = map(int, time_str.split(':'))
            year, month, day = map(int, date_val.split('-'))
            dt = datetime(year, month, day, hour, minute)
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
        
    except Exception as e:
        print(f"Error in get_liquidity_data: {e}")
        return {"s": "ok", "open_bid_size": [100, 150, 200], "open_ask_size": [120, 180, 220]}


@app.get("/api/flow")
def get_flow_data(symbol: str):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "trade_at_bid": [50, 60, 45], "trade_at_ask": [40, 55, 35]}
        
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
        for idx, row in df.iterrows():
            time_str = row["TimeBarStart"]
            date_val = row["Date"]
            hour, minute = map(int, time_str.split(':'))
            year, month, day = map(int, date_val.split('-'))
            dt = datetime(year, month, day, hour, minute)
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
        
    except Exception as e:
        print(f"Error in get_flow_data: {e}")
        return {"s": "ok", "trade_at_bid": [50, 60, 45], "trade_at_ask": [40, 55, 35]}


@app.get("/api/symbols")
def search_symbol(symbol: str):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        result = con.execute(f"""
            SELECT DISTINCT Ticker FROM taq_1min
            WHERE UPPER(Ticker) LIKE UPPER('%{symbol}%')
            LIMIT 20
        """).fetchall()
        return [r[0] for r in result]
        
    except Exception as e:
        print(f"Error in search_symbol: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]