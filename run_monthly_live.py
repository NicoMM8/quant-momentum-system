"""
Live Trading Orchestration Module
---------------------------------
Coordinates live execution logic syncing historical parameters
with the MetaTrader 5 live API. Includes identical filters (Regime, ATR, Sector, Momentum)
as the historical simulation.
"""

import os
import time
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

from src.utils.logger import get_logger
from src.utils.static_universe import MY_HUGE_UNIVERSE
from src.analysis.portfolio_backtest import _load_sector_map
from src.execution.mt5_connector import MT5Connector, map_symbol_to_mt5

logger = get_logger("live_trading")
DB_FILE = os.path.join(os.getcwd(), "quant.db")

# Strategy Configuration
TOP_N = 8
LOOKBACK_MONTHS = 3
SKIP_RECENT_MONTH = True
MAX_VOLATILITY_PCT = 0.15
MAX_PER_SECTOR = 3
TRADE_MODE = 'LIVE'

# Macro Regime Filter 
MARKET_FILTER_TICKER = 'SPY'
SMA_WINDOW = 200

def get_current_universe():
    """Retrieve the current proxy universe for execution routing."""
    return MY_HUGE_UNIVERSE

def calculate_atr(prices, highs, lows, period=14):
    """
    Compute daily ATR (Average True Range) normalized by price.
    """
    prev_close = prices.shift(1)
    tr1 = highs - lows
    tr2 = (highs - prev_close).abs()
    tr3 = (lows - prev_close).abs()
    
    true_range = np.maximum(np.maximum(tr1, tr2), tr3)
    atr = true_range.rolling(window=period).mean()
    
    return atr / prices

def apply_sector_limit(ranked_stocks, max_per_sector, sector_map):
    """
    Iterate over the rank to maintain a strict upper bound on sector exposure.
    """
    selected = []
    sector_counts = {}
    
    for stock in ranked_stocks:
        sector = sector_map.get(stock, 'Other')
        current_count = sector_counts.get(sector, 0)
        
        if current_count < max_per_sector:
            selected.append(stock)
            sector_counts[sector] = current_count + 1
            
    return selected

def generate_live_target_portfolio():
    """
    Generates the exact target portfolio based on today's pricing,
    applying momentum rules, ATR filtering, and the SMA200 market regime filter.
    Returns an empty list (100% Cash) if the regime is bearish.
    """
    logger.info("Downloading updated market data...")
    
    end_date = datetime.today()
    start_date = end_date - timedelta(days=350)
    
    universe = get_current_universe()
    if MARKET_FILTER_TICKER and MARKET_FILTER_TICKER not in universe:
        universe.append(MARKET_FILTER_TICKER)
    
    data = yf.download(
        universe, 
        start=start_date.strftime('%Y-%m-%d'), 
        end=(end_date + timedelta(days=1)).strftime('%Y-%m-%d'), 
        progress=False, 
        ignore_tz=True
    )
    
    prices = data['Close'].ffill()
    highs = data['High'].ffill()
    lows = data['Low'].ffill()
    
    logger.info("Computing factor models and asset allocation...")
    
    today_idx = prices.index[-1]
    skip_date = today_idx - pd.DateOffset(months=1)
    
    try:
        skip_idx_loc = prices.index.get_indexer(pd.DatetimeIndex([skip_date]), method='pad')[0]
    except Exception:
        logger.error("Insufficient market depth for skip-month alignment.")
        return []
        
    start_dt = skip_date - pd.DateOffset(months=LOOKBACK_MONTHS)
    try:
        start_idx_loc = prices.index.get_indexer(pd.DatetimeIndex([start_dt]), method='pad')[0]
    except Exception:
        logger.error("Insufficient market depth for momentum lookback alignment.")
        return []
    
    # Calculate Cross-Sectional Momentum
    p_now = prices.iloc[skip_idx_loc]
    p_past = prices.iloc[start_idx_loc]
    momentum = (p_now / p_past) - 1
    
    # Apply Volatility Filter
    atr_pct = calculate_atr(prices, highs, lows)
    current_atr = atr_pct.iloc[-1]
    low_vol_mask = current_atr < MAX_VOLATILITY_PCT
    momentum_filtered = momentum[low_vol_mask]
    
    # Macro Regime Filter Evaluator (SPY SMA200 Check)
    if MARKET_FILTER_TICKER and MARKET_FILTER_TICKER in prices.columns:
        market_series = prices[MARKET_FILTER_TICKER]
        if len(market_series) >= SMA_WINDOW:
            market_sma = market_series.rolling(window=SMA_WINDOW).mean()
            
            current_market_price = market_series.iloc[-1]
            current_market_sma = market_sma.iloc[-1]
            
            logger.info(f"Market Regime [{MARKET_FILTER_TICKER}]: Price = ${current_market_price:.2f} | SMA200 = ${current_market_sma:.2f}")
            
            if pd.notna(current_market_sma) and current_market_price < current_market_sma:
                logger.warning(f"Regime Switch Triggered: {MARKET_FILTER_TICKER} is below SMA{SMA_WINDOW}. Halting long bias.")
                logger.warning("Moving to 100% Cash.")
                return []
        else:
            logger.warning(f"SMA window insufficient for core filter. Req: {SMA_WINDOW}, Avail: {len(market_series)}.")
            
    if MARKET_FILTER_TICKER in momentum_filtered.index:
        momentum_filtered = momentum_filtered.drop(index=[MARKET_FILTER_TICKER])
        
    ranked = momentum_filtered.sort_values(ascending=False)
    
    sector_map = _load_sector_map(DB_FILE)
    top_candidates = ranked.index.tolist()
    top_n_portfolio = apply_sector_limit(top_candidates, MAX_PER_SECTOR, sector_map)[:TOP_N]
    
    print("\n[Target Allocation]")
    for i, ticker in enumerate(top_n_portfolio, 1):
        sector = sector_map.get(ticker, 'Other')
        mom_val = ranked[ticker] * 100
        atr_val = current_atr[ticker] * 100
        print(f" {i}. {ticker:<5} | Mom: +{mom_val:.1f}% | ATR: {atr_val:.1f}% | Sec: {sector}")
        
    return top_n_portfolio

