import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

class MockDataGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.sectors = ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']

    def init_db(self):
        """Inicializa las tablas usando el schema.sql"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        schema_path = os.path.join(base_dir, 'data', 'schema.sql')
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
        print("--> Schema SQL aplicado correctamente.")

    def generate_assets(self, n_assets=500):
        symbols = [f"TICKER_{i:03d}" for i in range(n_assets)]
        df = pd.DataFrame({
            'symbol': symbols,
            'sector': np.random.choice(self.sectors, n_assets),
            'industry': 'General',
            'is_active': 1
        })
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql('assets', conn, if_exists='replace', index=False)
        return symbols

    def generate_fundamentals(self, symbols, days_back=0):
        n = len(symbols)
        base_date = datetime.now() - timedelta(days=days_back)
        pe_base = np.random.normal(20, 5, n) 
        pb_base = np.random.normal(3, 1, n)
        
        df = pd.DataFrame({
            'symbol': symbols,
            'date': base_date.strftime('%Y-%m-%d'),
            'market_cap': np.random.lognormal(20, 2, n), 
            'pe_ratio': np.abs(pe_base + np.random.normal(0, 2, n)), 
            'pb_ratio': np.abs(pb_base + np.random.normal(0, 0.5, n)),  # Agregado
            'roe': np.random.normal(0.15, 0.05, n),                     # Agregado
            'debt_to_equity': np.random.uniform(0, 2, n)
        })
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql('fundamentals', conn, if_exists='append', index=False)



    def generate_micro_data(self, symbols: list, date_str: str) -> pd.DataFrame:
        """
        Genera datos M1 (1 minuto) para una fecha específica.
        CORREGIDO: Ahora incluye 'open' para que el gráfico de velas funcione.
        """
        print(f"--> Generando Micro-Data (M1 + Order Flow) para {len(symbols)} activos...")
        
        minutes = 390
        start_time = pd.to_datetime(f"{date_str} 09:30:00")
        time_index = [start_time + timedelta(minutes=i) for i in range(minutes)]
        
        all_micro = []

        for sym in symbols:
            price = 100.0
            price_path = []
            obi_path = [] 
            
            for _ in range(minutes):
                obi = np.random.normal(0, 0.4) 
                obi = max(min(obi, 1), -1)
                
                micro_drift = obi * 0.05 
                change = np.random.normal(0, 0.1) + micro_drift
                
                price += change
                price_path.append(price)
                obi_path.append(obi)

            df = pd.DataFrame({
                'symbol': sym,
                'datetime': time_index,
                'close': price_path,
                'obi': obi_path
            })
            
            # --- CORRECCIÓN AQUÍ ---
            # 1. Generamos un 'open' sintético cercano al close
            df['open'] = df['close'] + np.random.uniform(-0.05, 0.05, minutes)
            
            # 2. Aseguramos que High sea el mayor y Low el menor
            # High es el maximo entre Open y Close + un poco de mecha
            df['high'] = df[['open', 'close']].max(axis=1) + np.random.uniform(0, 0.05, minutes)
            # Low es el minimo entre Open y Close - un poco de mecha
            df['low'] = df[['open', 'close']].min(axis=1) - np.random.uniform(0, 0.05, minutes)
            
            all_micro.append(df)

        return pd.concat(all_micro)
    
    # --- NUEVO MÉTODO SPRINT 3 ---
    def generate_ohlcv(self, symbols: list, timeframe='1H', days=60):
        """
        Genera OHLCV usando Geometric Brownian Motion.
        """
        print(f"--> Generando Market Data ({timeframe}) para {len(symbols)} activos...")
        
        all_data = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq=timeframe)
        n_periods = len(dates)

        for sym in symbols:
            # Drift (Tendencia) y Volatilidad aleatoria por activo
            drift = np.random.normal(0.0001, 0.0005) 
            volatility = np.random.normal(0.01, 0.002)
            
            # Precio inicial
            price = np.random.uniform(50, 150)
            
            # Caminata Aleatoria
            returns = np.random.normal(drift, volatility, n_periods)
            price_path = price * np.exp(np.cumsum(returns))
            
            # Velas OHLC
            noise_h = np.abs(np.random.normal(0, 0.005, n_periods))
            noise_l = np.abs(np.random.normal(0, 0.005, n_periods))
            
            open_p = price_path * (1 + np.random.normal(0, 0.002, n_periods))
            high = price_path * (1 + noise_h)
            low = price_path * (1 - noise_l)
            # Volume bursts
            vol_base = np.random.lognormal(10, 1, n_periods)
            
            df = pd.DataFrame({
                'symbol': sym,
                'datetime': dates,
                'open': open_p,
                'high': np.maximum(high, open_p),
                'low': np.minimum(low, open_p),
                'close': price_path,
                'volume': vol_base
            })
            all_data.append(df)

        big_df = pd.concat(all_data)
        
        with sqlite3.connect(self.db_path) as conn:
            # Crear tabla si no existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT, datetime TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_md_sym_date ON market_data(symbol, datetime)")
            
            # Guardamos todo
            big_df.to_sql('market_data', conn, if_exists='replace', index=False)
            
        print(f"--> {len(big_df)} velas generadas en SQLite.")