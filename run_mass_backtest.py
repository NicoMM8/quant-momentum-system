import pandas as pd
import os
import time
from tqdm import tqdm
from src.utils.static_universe import MY_HUGE_UNIVERSE
from src.data.ingestion import DataIngestor
from src.analysis.backtest import VectorBacktester

DB_FILE = os.path.join(os.getcwd(), "quant.db")

def main():
    """
    Executes a mass vector backtest across the entire static universe.
    Primarily used for validating factor robustness across multiple assets.
    Default Strategy: Golden Cross (SMA50 > SMA200)
    """
    print("Initiating Mass Vector Backtest (Golden Cross Strategy)")
    
    # Optional Data Sync
    # print("Verifying market data integrity...")
    # ingestor = DataIngestor(DB_FILE)
    # ingestor.tickers = MY_HUGE_UNIVERSE
    # ingestor.sync_market_data(period="10y") 

    print("Executing simulation envelope...")
    bt = VectorBacktester(DB_FILE)
    
    results = []
    errors_log = []
    
    for ticker in tqdm(MY_HUGE_UNIVERSE, desc="Simulating"):
        try:
            df = bt.run_strategy(ticker, short_window=50, long_window=200)
            
            if df is not None:
                final_strat_ret = (df['cum_strategy'].iloc[-1] / bt.initial_capital) - 1
                final_market_ret = (df['cum_market'].iloc[-1] / bt.initial_capital) - 1
                alpha = final_strat_ret - final_market_ret
                
                results.append({
                    'symbol': ticker,
                    'strat_return': final_strat_ret,
                    'market_return': final_market_ret,
                    'alpha': alpha
                })
            else:
                errors_log.append(f"{ticker}: Insufficient depth (< 200 candles)")
                
        except Exception as e:
            error_msg = f"Execution failed for {ticker}: {str(e)}"
            if len(errors_log) < 3: 
                print(error_msg)
            errors_log.append(error_msg)
            continue

    if not results:
        print("Simulation aborted: No valid trajectories generated.")
        for err in errors_log[:5]:
            print(err)
        return

    df_res = pd.DataFrame(results)
    
    # Portfolio-level metrics Aggregation
    avg_return = df_res['strat_return'].mean()
    avg_market = df_res['market_return'].mean()
    win_rate = len(df_res[df_res['strat_return'] > 0]) / len(df_res)
    beats_market = len(df_res[df_res['alpha'] > 0]) / len(df_res)
    
    print("\nPortfolio Summary")
    print("-" * 40)
    print(f"Total Assets Evaluated: {len(df_res)}")
    print(f"Average Strategy Return: {avg_return:.2%}")
    print(f"Average Buy&Hold Return: {avg_market:.2%}")
    print(f"Average Alpha:           {avg_return - avg_market:.2%}")
    print("-" * 40)
    print(f"Absolute Win Rate (> 0%): {win_rate:.1%}")
    print(f"Relative Win Rate (Alpha > 0%): {beats_market:.1%}")
    
    print("\nTop 5 Trajectories (By Alpha):")
    print(df_res.sort_values(by='alpha', ascending=False).head(5)[['symbol', 'strat_return', 'alpha']])

if __name__ == "__main__":
    main()