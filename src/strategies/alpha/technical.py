# =============================================================================
# TECHNICAL.PY - CAPA 2: FILTRO TÉCNICO
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este es el SEGUNDO FILTRO del embudo de trading (Capa 2).
# Recibe los candidatos de Capa 1 (fundamentalmente buenos) y los filtra
# según criterios TÉCNICOS para asegurar que tienen buen TIMING.
#
# ¿POR QUÉ NECESITAMOS ANÁLISIS TÉCNICO?
# ──────────────────────────────────────
# Una empresa puede ser excelente fundamentalmente, pero si:
# • Está en tendencia bajista → perderás dinero esperando la reversión
# • No tiene volumen → no podrás salir cuando quieras
# • Está sobrecomprada → es tarde para entrar
#
# "Un buen negocio comprado en mal momento sigue siendo una mala inversión"
#
# CRITERIOS QUE ANALIZA:
# ─────────────────────────
#
# 1. TENDENCIA (40% del peso)
#    ─────────────────────────
#    ¿El precio está subiendo?
#    Usamos EMAs (Exponential Moving Averages):
#    • EMA 50 > EMA 200 = "Golden Cross" (tendencia alcista)
#    • Precio > EMA 200 = confirmación de tendencia
#
# 2. MOMENTUM (30% del peso)
#    ─────────────────────────
#    ¿La fuerza de compra es buena?
#    Usamos RSI (Relative Strength Index):
#    • RSI > 50 = más fuerza compradora que vendedora
#    • RSI < 30 = sobreventa (posible rebote)
#    • RSI > 70 = sobrecompra (cuidado)
#
# 3. VOLUMEN INSTITUCIONAL (30% del peso)
#    ──────────────────────────────────────
#    ¿Hay "dinero inteligente" participando?
#    Usamos RVOL (Relative Volume):
#    • RVOL > 1.2 = volumen 20% mayor al promedio
#    • Esto indica interés institucional
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

import pandas as pd
# Pandas para manipulación de DataFrames

import sqlite3
# SQLite para conexión a base de datos

from typing import List, Dict, Any
# Type hints

from src.core.interfaces import IUniverseFilter
# Interfaz para estrategias que filtran el universo

from src.utils.indicators import TechnicalMath
# Nuestra librería de indicadores técnicos


# =============================================================================
# CLASE: TechnicalFilterStrategy (Filtro Técnico)
# =============================================================================

