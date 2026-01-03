#!/usr/bin/env python3
"""
Create daily aggregated table from intraday data
Only uses regular market hours: 9:30 AM - 4:00 PM ET
"""
import duckdb
import pandas as pd

# Connect to database (read-write mode)
con = duckdb.connect('/Users/george/Documents/GitHub/orderFlow_datamanager/taq_database.duckdb')

print("Creating daily_aggregated table from regular market hours (9:30 AM - 4:00 PM)...")

# Drop existing table if it exists
con.execute("DROP TABLE IF EXISTS daily_aggregated")

# Create aggregated daily data - ONLY regular hours
query = """
CREATE TABLE daily_aggregated AS
SELECT 
    Ticker,
    Date,
    
    -- OHLC (First/Last bars of the day)
    (SELECT OpenBidPrice FROM taq_1min t2 
     WHERE t2.Ticker = t1.Ticker AND t2.Date = t1.Date 
     AND t2.TimeBarStart >= '09:30:00' AND t2.TimeBarStart < '16:00:00'
     ORDER BY TimeBarStart LIMIT 1) as open,
    MAX(HighTradePrice) as high,
    MIN(LowTradePrice) as low,
    (SELECT CloseAskPrice FROM taq_1min t2 
     WHERE t2.Ticker = t1.Ticker AND t2.Date = t1.Date 
     AND t2.TimeBarStart >= '09:30:00' AND t2.TimeBarStart < '16:00:00'
     ORDER BY TimeBarStart DESC LIMIT 1) as close,
    
    -- Last trade price for compatibility
    (SELECT LastTradePrice FROM taq_1min t2 
     WHERE t2.Ticker = t1.Ticker AND t2.Date = t1.Date 
     AND t2.TimeBarStart >= '09:30:00' AND t2.TimeBarStart < '16:00:00'
     ORDER BY TimeBarStart DESC LIMIT 1) as last_price,
    
    -- Volume & Trades
    SUM(Volume) as total_volume,
    SUM(TotalTrades) as total_trades,
    SUM(UptickVolume) as uptick_volume,
    SUM(DowntickVolume) as downtick_volume,
    SUM(RepeatUptickVolume) as repeat_uptick_volume,
    SUM(RepeatDowntickVolume) as repeat_downtick_volume,
    
    -- Spread
    MIN(MinSpread) as min_spread,
    MAX(MaxSpread) as max_spread,
    AVG(MinSpread) as avg_spread,
    
    -- VWAP (volume-weighted average price)
    SUM(VolumeWeightPrice * Volume) / NULLIF(SUM(Volume), 0) as vwap,
    
    -- Liquidity
    AVG(OpenBidSize) as avg_bid_size,
    AVG(OpenAskSize) as avg_ask_size,
    AVG(CloseBidSize) as avg_close_bid_size,
    AVG(CloseAskSize) as avg_close_ask_size,
    AVG(OpenBidSize + OpenAskSize) as avg_total_liquidity,
    SUM(NBBOQuoteCount) as total_quote_count,
    
    -- Flow (order flow imbalance)
    SUM(TradeAtBid) as trades_at_bid,
    SUM(TradeAtAsk) as trades_at_ask,
    SUM(TradeAtMid) as trades_at_mid,
    
    -- Delta
    SUM(UptickVolume - DowntickVolume) as volume_delta,
    
    -- Accumulation metrics
    SUM(CASE WHEN UptickVolume > DowntickVolume THEN Volume ELSE 0 END) as accumulation_volume,
    SUM(CASE WHEN UptickVolume < DowntickVolume THEN Volume ELSE 0 END) as distribution_volume,
    
    -- Count of bars
    COUNT(*) as bar_count
    
FROM taq_1min t1
WHERE TimeBarStart >= '09:30:00' 
  AND TimeBarStart < '16:00:00'
GROUP BY Ticker, Date
ORDER BY Ticker, Date
"""

con.execute(query)

# Get row count and sample data
count = con.execute("SELECT COUNT(*) FROM daily_aggregated").fetchone()[0]
print(f"\n✅ Created daily_aggregated table with {count:,} rows")

print("\nSample data (first 5 rows):")
sample = con.execute("""
    SELECT Ticker, Date, open, high, low, close, total_volume, 
           total_trades, vwap, min_spread, max_spread
    FROM daily_aggregated 
    ORDER BY Ticker, Date 
    LIMIT 5
""").fetchdf()
print(sample)

print("\nData summary by ticker:")
summary = con.execute("""
    SELECT 
        Ticker,
        COUNT(*) as days,
        MIN(Date) as first_date,
        MAX(Date) as last_date,
        SUM(total_volume) as total_volume,
        AVG(total_trades) as avg_daily_trades
    FROM daily_aggregated
    GROUP BY Ticker
    ORDER BY Ticker
""").fetchdf()
print(summary)

con.close()
print("\n✅ Daily aggregation complete!")
