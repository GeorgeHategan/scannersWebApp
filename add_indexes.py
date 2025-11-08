#!/usr/bin/env python3
"""
Add indexes to MotherDuck database for improved query performance
"""
import os
import duckdb

def add_indexes():
    # Connect to MotherDuck
    database_name = os.environ.get('DATABASE_NAME', 'marketflow')
    print(f"🦆 Connecting to MotherDuck database: {database_name}")
    con = duckdb.connect(f'md:{database_name}')
    
    indexes = [
        # Single column index on Ticker (most selective filter)
        ("idx_ticker", "CREATE INDEX IF NOT EXISTS idx_ticker ON taq_1min(Ticker)"),
        
        # Composite index on Ticker + TimeBarStart (covers WHERE + ORDER BY)
        ("idx_ticker_time", "CREATE INDEX IF NOT EXISTS idx_ticker_time ON taq_1min(Ticker, TimeBarStart)"),
        
        # Composite index on Ticker + Date (for date-based queries)
        ("idx_ticker_date", "CREATE INDEX IF NOT EXISTS idx_ticker_date ON taq_1min(Ticker, Date)"),
        
        # Full composite index (optimal for all queries)
        ("idx_ticker_date_time", "CREATE INDEX IF NOT EXISTS idx_ticker_date_time ON taq_1min(Ticker, Date, TimeBarStart)"),
    ]
    
    print("\n📊 Adding indexes to improve query performance...")
    
    for idx_name, sql in indexes:
        try:
            print(f"\n  Creating {idx_name}...")
            con.execute(sql)
            print(f"  ✅ {idx_name} created successfully")
        except Exception as e:
            print(f"  ⚠️  Error creating {idx_name}: {e}")
    
    # Verify indexes
    print("\n\n📋 Current indexes:")
    try:
        result = con.execute("SELECT * FROM duckdb_indexes() WHERE table_name = 'taq_1min'").fetchall()
        if result:
            for row in result:
                print(f"  ✓ {row}")
        else:
            print("  No indexes found")
    except Exception as e:
        print(f"  Could not verify indexes: {e}")
    
    con.close()
    print("\n✅ Index creation complete!")

if __name__ == "__main__":
    # Check for required environment variables
    if not os.environ.get('MOTHERDUCK_TOKEN'):
        print("❌ Error: MOTHERDUCK_TOKEN environment variable not set")
        exit(1)
    
    add_indexes()
