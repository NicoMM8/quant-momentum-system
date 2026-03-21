import pandas as pd

import numpy as np

import sqlite3

from typing import List, Dict, Any, Optional

from src.core.interfaces import IUniverseFilter


class MacroScannerStrategy(IUniverseFilter):

    def __init__(self, db_path: str):
        self.db_path = db_path


    def load_data(self) -> pd.DataFrame:
        query = """
        SELECT f.symbol, f.pe_ratio, f.pb_ratio, f.roe, a.sector
        FROM fundamentals f
        LEFT JOIN assets a ON f.symbol = a.symbol
        WHERE f.date = (SELECT MAX(date) FROM fundamentals)
        """

        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn)


    def compute_factors(self, df: pd.DataFrame) -> pd.DataFrame:

        cols_to_numeric = ['pe_ratio', 'pb_ratio', 'roe']
        for col in cols_to_numeric:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=cols_to_numeric)

        if df.empty:
            return df


        def zscore(x):
            if x.std() == 0 or np.isnan(x.std()):
                return 0
            return (x - x.mean()) / x.std()


        df['sector'] = df['sector'].fillna('Unknown')


        df['z_pe'] = df.groupby('sector')['pe_ratio'].transform(zscore) * -1

        df['z_pb'] = df.groupby('sector')['pb_ratio'].transform(zscore) * -1

        df['z_roe'] = df.groupby('sector')['roe'].transform(zscore)


        df[['z_pe', 'z_pb', 'z_roe']] = df[['z_pe', 'z_pb', 'z_roe']].fillna(0)

        df['alpha_score'] = (0.4 * df['z_pe']) + (0.3 * df['z_pb']) + (0.3 * df['z_roe'])

        return df


    def update_universe(self, candidates: Optional[List[str]] = None, data_context: Any = None) -> List[str]:
        raw_data = self.load_data()

        if raw_data.empty:
            print("⚠️ WARNING: No hay datos en tabla 'fundamentals'.")
            return []

        scored_data = self.compute_factors(raw_data)

        if scored_data.empty:
            print("⚠️ WARNING: Datos insuficientes tras limpieza.")
            return []

        top_candidates = scored_data.sort_values(by='alpha_score', ascending=False)

        print("\n--- Ranking Fundamental (Capa 1) ---")
        print(top_candidates[['symbol', 'pe_ratio', 'roe', 'alpha_score']].head(5).to_string(index=False))

        return top_candidates['symbol'].tolist()


    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        return 0.0


