import pandas as pd

import sqlite3

from typing import List, Dict, Any

from src.core.interfaces import IUniverseFilter

from src.utils.indicators import TechnicalMath


class TechnicalFilterStrategy(IUniverseFilter):

    def __init__(self, db_path: str):
        self.db_path = db_path


    def fetch_data(self, universe: List[str]) -> pd.DataFrame:
        if not universe:
            return pd.DataFrame()

        placeholders = ','.join(['?'] * len(universe))

        query = f"""
        SELECT symbol, datetime, open, high, low, close, volume
        FROM market_data
        WHERE symbol IN ({placeholders})
        ORDER BY symbol, datetime ASC
        """

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=tuple(universe))
            df['datetime'] = pd.to_datetime(df['datetime'])
            return df


    def update_universe(self, candidates: List[str], data_context: Any = None) -> List[str]:
        print(f"--> [Tech Filter] Analizando {len(candidates)} candidatos...")


        df = self.fetch_data(candidates)
        if df.empty:
            print("WARNING: No market data found.")
            return []


        g = df.groupby('symbol')

        df['ema_50'] = g['close'].transform(lambda x: TechnicalMath.ema(x, 50))

        df['ema_200'] = g['close'].transform(lambda x: TechnicalMath.ema(x, 200))

        df['rsi'] = g['close'].transform(lambda x: TechnicalMath.rsi(x, 14))

        df['rvol'] = g['volume'].transform(lambda x: TechnicalMath.relative_volume(x, 20))


        df['trend_ok'] = (df['close'] > df['ema_200']) & (df['ema_50'] > df['ema_200'])


        df['score_rsi'] = df['rsi'] / 100.0

        df['tech_score'] = (
            (df['trend_ok'].astype(int) * 0.4) +
            (df['score_rsi'] * 0.3) +
            ((df['rvol'] > 1.2).astype(int) * 0.3)
        )


        latest = df.groupby('symbol').tail(1).copy()

        valid = latest[latest['trend_ok'] == True]

        top_n = 5
        finalists = valid.sort_values(by='tech_score', ascending=False).head(top_n)

        print("\n--- Top Candidatos Técnicos ---")
        print(finalists[['symbol', 'close', 'rsi', 'rvol', 'tech_score']].to_string(index=False))

        return finalists['symbol'].tolist()


    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        return 0.0


