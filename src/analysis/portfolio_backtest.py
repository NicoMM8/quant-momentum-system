"""
Portfolio Momentum Backtester
-----------------------------
Simulates rotational momentum models across a custom universe or S&P 500 constituents.
Incorporates institutional-grade friction modeling:
- Transaction costs (commissions + slippage)
- Survivorship-bias free evaluation (Point-in-Time universe handling)
- Sector concentration limits
- Daily Volatility (ATR) filtering
- Macro regime filtering (SMA200)
- Dividend yield modeling
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt

# Static fallback sector definitions for testing without DB access
_SECTOR_MAP_FALLBACK = {
    'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'META': 'Tech', 'NVDA': 'Tech',
    'AMD': 'Tech', 'INTC': 'Tech', 'AVGO': 'Tech', 'ORCL': 'Tech', 'CRM': 'Tech',
    'ADBE': 'Tech', 'CSCO': 'Tech', 'IBM': 'Tech', 'NOW': 'Tech', 'INTU': 'Tech',
    'AMAT': 'Tech', 'LRCX': 'Tech', 'KLAC': 'Tech', 'MCHP': 'Tech', 'TXN': 'Tech',
    'QCOM': 'Tech', 'MU': 'Tech', 'ADI': 'Tech', 'ARM': 'Tech', 'SMCI': 'Tech',
    'CRWD': 'Tech', 'SNOW': 'Tech', 'DDOG': 'Tech', 'ZS': 'Tech', 'NET': 'Tech',
    'PANW': 'Tech', 'FTNT': 'Tech', 'PLTR': 'Tech', 'SHOP': 'Tech', 'TEAM': 'Tech',
    'TSM': 'Semis', 'ASML': 'Semis', 'SNPS': 'Semis', 'CDNS': 'Semis', 'ON': 'Semis',
    'SWKS': 'Semis', 'QRVO': 'Semis', 'STM': 'Semis', 'MRVL': 'Semis', 'ANET': 'Semis',
    'JPM': 'Finance', 'BAC': 'Finance', 'WFC': 'Finance', 'GS': 'Finance', 'MS': 'Finance',
    'C': 'Finance', 'BLK': 'Finance', 'SCHW': 'Finance', 'AXP': 'Finance', 'V': 'Finance',
    'MA': 'Finance', 'PYPL': 'Finance', 'SQ': 'Finance', 'COIN': 'Finance', 'HOOD': 'Finance',
    'BX': 'Finance', 'KKR': 'Finance', 'APO': 'Finance', 'ICE': 'Finance', 'CME': 'Finance',
    'UNH': 'Health', 'JNJ': 'Health', 'PFE': 'Health', 'MRK': 'Health', 'ABBV': 'Health',
    'LLY': 'Health', 'TMO': 'Health', 'ABT': 'Health', 'DHR': 'Health', 'BMY': 'Health',
    'AMGN': 'Health', 'GILD': 'Health', 'VRTX': 'Health', 'REGN': 'Health', 'MRNA': 'Health',
    'ISRG': 'Health', 'SYK': 'Health', 'MDT': 'Health', 'BSX': 'Health', 'ZTS': 'Health',
    'AMZN': 'Consumer', 'TSLA': 'Consumer', 'WMT': 'Consumer', 'HD': 'Consumer', 'COST': 'Consumer',
    'MCD': 'Consumer', 'SBUX': 'Consumer', 'NKE': 'Consumer', 'LOW': 'Consumer', 'TGT': 'Consumer',
    'TJX': 'Consumer', 'ROST': 'Consumer', 'LULU': 'Consumer', 'ULTA': 'Consumer', 'CMG': 'Consumer',
    'DG': 'Consumer', 'DLTR': 'Consumer', 'ORLY': 'Consumer', 'AZO': 'Consumer', 'BBY': 'Consumer',
    'PG': 'Staples', 'KO': 'Staples', 'PEP': 'Staples', 'PM': 'Staples', 'MO': 'Staples',
    'CL': 'Staples', 'KMB': 'Staples', 'GIS': 'Staples', 'K': 'Staples', 'KHC': 'Staples',
    'MDLZ': 'Staples', 'HSY': 'Staples', 'STZ': 'Staples', 'EL': 'Staples', 'CLX': 'Staples',
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy', 'EOG': 'Energy',
    'OXY': 'Energy', 'HAL': 'Energy', 'BKR': 'Energy', 'DVN': 'Energy', 'FANG': 'Energy',
    'MRO': 'Energy', 'HES': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy', 'MPC': 'Energy',
    'CAT': 'Industrial', 'DE': 'Industrial', 'HON': 'Industrial', 'UPS': 'Industrial', 'BA': 'Industrial',
    'RTX': 'Industrial', 'LMT': 'Industrial', 'GD': 'Industrial', 'NOC': 'Industrial', 'GE': 'Industrial',
    'UNP': 'Industrial', 'CSX': 'Industrial', 'FDX': 'Industrial', 'WM': 'Industrial', 'ETN': 'Industrial',
    'NFLX': 'Comms', 'DIS': 'Comms', 'CMCSA': 'Comms', 'T': 'Comms', 'VZ': 'Comms',
    'TMUS': 'Comms', 'CHTR': 'Comms', 'WBD': 'Comms', 'PARA': 'Comms', 'FOXA': 'Comms',
    'AMT': 'REIT', 'PLD': 'REIT', 'CCI': 'REIT', 'EQIX': 'REIT', 'PSA': 'REIT',
    'SPG': 'REIT', 'O': 'REIT', 'DLR': 'REIT', 'WELL': 'REIT', 'SBAC': 'REIT',
    'NEE': 'Utility', 'DUK': 'Utility', 'SO': 'Utility', 'AEP': 'Utility', 'D': 'Utility',
    'SRE': 'Utility', 'XEL': 'Utility', 'ED': 'Utility', 'PCG': 'Utility', 'EXC': 'Utility',
    'LIN': 'Materials', 'APD': 'Materials', 'SHW': 'Materials', 'FCX': 'Materials', 'NEM': 'Materials',
    'NUE': 'Materials', 'STLD': 'Materials', 'ALB': 'Materials', 'MOS': 'Materials', 'CF': 'Materials',
    'F': 'Auto', 'GM': 'Auto', 'RIVN': 'Auto', 'LCID': 'Auto', 'NIO': 'Auto',
    'LI': 'Auto', 'XPEV': 'Auto', 'TM': 'Auto', 'HMC': 'Auto', 'RACE': 'Auto',
    'SPY': 'ETF', 'QQQ': 'ETF', 'IWM': 'ETF', 'DIA': 'ETF', 'VOO': 'ETF',
    'VTI': 'ETF', 'XLF': 'ETF', 'XLK': 'ETF', 'XLE': 'ETF', 'XLV': 'ETF',
    'SMH': 'ETF', 'SOXX': 'ETF', 'ARKK': 'ETF', 'GLD': 'ETF', 'TLT': 'ETF',
    'MSTR': 'Crypto', 'MARA': 'Crypto', 'RIOT': 'Crypto', 'CLSK': 'Crypto',
    'GME': 'Meme', 'AMC': 'Meme', 'BB': 'Meme', 'NOK': 'Meme',
}

def _load_sector_map(db_path: str) -> dict:
    """
    Dynamically loads the sector mapping from the SQLite 'assets' table.
    Falls back to a static mapping if unavailable.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT symbol, sector FROM assets", conn)
            if not df.empty:
                return dict(zip(df['symbol'], df['sector']))
    except Exception:
        pass
    return _SECTOR_MAP_FALLBACK.copy()

