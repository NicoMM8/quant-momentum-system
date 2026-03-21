import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt

class VectorBacktester:
    def __init__(self, db_path, initial_capital=10000.0):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.results = {}

    def load_data(self, symbol):
        query = "SELECT datetime, close FROM market_data WHERE symbol = ? ORDER BY datetime ASC"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql(query, conn, params=(symbol,))

            if df.empty:
                return df

            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df['close'] = df['close'].astype(float)
            return df

    def run_strategy(self, symbol, short_window=50, long_window=200):
        df = self.load_data(symbol)

        if df.empty or len(df) < long_window:
            return None

        df['SMA_S'] = df['close'].rolling(window=short_window).mean()
        df['SMA_L'] = df['close'].rolling(window=long_window).mean()

        df['signal'] = np.where(df['SMA_S'] > df['SMA_L'], 1.0, 0.0)

        df['trade'] = df['signal'].diff()

        df['market_return'] = df['close'].pct_change(fill_method=None)

        df['strategy_return'] = df['signal'].shift(1) * df['market_return']

        df['strategy_return'] = df['strategy_return'].fillna(0)
        df['market_return'] = df['market_return'].fillna(0)

        df['cum_strategy'] = (1 + df['strategy_return']).cumprod() * self.initial_capital
        df['cum_market'] = (1 + df['market_return']).cumprod() * self.initial_capital

        self.results[symbol] = df
        return df
