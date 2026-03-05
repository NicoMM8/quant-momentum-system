# =============================================================================
# BACKTEST.PY - MOTOR DE BACKTESTING VECTORIZADO
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo implementa un BACKTESTER, que es una herramienta para
# PROBAR ESTRATEGIAS DE TRADING en datos HISTÓRICOS.
#
# ¿QUÉ ES BACKTESTING?
# ─────────────────────
# Backtesting es simular cómo habría funcionado una estrategia en el pasado.
#
# Es como si un piloto de F1 probara su estrategia de carrera
# revisando grabaciones de carreras anteriores:
# "Si hubiera frenado aquí, ¿habría ganado tiempo?"
#
# En trading:
# "Si hubiera comprado aquí y vendido allá, ¿habría ganado dinero?"
#
# ¿POR QUÉ ES IMPORTANTE?
# ─────────────────────────
# • Probar ideas SIN arriesgar dinero real
# • Detectar fallos en la estrategia antes de invertir
# • Calcular métricas de rendimiento (retorno, drawdown, Sharpe)
# • Ganar confianza en tu sistema
#
# ⚠️ ADVERTENCIA: El backtesting tiene LIMITACIONES
# • El pasado NO garantiza el futuro
# • Puede haber "overfitting" (optimizar para el pasado)
# • No captura slippage, comisiones ni impacto de mercado
#
# ¿QUÉ ESTRATEGIA PRUEBA ESTE BACKTEST?
# ─────────────────────────────────────
# Este archivo implementa la estrategia de "GOLDEN CROSS":
#
# GOLDEN CROSS:
# Comprar cuando la Media Móvil Corta (50 días) cruza HACIA ARRIBA
# la Media Móvil Larga (200 días).
#
#              EMA 50 ─────────────────╮
#                                       ╲
#     Señal de COMPRA aquí ────────────► ╳ ←── Cruce
#                                       ╱
#              EMA 200 ────────────────╯
#
# Vender cuando EMA 50 cruza HACIA ABAJO EMA 200 ("Death Cross").
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

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
        # Usamos parámetros en la query para evitar problemas con caracteres especiales
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
        
        # Validación estricta de datos mínimos
        if df.empty or len(df) < long_window:
            # Retornamos None para indicar que no hubo suficientes datos
            return None

        # 1. Indicadores
        df['SMA_S'] = df['close'].rolling(window=short_window).mean()
        df['SMA_L'] = df['close'].rolling(window=long_window).mean()

        # 2. Señal: 1 (Comprado) cuando Corta > Larga
        df['signal'] = np.where(df['SMA_S'] > df['SMA_L'], 1.0, 0.0)
        
        # 3. Detectar Cruces (Trades)
        df['trade'] = df['signal'].diff()

        # 4. Calcular Retornos
        # CORRECCIÓN WARNING: Usamos fill_method=None
        df['market_return'] = df['close'].pct_change(fill_method=None)
        
        # Shift para evitar mirar el futuro
        df['strategy_return'] = df['signal'].shift(1) * df['market_return']
        
        # Rellenar NaNs iniciales con 0 para que el cálculo acumulado no falle
        df['strategy_return'] = df['strategy_return'].fillna(0)
        df['market_return'] = df['market_return'].fillna(0)

        df['cum_strategy'] = (1 + df['strategy_return']).cumprod() * self.initial_capital
        df['cum_market'] = (1 + df['market_return']).cumprod() * self.initial_capital
        
        self.results[symbol] = df
        return df
    # ... (resto de métodos print_trade_log y plot_equity_curve iguales) ...