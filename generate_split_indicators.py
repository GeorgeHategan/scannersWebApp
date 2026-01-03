#!/usr/bin/env python3
"""
Generate two TradingView indicators with split ticker groups and full date range
"""
import duckdb
import os

# Database path
DB_PATH = '/Users/george/Documents/GitHub/orderFlow_datamanager/taq_database.duckdb'

# Split tickers into two groups
TICKERS_GROUP1 = ['ABBV', 'ABT', 'ALB', 'AMD', 'BABA', 'BIDU', 'CL', 'CMCSA', 'CRM', 'CRWD',
                  'DELL', 'DG', 'DHR', 'EOG', 'F', 'FCX', 'FSLR', 'GD', 'GDDY', 'GEV',
                  'GLW', 'GOOGL', 'GS', 'HAL', 'HPE']

TICKERS_GROUP2 = ['HSY', 'INTC', 'IP', 'JD', 'JNJ', 'KEY', 'KHC', 'LEN', 'LIN', 'LLY',
                  'MAR', 'MARA', 'MDT', 'MMM', 'MOS', 'MRVL', 'MSFT', 'NEM', 'ORCL', 'PATH',
                  'PCG', 'PFE', 'PG', 'PLTR', 'PPLT', 'RCL']

def get_spread_data(con, tickers):
    """Fetch spread data for given tickers"""
    # Get all dates
    dates_query = "SELECT DISTINCT Date FROM taq_1min ORDER BY Date"
    dates = [row[0] for row in con.execute(dates_query).fetchall()]
    
    # Get spread data for each ticker
    ticker_data = {}
    for ticker in tickers:
        query = """
        SELECT 
            Date,
            MAX(MaxSpread) as max_spread,
            AVG((CloseBidPrice + CloseAskPrice) / 2) as mid_price
        FROM taq_1min
        WHERE Ticker = ?
        GROUP BY Date
        ORDER BY Date
        """
        results = con.execute(query, [ticker]).fetchall()
        
        # Create spread percentage array
        spread_dict = {}
        for date, max_spread, mid_price in results:
            if mid_price and mid_price > 0:
                spread_pct = (max_spread / mid_price) * 10000  # basis points * 100
                spread_dict[date] = round(spread_pct, 2)
        
        # Build array in date order
        spread_array = []
        for date in dates:
            if date in spread_dict:
                spread_array.append(spread_dict[date])
            else:
                spread_array.append(0.0)  # No data for this date
        
        ticker_data[ticker] = spread_array
    
    return dates, ticker_data

