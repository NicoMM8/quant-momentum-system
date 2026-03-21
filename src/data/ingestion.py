import yfinance as yf

import pandas as pd

import sqlite3

import os

import time

import yaml

import logging

from tqdm import tqdm

from typing import Optional, List

from src.utils.static_universe import MY_HUGE_UNIVERSE


logger = logging.getLogger(__name__)


class DataIngestor:


    def __init__(self, db_path: str, config_path: str = "config/settings.yaml"):
        self.db_path = db_path

        self.config = self._load_config(config_path)


        universe_config = self.config.get('universe', {})

        self.tickers = universe_config.get('default_tickers', MY_HUGE_UNIVERSE)


        ingestion_config = self.config.get('ingestion', {})

        self.delay_ms = ingestion_config.get('yahoo_delay_ms', 500)

        self.max_retries = ingestion_config.get('max_retries', 3)


    def _load_config(self, config_path: str) -> dict:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)

            except Exception as e:
                logger.warning(f"No se pudo cargar config: {e}. Usando defaults.")

        return {}


    def _validate_ohlcv(self, df: pd.DataFrame, symbol: str) -> bool:
        if df.empty:
            return False

        issues = []

        invalid_hl = (df['high'] < df['low']).sum()

        if invalid_hl > 0:
            issues.append(f"High < Low en {invalid_hl} filas")

        invalid_high = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()

        if invalid_high > 0:
            issues.append(f"High inválido en {invalid_high} filas")

        invalid_low = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()

        if invalid_low > 0:
            issues.append(f"Low inválido en {invalid_low} filas")

        negative_vol = (df['volume'] < 0).sum()

        if negative_vol > 0:
            issues.append(f"Volumen negativo en {negative_vol} filas")

        negative_prices = (
            (df['open'] < 0) |
            (df['high'] < 0) |
            (df['low'] < 0) |
            (df['close'] < 0)
        ).sum()

        if negative_prices > 0:
            issues.append(f"Precios negativos en {negative_prices} filas")

        if issues:
            logger.warning(f"⚠️ Validación OHLCV para {symbol}: {', '.join(issues)}")
            return False

        return True


    def _rate_limit(self):
        time.sleep(self.delay_ms / 1000.0)


    def sync_assets_table(self):
        print(f"--- 1. Sincronizando Maestro de Activos ({len(self.tickers)}) ---")

        asset_data = []

        for ticker in tqdm(self.tickers, desc="Descargando Info"):

            try:

                t = yf.Ticker(ticker)

                info = t.info


                asset_data.append({
                    'symbol': ticker,

                    'sector': info.get('sector', 'ETF'),

                    'industry': info.get('industry', 'Unknown'),

                    'is_active': 1
                })

            except Exception as e:
                print(f"⚠️ Error con {ticker}: {e}")


        df = pd.DataFrame(asset_data)

        with sqlite3.connect(self.db_path) as conn:

            df.to_sql('assets', conn, if_exists='replace', index=False)

        print("✅ Tabla 'assets' actualizada.")


    def sync_market_data(self, period="2y"):
        print(f"--- 2. Descargando Market Data (Periodo: {period}) ---")


        data = yf.download(
            self.tickers,
            period=period,
            group_by='ticker',
            auto_adjust=True,
            progress=True,
            threads=True
        )


        if data is None or data.empty:
            print("❌ Error crítico: yfinance no devolvió datos. Revisa tu conexión.")
            return


        clean_data = []

        for ticker in self.tickers:
            try:

                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.levels[0]:
                        print(f"⚠️ {ticker} no se encontró en la descarga (MultiIndex).")
                        continue

                    ticker_data = data[ticker].copy()

                elif len(self.tickers) == 1 and ticker == self.tickers[0]:
                    ticker_data = data.copy()

                else:
                    print(f"⚠️ Estructura de datos no coincide para {ticker}")
                    continue

                if ticker_data.empty:
                    print(f"⚠️ Datos vacíos para {ticker}")
                    continue


                df = ticker_data.reset_index()

                df.columns = [c.lower() for c in df.columns]

                df['symbol'] = ticker

                df = df.rename(columns={'date': 'datetime'})

                required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']

                if not all(col in df.columns for col in required_cols):
                    print(f"⚠️ {ticker} le faltan columnas críticas.")
                    continue

                df = df[['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']]

                if self._validate_ohlcv(df, ticker):
                    clean_data.append(df)
                else:
                    logger.warning(f"⚠️ {ticker}: datos con problemas de validación, se agregan con advertencia.")
                    clean_data.append(df)

            except Exception as e:
                print(f"⚠️ Error procesando {ticker}: {e}")
                continue


        if not clean_data:
            print("❌ No se pudo procesar ningún activo.")
            return

        final_df = pd.concat(clean_data)


        with sqlite3.connect(self.db_path) as conn:
            try:
                existing = pd.read_sql("SELECT * FROM market_data", conn)
                combined = pd.concat([existing, final_df])
                combined = combined.drop_duplicates(
                    subset=['symbol', 'datetime'], keep='last'
                )
                combined.to_sql('market_data', conn, if_exists='replace', index=False)
            except Exception:
                final_df.to_sql('market_data', conn, if_exists='replace', index=False)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_md_sym_date ON market_data(symbol, datetime)")

        print(f"✅ Market Data inyectada: {len(final_df)} filas.")


    def sync_fundamentals(self):
        print("--- 3. Descargando Fundamentales ---")

        fund_data = []

        for ticker in tqdm(self.tickers, desc="Fundamentales"):
            try:
                t = yf.Ticker(ticker)
                info = t.info

                fund_data.append({
                    'symbol': ticker,

                    'date': pd.Timestamp.now().strftime('%Y-%m-%d'),

                    'market_cap': info.get('marketCap', 0),

                    'pe_ratio': info.get('trailingPE', 0),

                    'pb_ratio': info.get('priceToBook', 0),

                    'roe': info.get('returnOnEquity', 0),

                    'debt_to_equity': info.get('debtToEquity', 0)
                })

            except:
                pass

        df = pd.DataFrame(fund_data)

        with sqlite3.connect(self.db_path) as conn:
            try:
                existing = pd.read_sql("SELECT * FROM fundamentals", conn)
                combined = pd.concat([existing, df])
                combined = combined.drop_duplicates(
                    subset=['symbol', 'date'], keep='last'
                )
                combined.to_sql('fundamentals', conn, if_exists='replace', index=False)
            except Exception:
                df.to_sql('fundamentals', conn, if_exists='replace', index=False)

        print("✅ Fundamentales actualizados.")


