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
LOCAL_DB_PATH = os.getenv("LOCAL_DATABASE_PATH", "/Users/george/Documents/GitHub/orderFlow_datamanager/taq_database.duckdb")

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
            # Use read_only=True to allow multiple connections
            return duckdb.connect(LOCAL_DB_PATH, read_only=True)
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
async def home(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("index.html", {"request": request, "symbol": symbol})


@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {"status": "ok", "message": "Market Analysis Platform is working!", "version": "1.0.1"}


@app.get("/spread")
def spread_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("spread_new.html", {"request": request, "symbol": symbol})

@app.get("/vwap")
def vwap_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("vwap.html", {"request": request, "symbol": symbol})


@app.get("/volume")
def volume_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("volume.html", {"request": request, "symbol": symbol})


@app.get("/liquidity")
def liquidity_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("liquidity.html", {"request": request, "symbol": symbol})


@app.get("/flow")
def flow_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("flow.html", {"request": request, "symbol": symbol})


@app.get("/accumulation")
def accumulation_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("accumulation.html", {"request": request, "symbol": symbol})


@app.get("/delta")
def delta_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("delta.html", {"request": request, "symbol": symbol})


@app.get("/signal")
def signal_page(request: Request, symbol: str = "AMD"):
    return templates.TemplateResponse("signal.html", {"request": request, "symbol": symbol})


@app.get("/documentation")
def docs_page(request: Request):
    return templates.TemplateResponse("docs.html", {"request": request})


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
def get_spread_data(symbol: str, date: int = None):
    """Get min and max spread data for overlay"""
    try:
        con = get_database_connection()
        if not con:
            # Return sample spread data
            return {"s": "ok", "min_spread": [0.01, 0.015, 0.012], "max_spread": [0.02, 0.025, 0.022]}
        
        date_filter = f"AND Date = {date}" if date else ""
        query = f"""
        SELECT 
            TimeBarStart,
            MinSpread,
            MaxSpread,
            LastTradePrice,
            Date
        FROM taq_1min
        WHERE Ticker = '{symbol.upper()}' {date_filter}
        ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        # Convert time format to timestamps for TradingView
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            # Handle both datetime.time objects and strings
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            # Convert integer date (YYYYMMDD) to year, month, day
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
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
            "last_price": df["LastTradePrice"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_spread_data: {e}")
        # Return sample spread data
        return {"s": "ok", "min_spread": [0.01, 0.015, 0.012], "max_spread": [0.02, 0.025, 0.022]}


# -----------------------------
# � VWAP and other indicators endpoint
# -----------------------------
@app.get("/api/indicators")
def get_indicators(symbol: str, date: int = None):
    """Get VWAP and other technical indicators for overlay"""
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "vwap": [150.5, 151.2, 150.8], "total_trades": [100, 120, 95]}
        
        date_filter = f"AND Date = {date}" if date else ""
        query = f"""
            SELECT 
                TimeBarStart,
                VolumeWeightPrice as vwap,
                TradeAtBid,
                TradeAtAsk,
                TotalTrades,
                LastTradePrice,
                Date
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
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
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            # Handle both datetime.time objects and strings
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            # Convert integer date (YYYYMMDD) to year, month, day
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
            dt = datetime(year, month, day, hour, minute)
            timestamps.append(int(dt.timestamp()))

        return {
            "s": "ok",
            "t": timestamps,
            "vwap": df["vwap"].tolist(),
            "trade_at_bid": df["TradeAtBid"].tolist(),
            "trade_at_ask": df["TradeAtAsk"].tolist(),
            "total_trades": df["TotalTrades"].tolist(),
            "last_price": df["LastTradePrice"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_indicators: {e}")
        return {"s": "ok", "vwap": [150.5, 151.2, 150.8], "total_trades": [100, 120, 95]}


# -----------------------------
# Symbol search endpoint (optional)
# -----------------------------
@app.get("/api/volume")
def get_volume_data(symbol: str, date: int = None):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "volume": [1000, 1200, 950], "total_trades": [50, 60, 45]}
        
        date_filter = f"AND Date = {date}" if date else ""
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
                LastTradePrice,
                Date
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            # Handle both datetime.time objects and strings
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            # Convert integer date (YYYYMMDD) to year, month, day
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
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
            "last_price": df["LastTradePrice"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_volume_data: {e}")
        return {"s": "ok", "volume": [1000, 1200, 950], "total_trades": [50, 60, 45]}


@app.get("/api/liquidity")
def get_liquidity_data(symbol: str, date: int = None):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "open_bid_size": [100, 150, 200], "open_ask_size": [120, 180, 220]}
        
        date_filter = f"AND Date = {date}" if date else ""
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
                LastTradePrice,
                Date
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            # Handle both datetime.time objects and strings
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            # Convert integer date (YYYYMMDD) to year, month, day
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
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
            "last_price": df["LastTradePrice"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_liquidity_data: {e}")
        return {"s": "ok", "open_bid_size": [100, 150, 200], "open_ask_size": [120, 180, 220]}


@app.get("/api/flow")
def get_flow_data(symbol: str, date: int = None):
    try:
        con = get_database_connection()
        if not con:
            # Return sample data
            return {"s": "ok", "trade_at_bid": [50, 60, 45], "trade_at_ask": [40, 55, 35]}
        
        date_filter = f"AND Date = {date}" if date else ""
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
                LastTradePrice,
                Date
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            # Handle both datetime.time objects and strings
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            # Convert integer date (YYYYMMDD) to year, month, day
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
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
            "last_price": df["LastTradePrice"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_flow_data: {e}")
        return {"s": "ok", "trade_at_bid": [50, 60, 45], "trade_at_ask": [40, 55, 35]}


@app.get("/api/symbols")
def search_symbol(symbol: str = ""):
    try:
        con = get_database_connection()
        if not con:
            return ["AMD", "MSFT", "GOOGL", "NVDA", "INTC"]
        
        if symbol:
            result = con.execute(f"""
                SELECT DISTINCT Ticker FROM taq_1min
                WHERE UPPER(Ticker) LIKE UPPER('%{symbol}%')
                ORDER BY Ticker
                LIMIT 20
            """).fetchall()
        else:
            result = con.execute("""
                SELECT DISTINCT Ticker FROM taq_1min
                ORDER BY Ticker
            """).fetchall()
        return [r[0] for r in result]
        
    except Exception as e:
        print(f"Error in search_symbol: {e}")
        return ["AMD", "MSFT", "GOOGL", "NVDA", "INTC"]


@app.get("/api/dates")
def get_available_dates(symbol: str):
    """Get available dates for a specific ticker"""
    try:
        con = get_database_connection()
        if not con:
            return {"dates": [20200128]}
        
        result = con.execute(f"""
            SELECT DISTINCT Date FROM taq_1min
            WHERE Ticker = '{symbol.upper()}'
            ORDER BY Date DESC
        """).fetchall()
        dates = [r[0] for r in result]
        return {"dates": dates, "count": len(dates)}
        
    except Exception as e:
        print(f"Error in get_available_dates: {e}")
        return {"dates": [], "error": str(e)}


@app.get("/api/accumulation")
def get_accumulation_data(symbol: str, date: int = None):
    """Get accumulation/distribution and buying pressure data"""
    try:
        con = get_database_connection()
        if not con:
            return {"s": "no_data"}
        
        date_filter = f"AND Date = {date}" if date else ""
        query = f"""
            SELECT
                TimeBarStart,
                Date,
                TradeAtBid,
                TradeAtBidMid,
                TradeAtMid,
                TradeAtMidAsk,
                TradeAtAsk,
                TradeAtCrossOrLocked,
                Volume,
                TotalTrades,
                UptickVolume,
                DowntickVolume,
                RepeatUptickVolume,
                RepeatDowntickVolume,
                OpenBidSize,
                OpenAskSize,
                CloseBidSize,
                CloseAskSize,
                FirstTradePrice,
                LastTradePrice,
                HighTradePrice,
                LowTradePrice,
                VolumeWeightPrice,
                TradeToMidVolWeight
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
            dt = datetime(year, month, day, hour, minute)
            timestamps.append(int(dt.timestamp()))

        # Calculate derived metrics
        # Buy Volume = TradeAtAsk + TradeAtMidAsk (aggressive + passive buying)
        buy_volume = (df["TradeAtAsk"] + df["TradeAtMidAsk"]).tolist()
        # Sell Volume = TradeAtBid + TradeAtBidMid (aggressive + passive selling)
        sell_volume = (df["TradeAtBid"] + df["TradeAtBidMid"]).tolist()
        # Delta = Buy - Sell (positive = buying pressure)
        delta = (df["TradeAtAsk"] + df["TradeAtMidAsk"] - df["TradeAtBid"] - df["TradeAtBidMid"]).tolist()
        # Cumulative Delta
        cumulative_delta = (df["TradeAtAsk"] + df["TradeAtMidAsk"] - df["TradeAtBid"] - df["TradeAtBidMid"]).cumsum().tolist()
        
        return {
            "s": "ok",
            "t": timestamps,
            "trade_at_bid": df["TradeAtBid"].tolist(),
            "trade_at_bid_mid": df["TradeAtBidMid"].tolist(),
            "trade_at_mid": df["TradeAtMid"].tolist(),
            "trade_at_mid_ask": df["TradeAtMidAsk"].tolist(),
            "trade_at_ask": df["TradeAtAsk"].tolist(),
            "trade_at_cross": df["TradeAtCrossOrLocked"].tolist(),
            "volume": df["Volume"].tolist(),
            "total_trades": df["TotalTrades"].tolist(),
            "uptick_volume": df["UptickVolume"].tolist(),
            "downtick_volume": df["DowntickVolume"].tolist(),
            "repeat_uptick": df["RepeatUptickVolume"].tolist(),
            "repeat_downtick": df["RepeatDowntickVolume"].tolist(),
            "open_bid_size": df["OpenBidSize"].tolist(),
            "open_ask_size": df["OpenAskSize"].tolist(),
            "close_bid_size": df["CloseBidSize"].tolist(),
            "close_ask_size": df["CloseAskSize"].tolist(),
            "first_price": df["FirstTradePrice"].tolist(),
            "last_price": df["LastTradePrice"].tolist(),
            "high_price": df["HighTradePrice"].tolist(),
            "low_price": df["LowTradePrice"].tolist(),
            "vwap": df["VolumeWeightPrice"].tolist(),
            "trade_to_mid": df["TradeToMidVolWeight"].tolist(),
            # Derived metrics
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "delta": delta,
            "cumulative_delta": cumulative_delta,
        }
        
    except Exception as e:
        print(f"Error in get_accumulation_data: {e}")
        return {"s": "error", "message": str(e)}


@app.get("/api/delta")
def get_delta_data(symbol: str, date: int = None):
    """Get delta and momentum data for directional analysis"""
    try:
        con = get_database_connection()
        if not con:
            return {"s": "no_data"}
        
        date_filter = f"AND Date = {date}" if date else ""
        query = f"""
            SELECT
                TimeBarStart,
                Date,
                TradeAtBid,
                TradeAtBidMid,
                TradeAtMid,
                TradeAtMidAsk,
                TradeAtAsk,
                Volume,
                TotalTrades,
                UptickVolume,
                DowntickVolume,
                RepeatUptickVolume,
                RepeatDowntickVolume,
                OpenBidSize,
                OpenAskSize,
                CloseBidSize,
                CloseAskSize,
                LastTradePrice,
                VolumeWeightPrice,
                TradeToMidVolWeight,
                TradeToMidVolWeightRelative
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
            dt = datetime(year, month, day, hour, minute)
            timestamps.append(int(dt.timestamp()))

        # Calculate Delta metrics
        buy_vol = df["TradeAtAsk"] + df["TradeAtMidAsk"]
        sell_vol = df["TradeAtBid"] + df["TradeAtBidMid"]
        delta = buy_vol - sell_vol
        cumulative_delta = delta.cumsum()
        
        # Tick Delta
        uptick_total = df["UptickVolume"] + df["RepeatUptickVolume"]
        downtick_total = df["DowntickVolume"] + df["RepeatDowntickVolume"]
        tick_delta = uptick_total - downtick_total
        cumulative_tick_delta = tick_delta.cumsum()
        
        # Order Book Imbalance
        bid_size = (df["OpenBidSize"] + df["CloseBidSize"]) / 2
        ask_size = (df["OpenAskSize"] + df["CloseAskSize"]) / 2
        total_size = bid_size + ask_size
        book_imbalance = ((bid_size - ask_size) / total_size.replace(0, 1) * 100)
        
        # Delta percentage (normalized)
        total_vol = buy_vol + sell_vol
        delta_pct = (delta / total_vol.replace(0, 1) * 100)
        
        return {
            "s": "ok",
            "t": timestamps,
            "delta": delta.tolist(),
            "cumulative_delta": cumulative_delta.tolist(),
            "tick_delta": tick_delta.tolist(),
            "cumulative_tick_delta": cumulative_tick_delta.tolist(),
            "book_imbalance": book_imbalance.tolist(),
            "delta_pct": delta_pct.tolist(),
            "buy_volume": buy_vol.tolist(),
            "sell_volume": sell_vol.tolist(),
            "uptick_volume": uptick_total.tolist(),
            "downtick_volume": downtick_total.tolist(),
            "volume": df["Volume"].tolist(),
            "last_price": df["LastTradePrice"].tolist(),
            "vwap": df["VolumeWeightPrice"].tolist(),
            "trade_to_mid": df["TradeToMidVolWeight"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_delta_data: {e}")
        return {"s": "error", "message": str(e)}


@app.get("/api/signal")
def get_signal_data(symbol: str, date: int = None):
    """Get combined signal score for price direction prediction"""
    try:
        con = get_database_connection()
        if not con:
            return {"s": "no_data"}
        
        date_filter = f"AND Date = {date}" if date else ""
        query = f"""
            SELECT
                TimeBarStart,
                Date,
                TradeAtBid,
                TradeAtBidMid,
                TradeAtMid,
                TradeAtMidAsk,
                TradeAtAsk,
                Volume,
                UptickVolume,
                DowntickVolume,
                RepeatUptickVolume,
                RepeatDowntickVolume,
                OpenBidSize,
                OpenAskSize,
                CloseBidSize,
                CloseAskSize,
                LastTradePrice,
                VolumeWeightPrice,
                TradeToMidVolWeight,
                TradeToMidVolWeightRelative,
                MinSpread,
                MaxSpread
            FROM taq_1min
            WHERE Ticker = '{symbol.upper()}' {date_filter}
            ORDER BY Date, TimeBarStart
        """
        df = con.execute(query).df()

        if df.empty:
            return {"s": "no_data"}

        df = df.ffill().fillna(0)
        timestamps = []
        for idx, row in df.iterrows():
            time_val = row["TimeBarStart"]
            date_val = row["Date"]
            if hasattr(time_val, 'hour'):
                hour, minute = time_val.hour, time_val.minute
            else:
                hour, minute = map(int, str(time_val).split(':')[:2])
            year = date_val // 10000
            month = (date_val % 10000) // 100
            day = date_val % 100
            dt = datetime(year, month, day, hour, minute)
            timestamps.append(int(dt.timestamp()))

        # === SIGNAL 1: Buy/Sell Delta Score (-100 to +100) ===
        buy_vol = df["TradeAtAsk"] + df["TradeAtMidAsk"]
        sell_vol = df["TradeAtBid"] + df["TradeAtBidMid"]
        total_vol = buy_vol + sell_vol
        delta_score = ((buy_vol - sell_vol) / total_vol.replace(0, 1) * 100).clip(-100, 100)
        
        # === SIGNAL 2: Tick Delta Score (-100 to +100) ===
        uptick = df["UptickVolume"] + df["RepeatUptickVolume"]
        downtick = df["DowntickVolume"] + df["RepeatDowntickVolume"]
        total_tick = uptick + downtick
        tick_score = ((uptick - downtick) / total_tick.replace(0, 1) * 100).clip(-100, 100)
        
        # === SIGNAL 3: Order Book Imbalance Score (-100 to +100) ===
        bid_size = (df["OpenBidSize"] + df["CloseBidSize"]) / 2
        ask_size = (df["OpenAskSize"] + df["CloseAskSize"]) / 2
        total_size = bid_size + ask_size
        book_score = ((bid_size - ask_size) / total_size.replace(0, 1) * 100).clip(-100, 100)
        
        # === SIGNAL 4: Trade-to-Mid Score (where trades happen relative to mid) ===
        # Positive = trades closer to ask (buying), Negative = trades closer to bid (selling)
        mid_score = (df["TradeToMidVolWeightRelative"] * 100).clip(-100, 100)
        
        # === COMBINED SIGNAL (weighted average) ===
        # Weights: Delta 40%, Tick 25%, Book 20%, Mid 15%
        combined_signal = (
            delta_score * 0.40 +
            tick_score * 0.25 +
            book_score * 0.20 +
            mid_score * 0.15
        ).clip(-100, 100)
        
        # === CUMULATIVE SIGNAL (running score) ===
        cumulative_signal = combined_signal.cumsum()
        
        # === SIGNAL STRENGTH (absolute value, 0-100) ===
        signal_strength = combined_signal.abs()
        
        # === MOMENTUM (rate of change of cumulative signal) ===
        momentum = cumulative_signal.diff().fillna(0)
        
        return {
            "s": "ok",
            "t": timestamps,
            # Individual signals
            "delta_score": delta_score.tolist(),
            "tick_score": tick_score.tolist(),
            "book_score": book_score.tolist(),
            "mid_score": mid_score.tolist(),
            # Combined
            "combined_signal": combined_signal.tolist(),
            "cumulative_signal": cumulative_signal.tolist(),
            "signal_strength": signal_strength.tolist(),
            "momentum": momentum.tolist(),
            # Price data
            "last_price": df["LastTradePrice"].tolist(),
            "vwap": df["VolumeWeightPrice"].tolist(),
            "volume": df["Volume"].tolist(),
            # Spread
            "min_spread": df["MinSpread"].tolist(),
            "max_spread": df["MaxSpread"].tolist(),
        }
        
    except Exception as e:
        print(f"Error in get_signal_data: {e}")
        return {"s": "error", "message": str(e)}