class TechnicalFilterStrategy(IUniverseFilter):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    CAPA 2: FILTRO TÉCNICO                                 ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Filtra candidatos de Capa 1 usando análisis técnico.                     ║
    ║  Busca: Tendencia alcista + Buen momentum + Volumen institucional         ║
    ║                                                                           ║
    ║  CONCEPTOS CLAVE:                                                         ║
    ║  ─────────────────                                                        ║
    ║                                                                           ║
    ║  EMA (Exponential Moving Average)                                         ║
    ║  ──────────────────────────────────                                       ║
    ║  Promedio que da más peso a los datos recientes.                          ║
    ║  • EMA 50: Media de últimas ~50 velas (tendencia corta)                   ║
    ║  • EMA 200: Media de últimas ~200 velas (tendencia larga)                 ║
    ║                                                                           ║
    ║  GOLDEN CROSS:                                                            ║
    ║  ───────────────                                                          ║
    ║  Cuando EMA corta cruza HACIA ARRIBA la EMA larga.                        ║
    ║  Señal alcista clásica usada por instituciones.                           ║
    ║                                                                           ║
    ║     EMA 50 ─────────────╮                                                 ║
    ║                          ╲                                                ║
    ║     EMA 200 ─────────────╳───────── ← Cruce = Golden Cross                ║
    ║                          ╱                                                ║
    ║     EMA 50 ─────────────╯                                                 ║
    ║     (después del cruce, EMA 50 está ARRIBA de EMA 200)                    ║
    ║                                                                           ║
    ║  RSI (Relative Strength Index)                                            ║
    ║  ──────────────────────────────                                           ║
    ║  Mide la velocidad de los movimientos de precio.                          ║
    ║  Rango: 0-100                                                             ║
    ║  • < 30: Sobreventa (posible rebote)                                      ║
    ║  • 30-70: Zona neutral                                                    ║
    ║  • > 70: Sobrecompra (posible caída)                                      ║
    ║                                                                           ║
    ║  RVOL (Relative Volume)                                                   ║
    ║  ──────────────────────────                                               ║
    ║  Compara volumen actual vs. promedio histórico.                           ║
    ║  • RVOL = 1.5 significa 50% más volumen de lo normal                      ║
    ║  • RVOL alto = institucionales probablemente activos                      ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, db_path: str):
        """
        Inicializa el filtro técnico con la ruta a la base de datos.
        """
        self.db_path = db_path

    # =========================================================================
    # MÉTODO: fetch_data (Obtener Datos de Mercado)
    # =========================================================================
    
    def fetch_data(self, universe: List[str]) -> pd.DataFrame:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    OBTENER DATOS DE MERCADO                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Consulta datos OHLCV para los símbolos del universo.                 ║
        ║                                                                       ║
        ║  OPTIMIZACIÓN:                                                        ║
        ║  ───────────────                                                      ║
        ║  • Solo consulta los símbolos necesarios (no toda la tabla)           ║
        ║  • Usa parámetros para prevenir SQL Injection                         ║
        ║  • Ordena por símbolo y fecha para cálculos consistentes              ║
        ║                                                                       ║
        ║  ¿QUÉ ES SQL INJECTION?                                               ║
        ║  ─────────────────────────                                            ║
        ║  Un ataque donde el usuario malicioso introduce código SQL            ║
        ║  en una consulta. Ejemplo del problema:                               ║
        ║                                                                       ║
        ║  # MAL (vulnerable):                                                  ║
        ║  query = f"SELECT * WHERE symbol = '{user_input}'"                    ║
        ║  # Si user_input = "'; DROP TABLE market_data; --"                    ║
        ║  # → ¡Borra la tabla!                                                 ║
        ║                                                                       ║
        ║  # BIEN (seguro):                                                     ║
        ║  query = "SELECT * WHERE symbol = ?"                                  ║
        ║  cursor.execute(query, (user_input,))                                 ║
        ║  # El ? se reemplaza de forma segura                                  ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Si no hay universo, retornar vacío
        if not universe:
            return pd.DataFrame()
        
        # Crear placeholders para la consulta segura
        # Si universe = ['AAPL', 'MSFT', 'GOOGL']
        # placeholders = '?,?,?'
        placeholders = ','.join(['?'] * len(universe))
        
        query = f"""
        SELECT symbol, datetime, open, high, low, close, volume
        FROM market_data
        WHERE symbol IN ({placeholders})
        ORDER BY symbol, datetime ASC
        """
        # ORDER BY importante: los indicadores necesitan datos ordenados
        
        with sqlite3.connect(self.db_path) as conn:
            # params=tuple(universe) → seguro contra SQL Injection
            df = pd.read_sql_query(query, conn, params=tuple(universe))
            df['datetime'] = pd.to_datetime(df['datetime'])
            return df

    # =========================================================================
    # MÉTODO: update_universe (Filtrar Universo - Interfaz IStrategy)
    # =========================================================================
    
    def update_universe(self, candidates: List[str], data_context: Any = None) -> List[str]:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      FILTRAR UNIVERSO (CAPA 2)                        ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Recibe candidatos de Capa 1 y los filtra técnicamente.               ║
        ║                                                                       ║
        ║  PROCESO:                                                             ║
        ║  ─────────                                                            ║
        ║  1. Obtener datos OHLCV de los candidatos                             ║
        ║  2. Calcular indicadores (EMA 50, EMA 200, RSI, RVOL)                 ║
        ║  3. Filtrar por tendencia alcista (EMA 50 > EMA 200)                  ║
        ║  4. Calcular score técnico ponderado                                  ║
        ║  5. Retornar Top N ordenado por score                                 ║
        ║                                                                       ║
        ║  LÓGICA DE FILTRADO:                                                  ║
        ║  ─────────────────────                                                ║
        ║                                                                       ║
        ║  REQUISITO OBLIGATORIO (HARD FILTER):                                 ║
        ║  • Precio > EMA 200 (sobre tendencia a largo plazo)                   ║
        ║  • EMA 50 > EMA 200 (Golden Cross confirmado)                         ║
        ║                                                                       ║
        ║  SCORING (SOFT FILTER):                                               ║
        ║  • 40% Tendencia: ¿cumple requisito obligatorio?                      ║
        ║  • 30% Momentum: RSI normalizado (0-1)                                ║
        ║  • 30% Volumen: ¿RVOL > 1.2? (interés institucional)                  ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        print(f"--> [Tech Filter] Analizando {len(candidates)} candidatos...")
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 1: OBTENER DATOS
        # ─────────────────────────────────────────────────────────────────────
        
        df = self.fetch_data(candidates)
        if df.empty:
            print("WARNING: No market data found.")
            return []

        # ─────────────────────────────────────────────────────────────────────
        # PASO 2: CALCULAR INDICADORES (Vectorizado por Grupo)
        # ─────────────────────────────────────────────────────────────────────
        
        # groupby().transform() aplica la función a cada grupo
        # y retorna resultado del mismo tamaño que el DataFrame original
        g = df.groupby('symbol')

        # EMA 50: Media exponencial de 50 períodos
        df['ema_50'] = g['close'].transform(lambda x: TechnicalMath.ema(x, 50))
        
        # EMA 200: Media exponencial de 200 períodos
        df['ema_200'] = g['close'].transform(lambda x: TechnicalMath.ema(x, 200))
        
        # RSI: Índice de Fuerza Relativa de 14 períodos
        df['rsi'] = g['close'].transform(lambda x: TechnicalMath.rsi(x, 14))
        
        # RVOL: Volumen relativo de 20 períodos
        df['rvol'] = g['volume'].transform(lambda x: TechnicalMath.relative_volume(x, 20))
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 3: FILTRO DE TENDENCIA (HARD FILTER)
        # ─────────────────────────────────────────────────────────────────────
        
        # Tendencia alcista = Precio > EMA 200 AND EMA 50 > EMA 200
        df['trend_ok'] = (df['close'] > df['ema_200']) & (df['ema_50'] > df['ema_200'])
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 4: CALCULAR SCORE TÉCNICO
        # ─────────────────────────────────────────────────────────────────────
        
        # Normalizar RSI a rango 0-1
        df['score_rsi'] = df['rsi'] / 100.0
        
        # Score técnico ponderado
        df['tech_score'] = (
            (df['trend_ok'].astype(int) * 0.4) +   # 40% Tendencia
            (df['score_rsi'] * 0.3) +               # 30% Momentum
            ((df['rvol'] > 1.2).astype(int) * 0.3)  # 30% Volumen Institucional
        )
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 5: TOMAR ÚLTIMO SNAPSHOT Y FILTRAR
        # ─────────────────────────────────────────────────────────────────────
        
        # Solo última fila de cada símbolo (simulación de tiempo real)
        latest = df.groupby('symbol').tail(1).copy()
        
        # HARD FILTER: Solo activos en tendencia alcista confirmada
        valid = latest[latest['trend_ok'] == True]
        
        # Ordenar por score técnico
        top_n = 5
        finalists = valid.sort_values(by='tech_score', ascending=False).head(top_n)
        
        # Mostrar resultados
        print("\n--- Top Candidatos Técnicos ---")
        print(finalists[['symbol', 'close', 'rsi', 'rvol', 'tech_score']].to_string(index=False))
        
        return finalists['symbol'].tolist()

    # =========================================================================
    # MÉTODO: generate_signal (Generar Señal - Interfaz IStrategy)
    # =========================================================================
    
    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        """
        Esta capa no genera señales de trading directas.
        Solo filtra el universo para Capa 3 (Microestructura).
        
        Retorna 0.0 (neutral).
        """
        return 0.0


# =============================================================================
# EJEMPLO DE USO
# =============================================================================
#
# from src.strategies.alpha.technical import TechnicalFilterStrategy
#
# # Recibir candidatos de Capa 1
# candidates_from_layer1 = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
#
# # Crear filtro técnico
# tech_filter = TechnicalFilterStrategy("data/trading.db")
#
# # Filtrar por criterios técnicos
# finalists = tech_filter.update_universe(candidates_from_layer1)
# print(f"Finalistas para Capa 3: {finalists}")
#
# # Ejemplo de output:
# # --> [Tech Filter] Analizando 5 candidatos...
# # 
# # --- Top Candidatos Técnicos ---
# # symbol   close    rsi   rvol  tech_score
# #   NVDA  890.25  65.30   1.85        0.90
# #   AAPL  185.50  58.20   1.35        0.85
# #   MSFT  420.10  52.40   1.50        0.80
#
# =============================================================================