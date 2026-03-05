import os
from src.utils.static_universe import MY_HUGE_UNIVERSE
from src.analysis.portfolio_backtest import PortfolioMomentumBacktester

DB_FILE = os.path.join(os.getcwd(), "quant.db")

def main():
    """
    Executes the static-universe momentum backtest schema.
    Validates cross-sectional alpha without point-in-time constraints.
    """
    print("Initiating Momentum Backtest Environment (Static Universe)")
    
    # Optional Data Fetching
    # from src.data.ingestion import DataIngestor
    # ingestor = DataIngestor(DB_FILE)
    # ingestor.tickers = MY_HUGE_UNIVERSE
    # ingestor.sync_market_data(period="10y")

    bt = PortfolioMomentumBacktester(DB_FILE, MY_HUGE_UNIVERSE)
    
    results = bt.run_backtest(
        top_n=8,                    
        lookback_months=3,          
        rebalance_freq='ME',        
        crash_prob=0.001,           
        transaction_cost=0.001,     
        skip_recent_month=True,     
        max_volatility_pct=0.15,    
        max_per_sector=3,           
        dividend_yield=0.015        
    )
    
    bt.plot_results(benchmark_symbol='SPY')


def run_comparison():
    """
    Benchmarking function comparing naive momentum implementation 
    against the friction-adjusted (institutional) model.
    """
    print("Execution Delta Analysis: Naive vs Institutional")
    
    bt = PortfolioMomentumBacktester(DB_FILE, MY_HUGE_UNIVERSE)
    
    # Naive Model (Frictionless)
    print("Phase 1: Computing Frictionless Baseline...")
    results_original = bt.run_backtest(
        top_n=8,
        lookback_months=3,
        rebalance_freq='ME',
        crash_prob=0.0,             
        transaction_cost=0.0,       
        skip_recent_month=False,    
        max_volatility_pct=1.0,     
        max_per_sector=999          
    )
    original_final = results_original['Equity'].iloc[-1]
    
    # Friction Model
    print("Phase 2: Computing Institutional Friction Model...")
    bt2 = PortfolioMomentumBacktester(DB_FILE, MY_HUGE_UNIVERSE)
    results_v2 = bt2.run_backtest(
        top_n=8,
        lookback_months=3,
        rebalance_freq='ME',
        crash_prob=0.001,
        transaction_cost=0.001,
        skip_recent_month=True,
        max_volatility_pct=0.05,
        max_per_sector=2
    )
    v2_final = results_v2['Equity'].iloc[-1]
    
    print("\nComparative Summary:")
    print(f"  Frictionless Equity: ${original_final:,.2f}")
    print(f"  Friction Eq (Live):  ${v2_final:,.2f}")
    print(f"  Execution Drag:       {((v2_final/original_final) - 1)*100:+.2f}%")


if __name__ == "__main__":
    main()