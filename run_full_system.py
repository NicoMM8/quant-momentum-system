import os
from src.data.ingestion import DataIngestor
from src.strategies.alpha.macro import MacroScannerStrategy
from src.analysis.backtest import VectorBacktester

DB_FILE = os.path.join(os.getcwd(), "quant.db")

# Sample Raw Universe for fundamental screening validation
RAW_UNIVERSE = [
    'AAPL', 'MSFT', 'NVDA', 'AMD', 'INTC',  
    'PYPL', 'SQ', 'COIN', 'HOOD',           
    'ZM', 'DOCU', 'PTON', 'NFLX',           
    'XOM', 'CVX',                           
    'JPM', 'BAC',                           
    'TSLA', 'F'                             
]

def main():
    """
    End-to-end integration test validating the entire quantitative pipeline:
    1. ETL Ingestion / Data Sourcing
    2. Fundamental Macro Screening (Alpha Generation)
    3. Technical Strategy Vector Execution
    """
    print("Initiating Pipeline Integration Test")
    
    # Phase 1: Ingestion
    print(f"[Phase 1] Bootstrapping ETL process for {len(RAW_UNIVERSE)} assets.")
    ingestor = DataIngestor(DB_FILE)
    ingestor.tickers = RAW_UNIVERSE 
    
    ingestor.sync_assets_table()
    ingestor.sync_market_data(period="3y") 
    ingestor.sync_fundamentals()

    # Phase 2: Factor Screening
    print("\n[Phase 2] Executing Fundamental Constraints Engine.")
    scanner = MacroScannerStrategy(DB_FILE)
    selected_universe = scanner.update_universe()[:3] 
    
    print(f"Fundamental screener converged on: {selected_universe}")

    # Phase 3: Technical Execution
    print("\n[Phase 3] Routing targets to Vector Simulation Engine.")
    bt = VectorBacktester(DB_FILE)

    for ticker in selected_universe:
        result = bt.run_strategy(ticker, short_window=50, long_window=200)
        
        if result is not None:
            final_ret = (result['cum_strategy'].iloc[-1] / 10000) - 1
            print(f"Target [{ticker}] Absolute Return: {final_ret:.2%}")

if __name__ == "__main__":
    main()