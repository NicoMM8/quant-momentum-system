"""
S&P 500 Historical Constituents ETL
-----------------------------------
Scrapes Wikipedia's changelog to reconstruct the cross-sectional 
S&P 500 universe month-by-month over a 20-year period.
This artifacts a Point-in-Time json map used to eliminate survivorship 
bias in quantitative simulations.
"""

import pandas as pd
import json
import os
import ssl
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_historical_sp500():
    """
    Reverse-engineers the S&P 500 index composition historically.
    Outputs a structured JSON mapping YYYY-MM -> [Tickers].
    """
    logger.info("Initializing S&P 500 historical changelog extraction.")
    
    # Bypassing strict SSL validation for public wiki data
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read()
        tables = pd.read_html(html)
        current_sp500_table = tables[0]
        changes_table = tables[1]
    except Exception as e:
        logger.error(f"Failed to fetch or parse Wikipedia constituents: {e}")
        return

    # Extract currently active tickers
    current_tickers = current_sp500_table['Symbol'].tolist()
    # Normalize ticker syntax (e.g., BRK.B -> BRK-B)
    current_tickers = [str(ticker).replace('.', '-') for ticker in current_tickers]
    
    logger.info(f"Current base universe secured: {len(current_tickers)} components.")
    
    # Standardize column headers
    if isinstance(changes_table.columns, pd.MultiIndex):
        changes_table.columns = ['_'.join(col).strip() for col in changes_table.columns.values]
    
    date_col = next((col for col in changes_table.columns if 'Date' in col), None)
    added_col = next((col for col in changes_table.columns if 'Added_Ticker' in col or ('Added' in col and 'Ticker' in col)), None)
    removed_col = next((col for col in changes_table.columns if 'Removed_Ticker' in col or ('Removed' in col and 'Ticker' in col)), None)

    if not date_col or not added_col or not removed_col:
        logger.error("Wikipedia schema change detected. Requires manual ETL maintenance.")
        return

    changes_table['Date'] = pd.to_datetime(changes_table[date_col])
    changes_table = changes_table.sort_values(by='Date')

    # Retroactive Universe Reconstruction
    historical_universe = {}
    start_date = pd.Timestamp.now() - pd.DateOffset(years=20)
    monthly_dates = pd.date_range(start=start_date, end=pd.Timestamp.now(), freq='ME')

    current_set = set(current_tickers)
    changes_reverse = changes_table.sort_values(by='Date', ascending=False)
    
    logger.info("Reconstructing historical Point-In-Time vectors...")
    
    for month_end in sorted(monthly_dates, reverse=True):
        month_str = month_end.strftime('%Y-%m')
        
        # Identifies any ledger shifts that occurred strictly POST this month-end
        changes_in_future = changes_reverse[changes_reverse['Date'] > month_end]
        
        historical_set = set(current_set)
        
        for _, row in changes_in_future.iterrows():
            added_ticker = str(row[added_col]) if pd.notna(row[added_col]) else None
            removed_ticker = str(row[removed_col]) if pd.notna(row[removed_col]) else None
            
            # Reverse engineer the past: Subtract post-additions, add post-removals
            if added_ticker:
                added_ticker = added_ticker.replace('.', '-')
                historical_set.discard(added_ticker)
                
            if removed_ticker:
                removed_ticker = removed_ticker.replace('.', '-')
                historical_set.add(removed_ticker)
                
        historical_universe[month_str] = sorted(list(historical_set))
    
    output_path = os.path.join(os.getcwd(), 'sp500_historical_universe.json')
    with open(output_path, 'w') as f:
        json.dump(historical_universe, f, indent=4)
        
    logger.info(f"Point-In-Time generation successful: {len(historical_universe)} historical periods mapped.")
    logger.info(f"Registry stored at: {output_path}")

    # Integrity Check
    sample_month = list(historical_universe.keys())[0]
    sample_10y = list(historical_universe.keys())[-1]
    
    logger.info(f"Integrity Check [{sample_month}]: {len(historical_universe[sample_month])} valid tickers.")
    logger.info(f"Integrity Check [{sample_10y}]: {len(historical_universe[sample_10y])} valid tickers.")
    
if __name__ == "__main__":
    generate_historical_sp500()