def execute_trades(target_portfolio):
    """
    Routings and order management against the MT5 Live Bridge.
    Reconciles current open operations and manages sizing limits.
    """
    logger.info("Initializing MetaTrader 5 API Bridge...")
    
    connector = MT5Connector()
    if TRADE_MODE == 'PAPER':
        connector._paper_mode = True
        
    if not connector.connect():
        logger.error("Failed to establish API handshake with MT5 terminal.")
        return
        
    acc = connector.get_account_info()
    logger.info(f"Nominal Margin Ready: {acc.balance} {acc.currency}")
    
    positions = connector.get_positions()
    current_tickers = [pos.symbol for pos in positions]
    
    logger.info(f"Active Exposure Lines ({len(current_tickers)}): {current_tickers}")
    
    # Portfolio Reconciliation
    sell_list = [pos for pos in positions if pos.symbol not in target_portfolio]
    buy_list = [sym for sym in target_portfolio if sym not in current_tickers]
    
    if not sell_list and not buy_list:
        logger.info("Portfolio reconciliation confirmed. No delta identified.")
        connector.disconnect()
        return

    # Liquidate existing exposure not resident in update model
    for pos in sell_list:
        print(f"[LIQUIDATE] Closing Position: {pos.symbol}")
        res = connector.close_position(pos.ticket)
        if hasattr(res, 'success') and not res.success:
             logger.error(f"Closure failed on ticket {pos.ticket}: {getattr(res, 'comment', 'Unknown')}")
    
    time.sleep(1) # Margin flush synchronization
    acc = connector.get_account_info()
    
    # Generate long side delta
    if buy_list:
        capital_per_trade = acc.balance / TOP_N
        
        for sym in buy_list:
            mt5_sym = map_symbol_to_mt5(sym, connector._symbol_suffix)
            info = connector.get_symbol_info(sym)
            
            if not info:
                logger.error(f"Routing logic invalid for MT5 mapping {mt5_sym}.")
                continue
                
            tick = connector.get_tick(sym)
            if not tick:
                logger.error(f"Bid/Ask depth unavailable: {mt5_sym}")
                continue
                
            ask_price = tick['ask']
            if ask_price <= 0:
                continue
                
            volume = capital_per_trade / ask_price
            step = info.volume_step if info.volume_step > 0 else 1.0
            volume = round(volume / step) * step
            volume = max(info.volume_min, min(info.volume_max, volume))
            
            print(f"[EXECUTE] BUY {sym} -> qty: {volume} @ ${ask_price:.2f}")
            
            res = connector.place_order(symbol=sym, order_type="BUY", volume=volume)
            if hasattr(res, 'success') and not res.success:
                 logger.error(f"Execution rejected for {sym}: {getattr(res, 'comment', 'Unknown')}")
                 
    connector.disconnect()
    logger.info("Rebalancing Execution Finalized.")

if __name__ == "__main__":
    print("Quant System - Base Environment")
    print("-------------------------------")
    target_p = generate_live_target_portfolio()
    
    if target_p:
        execute_trades(target_p)
    else:
        logger.info("Portfolio halted/cash mapping forced. System on standby.")
