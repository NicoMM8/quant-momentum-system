"""
Point-in-Time Momentum Backtest Simulation
------------------------------------------
Execution script for the production-grade momentum strategy.
incorporates:
  - 0.10% transaction costs (slippage + commissions)
  - Skip-month momentum scoring (reversion filter)
  - Volatility filtering via daily Average True Range (ATR)
  - Sector allocation limits
  - Macro regime filtering via 200-day SMA of a broad market proxy (SPY)
"""

import os
import pandas as pd
from src.utils.static_universe import MY_HUGE_UNIVERSE
from src.analysis.portfolio_backtest import PortfolioMomentumBacktester

DB_FILE = os.path.join(os.getcwd(), "quant.db")

def main():
    """Execute the point-in-time momentum backtest."""
    print("Initiating Point-in-Time Momentum Backtest...")
    
    # Optional Data Ingestion (uncomment if data sync is required)
    # from src.data.ingestion import DataIngestor
    # ingestor = DataIngestor(DB_FILE)
    # ingestor.tickers = MY_HUGE_UNIVERSE
    # ingestor.sync_market_data(period="20y")

    # Initialize Backtester with historical S&P 500 constituents
    bt = PortfolioMomentumBacktester(
        db_path=DB_FILE,
        universe_list=MY_HUGE_UNIVERSE,
        point_in_time_file='sp500_historical_universe.json'
    )
    
    # Run the simulation
    results = bt.run_backtest(
        top_n=8,
        lookback_months=3,
        rebalance_freq='ME',
        crash_prob=0.001,
        
        # Institutional realism parameters
        transaction_cost=0.001,
        skip_recent_month=True,
        max_volatility_pct=0.15,
        max_per_sector=3,
        dividend_yield=0.015,
        
        # Market regime filter
        market_filter_ticker='SPY',
        sma_window=200,             
        
        # Range
        start_date='2016-03-01'
    )
    
    # Export execution logs for audit
    if hasattr(bt, 'trade_log') and getattr(bt, 'trade_log'):
        trades_df = pd.DataFrame(bt.trade_log)
        trades_df = trades_df.sort_values(by=['Date', 'Action'])
        output_file = os.path.join(os.getcwd(), 'trades_log.csv')
        trades_df.to_csv(output_file, index=False)
        print(f"Trade log exported to: {output_file}")

    # Visualize results
    bt.plot_results(benchmark_symbol='SPY')

def run_comparison():
    """
    Executes a comparison between a naive momentum baseline and the filtered 
    institutional version. Useful for quantifying the impact of transaction costs, 
    regime filters, and sector bounds.
    """
    print("Comparing Baseline Momentum vs Institutional Momentum")
    
    bt_baseline = PortfolioMomentumBacktester(DB_FILE, MY_HUGE_UNIVERSE)
    
    # Baseline simulation
    print("Running Baseline...")
    results_baseline = bt_baseline.run_backtest(
        top_n=8,
        lookback_months=3,
        rebalance_freq='ME',
        crash_prob=0.0,
        transaction_cost=0.0,
        skip_recent_month=False,
        max_volatility_pct=1.0,
        max_per_sector=999
    )
    baseline_final = results_baseline['Equity'].iloc[-1]
    
    # Institutional simulation
    print("Running Institutional...")
    bt_inst = PortfolioMomentumBacktester(DB_FILE, MY_HUGE_UNIVERSE)
    results_inst = bt_inst.run_backtest(
        top_n=8,
        lookback_months=3,
        rebalance_freq='ME',
        crash_prob=0.001,
        transaction_cost=0.001,
        skip_recent_month=True,
        max_volatility_pct=0.05,
        max_per_sector=2
    )
    inst_final = results_inst['Equity'].iloc[-1]
    
    print("\nComparison Results:")
    print(f"  Baseline Eq:      ${baseline_final:,.2f}")
    print(f"  Institutional Eq: ${inst_final:,.2f}")
    print(f"  Delta:            {((inst_final/baseline_final) - 1)*100:+.2f}%")

if __name__ == "__main__":
    main()