def generate_pine_script(group_num, tickers, dates, ticker_data, output_file):
    """Generate Pine Script indicator"""
    
    # Split tickers into chunks for function splitting
    tickers_per_func = 10
    ticker_chunks = [tickers[i:i + tickers_per_func] for i in range(0, len(tickers), tickers_per_func)]
    
    script = f'''// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Generated from TAQ Database - Group {group_num}

//@version=5
indicator("Daily Max Spread % - Group {group_num}", shorttitle="MaxSpread%G{group_num}", overlay=false, precision=4)

// ============================================================================
// CONFIGURATION
// ============================================================================
showHistogram = input.bool(true, "Show as Histogram", group="Display")
showLine = input.bool(true, "Show Line", group="Display")
spreadColor = input.color(color.new(color.red, 0), "Spread Color", group="Display")
avgColor = input.color(color.new(color.orange, 0), "Average Color", group="Display")
avgLength = input.int(10, "Average Length", minval=1, maxval=50, group="Display")

// ============================================================================
// GROUP {group_num} TICKERS ({len(tickers)} total)
// ============================================================================
// {', '.join(tickers)}
//
// Data Coverage: {len(dates)} trading days
// Date Range: {dates[0]} to {dates[-1]}
// ============================================================================

// ============================================================================
// DATE ARRAY ({len(dates)} trading days)
// ============================================================================
var int[] dates = array.from({', '.join(map(str, dates))})

// ============================================================================
// MAX SPREAD DATA BY TICKER (stored as basis points * 100 for precision)
// ============================================================================

'''
    
    # Generate getSpreadData functions for each chunk
    for chunk_idx, chunk in enumerate(ticker_chunks):
        script += f'getSpreadData_{chunk_idx}(string ticker) =>\n'
        script += '    switch ticker\n'
        
        for ticker in chunk:
            data_str = ', '.join(map(str, ticker_data[ticker]))
            script += f'        "{ticker}" => array.from({data_str})\n'
        
        script += '        => array.new<float>(0)\n\n'
    
    # Generate main getSpreadData function
    script += '// Main function to get spread data for any ticker\n'
    script += 'getSpreadData(string ticker) =>\n'
    
    for chunk_idx, chunk in enumerate(ticker_chunks):
        ticker_list = ', '.join([f'"{t}"' for t in chunk])
        if chunk_idx == 0:
            script += f'    if array.includes(array.from({ticker_list}), ticker)\n'
        else:
            script += f'    else if array.includes(array.from({ticker_list}), ticker)\n'
        script += f'        getSpreadData_{chunk_idx}(ticker)\n'
    
    script += '    else\n'
    script += '        array.new<float>(0)\n\n'
    
    # Add main logic and plotting
    script += '''// ============================================================================
// MAIN LOGIC
// ============================================================================
currentTicker = str.replace_all(syminfo.ticker, "NASDAQ:", "")
currentTicker := str.replace_all(currentTicker, "NYSE:", "")
currentTicker := str.replace_all(currentTicker, "AMEX:", "")

spreadData = getSpreadData(currentTicker)
currentDate = year * 10000 + month * 100 + dayofmonth

var float spreadValue = na
if array.size(spreadData) > 0
    for i = 0 to array.size(dates) - 1
        if array.get(dates, i) == currentDate
            spreadValue := array.get(spreadData, i) / 100
            break

var float[] spreadHistory = array.new<float>(0)
if not na(spreadValue) and barstate.isconfirmed
    array.push(spreadHistory, spreadValue)
    if array.size(spreadHistory) > 100
        array.shift(spreadHistory)

avgSpread = array.size(spreadHistory) >= avgLength ? array.avg(array.slice(spreadHistory, array.size(spreadHistory) - avgLength, array.size(spreadHistory))) : na

// ============================================================================
// PLOTTING
// ============================================================================
plot(showHistogram ? spreadValue : na, "Max Spread %", spreadColor, style=plot.style_histogram, linewidth=4)
plot(showLine ? spreadValue : na, "Max Spread Line", spreadColor, linewidth=2)
plot(avgSpread, "Avg of Max Spread", avgColor, linewidth=2)
hline(0, "Zero", color.gray, linestyle=hline.style_dotted)

// ============================================================================
// INFO TABLE
// ============================================================================
var table infoTable = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 80), frame_color=color.gray, frame_width=1, border_width=1)

if barstate.islast
    table.cell(infoTable, 0, 0, "Symbol", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 0, currentTicker, text_color=color.yellow, text_size=size.small)
    table.cell(infoTable, 0, 1, "Date", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 1, str.tostring(currentDate), text_color=color.yellow, text_size=size.small)
    table.cell(infoTable, 0, 2, "Max Spread %", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 2, na(spreadValue) ? "N/A" : str.tostring(spreadValue, "#.####") + "%", text_color=na(spreadValue) ? color.gray : color.lime, text_size=size.small)
    table.cell(infoTable, 0, 3, "Avg Max Spread", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 3, na(avgSpread) ? "N/A" : str.tostring(avgSpread, "#.####") + "%", text_color=na(avgSpread) ? color.gray : color.orange, text_size=size.small)

alertcondition(spreadValue > 1.0, "High Max Spread Alert", "Max Spread is above 1.0%")
'''
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(script)
    
    print(f"✓ Generated {output_file}")
    print(f"  - {len(tickers)} tickers")
    print(f"  - {len(dates)} trading days")
    print(f"  - {len(ticker_chunks)} function chunks")

def main():
    # Connect to database
    con = duckdb.connect(DB_PATH, read_only=True)
    
    print("Generating Group 1 indicator...")
    dates1, ticker_data1 = get_spread_data(con, TICKERS_GROUP1)
    generate_pine_script(
        1, 
        TICKERS_GROUP1, 
        dates1, 
        ticker_data1,
        '/Users/george/Documents/GitHub/scannersWebApp/tradingview_indicators/daily_spread_group1.pine'
    )
    
    print("\nGenerating Group 2 indicator...")
    dates2, ticker_data2 = get_spread_data(con, TICKERS_GROUP2)
    generate_pine_script(
        2, 
        TICKERS_GROUP2, 
        dates2, 
        ticker_data2,
        '/Users/george/Documents/GitHub/scannersWebApp/tradingview_indicators/daily_spread_group2.pine'
    )
    
    con.close()
    print("\n✅ Both indicators generated successfully!")

if __name__ == "__main__":
    main()