class PortfolioMomentumBacktester:
    """
    Core simulation engine for cross-sectional momentum strategies.
    Supports point-in-time survivorship bias correction and transaction friction modeling.
    """
    
    def __init__(self, db_path, universe_list, initial_capital=10000.0, point_in_time_file=None):
        """
        Args:
            db_path (str): SQLite database path containing market data.
            universe_list (list): Default list of tickers to evaluate.
            initial_capital (float): Starting balance in USD.
            point_in_time_file (str): JSON file path mapping YYYY-MM to exact historical constituents.
        """
        self.db_path = db_path
        self.universe = universe_list
        self.initial_capital = initial_capital
        self.results = None
        self.trade_count = 0
        self.total_costs = 0
        self.trade_log = []
        self.point_in_time_file = point_in_time_file
        self.point_in_time_dict = {}
        
        if self.point_in_time_file:
            try:
                import json
                with open(self.point_in_time_file, 'r') as f:
                    self.point_in_time_dict = json.load(f)
            except Exception as e:
                print(f"Warning: Point-in-Time universe load failed: {e}")
        
        self.sector_map = _load_sector_map(db_path)

    def load_data_matrix(self):
        """Vectorizes historical market data into a dense DataFrame matrix."""
        conn = sqlite3.connect(self.db_path)
        
        df_all = pd.read_sql("SELECT datetime, symbol, close, high, low FROM market_data", conn)
        conn.close()
        
        df_all['datetime'] = pd.to_datetime(df_all['datetime'])
        df_all = df_all.drop_duplicates(subset=['datetime', 'symbol'], keep='last')
        
        prices = df_all.pivot(index='datetime', columns='symbol', values='close').ffill()
        prices.dropna(axis=1, thresh=250, inplace=True)
        
        highs = df_all.pivot(index='datetime', columns='symbol', values='high').ffill()
        lows = df_all.pivot(index='datetime', columns='symbol', values='low').ffill()
        
        return prices, highs, lows

    def calculate_atr(self, prices, highs, lows, period=14):
        """Calculates Average True Range (ATR) normalized as a percentage of price."""
        prev_close = prices.shift(1)
        
        tr1 = highs - lows
        tr2 = (highs - prev_close).abs()
        tr3 = (lows - prev_close).abs()
        
        true_range = np.maximum(np.maximum(tr1, tr2), tr3)
        atr_pct = true_range.rolling(window=period).mean() / prices
        
        return atr_pct

    def apply_sector_limit(self, ranked_stocks, max_per_sector=2):
        """Enforces a strict threshold on sector allocation iteratively."""
        selected = []
        sector_counts = {}
        
        for stock in ranked_stocks:
            sector = self.sector_map.get(stock, 'Other')
            current_count = sector_counts.get(sector, 0)
            
            if current_count < max_per_sector:
                selected.append(stock)
                sector_counts[sector] = current_count + 1
        
        return selected

    def run_backtest(
        self, 
        top_n=5, 
        lookback_months=3, 
        rebalance_freq='ME', 
        crash_prob=0.0,
        transaction_cost=0.001,
        skip_recent_month=True,
        max_volatility_pct=0.05,
        max_per_sector=2,
        dividend_yield=0.015,
        market_filter_ticker=None,
        sma_window=200,
        start_date=None
    ):
        """
        Executes the cross-sectional momentum vector backtest.
        
        Iterates over historical rebalance periods, applying multi-factor 
        constraints and transaction friction dynamically.
        """
        prices, highs, lows = self.load_data_matrix()
        daily_returns = prices.pct_change(fill_method=None)
        atr_pct = self.calculate_atr(prices, highs, lows)
        
        try:
            rebalance_dates = prices.resample(rebalance_freq).last().index
        except:
            rebalance_dates = prices.resample('ME').last().index
            
        if start_date is not None:
            rebalance_dates = rebalance_dates[rebalance_dates >= pd.to_datetime(start_date)]
            
        if len(rebalance_dates) == 0:
            return pd.DataFrame()
        
        equity_curve = [self.initial_capital]
        dates = [rebalance_dates[0]]
        capital = self.initial_capital
        previous_holdings = []
        self.total_dividends = 0
        monthly_dividend_rate = dividend_yield / 12
        
        self.trade_count = 0
        self.total_costs = 0
        
        if market_filter_ticker and market_filter_ticker in prices.columns:
            market_sma = prices[market_filter_ticker].rolling(window=sma_window).mean()
        else:
            market_sma = None

        lookback_days = int(lookback_months * 21)
        skip_days = 21 if skip_recent_month else 0

        for i in range(len(rebalance_dates) - 1):
            curr_date = rebalance_dates[i]
            next_date = rebalance_dates[i+1]
            
            try:
                idx_loc = prices.index.get_indexer(pd.DatetimeIndex([curr_date]), method='pad')[0]
            except:
                continue

            if idx_loc < lookback_days + skip_days:
                dates.append(next_date)
                equity_curve.append(capital)
                continue

            # Momentum Computation
            if skip_recent_month:
                p_now = prices.iloc[idx_loc - skip_days]
                p_past = prices.iloc[idx_loc - skip_days - lookback_days]
            else:
                p_now = prices.iloc[idx_loc]
                p_past = prices.iloc[idx_loc - lookback_days]
            
            momentum = (p_now / p_past) - 1
            
            # Point-In-Time Universe Mapping
            if self.point_in_time_dict:
                month_str = curr_date.strftime('%Y-%m')
                if month_str in self.point_in_time_dict:
                    active_tickers = self.point_in_time_dict[month_str]
                    valid_idx = [t for t in momentum.index if t in active_tickers]
                    momentum = momentum[valid_idx]
            
            # Volatility Filter
            current_atr = atr_pct.iloc[idx_loc]
            momentum_filtered = momentum[current_atr < max_volatility_pct]
            if momentum_filtered.empty:
                momentum_filtered = momentum
            
            # Ranking and Sector constraints
            ranked = momentum_filtered.sort_values(ascending=False)
            top_candidates = ranked.head(top_n * 3).index.tolist()
            top_stocks = self.apply_sector_limit(top_candidates, max_per_sector)[:top_n]
            
            # Market Regime Evaluator
            if market_sma is not None:
                current_market_price = prices[market_filter_ticker].iloc[idx_loc]
                current_market_sma = market_sma.iloc[idx_loc]
                
                if pd.notna(current_market_sma) and current_market_price < current_market_sma:
                    top_stocks = [] # Trigger total liquidation
                    
            if not top_stocks and not previous_holdings:
                dates.append(next_date)
                equity_curve.append(capital)
                continue

            # Rebalance Friction (Slippage + Commission)
            new_stocks = set(top_stocks) - set(previous_holdings)
            sold_stocks = set(previous_holdings) - set(top_stocks)
            
            for stock in sold_stocks:
                if stock in prices.columns:
                    exec_price = prices[stock].iloc[idx_loc]
                    self.trade_log.append({
                        'Date': curr_date.date(),
                        'Ticker': stock,
                        'Action': 'SELL',
                        'Price': exec_price
                    })

            for stock in new_stocks:
                if stock in prices.columns:
                    exec_price = prices[stock].iloc[idx_loc]
                    self.trade_log.append({
                        'Date': curr_date.date(),
                        'Ticker': stock,
                        'Action': 'BUY',
                        'Price': exec_price
                    })

            num_trades = len(new_stocks) + len(sold_stocks)
            self.trade_count += num_trades
            
            period_cost = transaction_cost * num_trades * (capital / max(1, top_n))
            self.total_costs += period_cost
            capital -= period_cost
            
            previous_holdings = top_stocks.copy()

            # Sub-period returns
            period_returns = daily_returns.loc[curr_date:next_date, top_stocks].iloc[1:].copy()
            
            if period_returns.empty:
                dates.append(next_date)
                equity_curve.append(capital)
                continue

            # Extreme event risk simulation
            if crash_prob > 0:
                for stock in top_stocks:
                    if np.random.random() < crash_prob:
                        if not period_returns.empty:
                            col_idx = period_returns.columns.get_loc(stock)
                            period_returns.iloc[0, col_idx] = -0.99
                            if len(period_returns) > 1:
                                period_returns.iloc[1:, col_idx] = 0.0

            # Cumulative vector
            portfolio_daily_ret = period_returns.mean(axis=1)
            cum_ret = (1 + portfolio_daily_ret).cumprod()
            
            if not cum_ret.empty:
                capital = capital * cum_ret.iloc[-1]
            
            # Dividend Distribution Simulation (DRIP)
            period_dividends = capital * monthly_dividend_rate
            self.total_dividends += period_dividends
            capital += period_dividends
            
            equity_curve.append(capital)
            dates.append(next_date)

        self.results = pd.DataFrame({'Equity': equity_curve}, index=dates)
        return self.results

    def get_max_drawdown(self):
        """Calculates Maximum Drawdown (MDD) of the equity curve."""
        if self.results is None or self.results.empty:
            return 0.0
        roll_max = self.results['Equity'].cummax()
        drawdown = self.results['Equity'] / roll_max - 1.0
        return drawdown.min()

    def plot_results(self, benchmark_symbol='SPY'):
        """Generates performance visualization vs. broad market benchmark."""
        if self.results is None or self.results.empty:
            return

        total_ret = (self.results['Equity'].iloc[-1] / self.initial_capital) - 1
        days = (self.results.index[-1] - self.results.index[0]).days
        cagr = (self.results['Equity'].iloc[-1] / self.initial_capital) ** (365.25/days) - 1 if days > 0 else 0
        
        mdd = self.get_max_drawdown()
        
        plt.figure(figsize=(12, 6))
        
        plt.plot(
            self.results.index, 
            self.results['Equity'], 
            label=f'Momentum Portfolio (CAGR: {cagr:.2%} | MDD: {mdd:.2%})', 
            color='blue',
            linewidth=2
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            bench = pd.read_sql(
                "SELECT datetime, close FROM market_data WHERE symbol=?", 
                conn,
                params=(benchmark_symbol,)
            )
            conn.close()
            
            bench['datetime'] = pd.to_datetime(bench['datetime'])
            bench.set_index('datetime', inplace=True)
            bench = bench.reindex(self.results.index, method='ffill')
            bench['Normalized'] = (bench['close'] / bench['close'].iloc[0]) * self.initial_capital
            
            bench_ret = (bench['Normalized'].iloc[-1] / self.initial_capital) - 1
            bench_cagr = (bench['Normalized'].iloc[-1] / self.initial_capital) ** (365.25/days) - 1 if days > 0 else 0
            
            plt.plot(
                bench.index, 
                bench['Normalized'], 
                label=f'Benchmark [{benchmark_symbol}] (CAGR: {bench_cagr:.2%})', 
                color='gray', 
                linestyle='--'
            )
        except Exception as e:
            print(f"Failed to load benchmark: {e}")

        plt.title("Institutional Momentum Strategy vs Market Baseline")
        plt.yscale('log')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

        print(f"Performance Summary:")
        print(f"  Final Equity:    ${self.results['Equity'].iloc[-1]:,.2f}")
        print(f"  CAGR:            {cagr:.2%}")
        print(f"  Max Drawdown:    {mdd:.2%}")
        print(f"  Executed Trades: {self.trade_count}")
        print(f"  Cap. Cost:       ${self.total_costs:,.2f}")