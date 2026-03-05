# =============================================================================
# MACRO.PY - CAPA 1: SCANNER FUNDAMENTAL (VALUE + QUALITY)
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este es el PRIMER FILTRO del embudo de trading (Capa 1).
# Analiza los FUNDAMENTALES de las empresas para encontrar:
# 
# 1. EMPRESAS INFRAVALORADAS (Value Investing)
#    → PE Ratio bajo: estás pagando poco por cada dólar de ganancia
#    → PB Ratio bajo: estás pagando poco por cada dólar de activos
#
# 2. EMPRESAS DE CALIDAD (Quality Investing)
#    → ROE alto: la empresa genera mucho retorno sobre su capital
#
# ARQUITECTURA DEL EMBUDO:
# ─────────────────────────
#
#    ┌─────────────────────────────────────────────────────────────────┐
#    │                    UNIVERSO INICIAL                            │
#    │               (8+ activos: AAPL, MSFT, GOOGL, etc.)            │
#    └─────────────────────────────────────────────────────────────────┘
#                                  │
#                                  ▼
#    ┌─────────────────────────────────────────────────────────────────┐
#    │              🔍 CAPA 1: MACRO SCANNER (este archivo)           │
#    │           Filtro Fundamental: Value + Quality                  │
#    │                                                                 │
#    │  Métricas analizadas:                                           │
#    │  • PE Ratio (Price/Earnings) - Queremos BAJO                    │
#    │  • PB Ratio (Price/Book) - Queremos BAJO                        │
#    │  • ROE (Return on Equity) - Queremos ALTO                       │
#    └─────────────────────────────────────────────────────────────────┘
#                                  │
#                                  ▼
#                       [ Top N candidatos ]
#                                  │
#                                  ▼
#    ┌─────────────────────────────────────────────────────────────────┐
#    │              📊 CAPA 2: FILTRO TÉCNICO                         │
#    └─────────────────────────────────────────────────────────────────┘
#                                  │
#                                  ▼
#    ┌─────────────────────────────────────────────────────────────────┐
#    │              🔬 CAPA 3: MICROESTRUCTURA                        │
#    └─────────────────────────────────────────────────────────────────┘
#
# ¿QUÉ ES VALUE INVESTING?
# ─────────────────────────
# Estrategia popularizada por Warren Buffett y Benjamin Graham.
# La idea: comprar empresas que valen MÁS de lo que cuesta su acción.
#
# Analogía del supermercado:
# Si un kilo de manzanas normalmente cuesta $5, y encuentras
# manzanas de la misma calidad a $3, es una GANGA.
# Value investing busca estas "gangas" en el mercado de valores.
#
# ¿QUÉ ES UN Z-SCORE?
# ─────────────────────
# El Z-Score normaliza los valores para compararlos entre sí.
#
# Fórmula: Z = (Valor - Media) / Desviación Estándar
#
# Un Z-Score de +2 significa que el valor está 2 desviaciones
# estándar por encima del promedio (muy alto).
# Un Z-Score de -2 significa 2 desviaciones por debajo (muy bajo).
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

import pandas as pd
# Pandas para manipulación de datos en DataFrames

import numpy as np
# NumPy para cálculos matemáticos (std, mean)

import sqlite3
# SQLite para conexión a base de datos

from typing import List, Dict, Any, Optional
# Type hints para mejor legibilidad

from src.core.interfaces import IUniverseFilter
# Interfaz para estrategias que filtran el universo de candidatos


# =============================================================================
# CLASE: MacroScannerStrategy (Filtro Fundamental)
# =============================================================================

class MacroScannerStrategy(IUniverseFilter):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                   CAPA 1: SCANNER FUNDAMENTAL                             ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Primera etapa del embudo de trading.                                     ║
    ║  Filtra empresas usando métricas fundamentales (Value + Quality).         ║
    ║                                                                           ║
    ║  MÉTRICAS UTILIZADAS:                                                     ║
    ║  ─────────────────────                                                    ║
    ║                                                                           ║
    ║  PE RATIO (Price to Earnings)                                             ║
    ║  ───────────────────────────────                                          ║
    ║  Fórmula: Precio de la acción / Ganancias por acción                      ║
    ║                                                                           ║
    ║  Ejemplo: Acción a $100, EPS = $5                                         ║
    ║  PE = $100 / $5 = 20x                                                     ║
    ║  Significa: pagas $20 por cada $1 de ganancia anual                       ║
    ║                                                                           ║
    ║  Interpretación:                                                          ║
    ║  • PE < 15: Potencialmente infravalorada (bueno para Value)               ║
    ║  • PE 15-25: Valoración justa                                             ║
    ║  • PE > 25: Potencialmente sobrevalorada                                  ║
    ║                                                                           ║
    ║  PB RATIO (Price to Book)                                                 ║
    ║  ─────────────────────────────                                            ║
    ║  Fórmula: Precio de la acción / Valor en libros por acción                ║
    ║                                                                           ║
    ║  Ejemplo: Acción a $100, Book Value = $50                                 ║
    ║  PB = $100 / $50 = 2x                                                     ║
    ║  Significa: pagas $2 por cada $1 de activos netos                         ║
    ║                                                                           ║
    ║  Interpretación:                                                          ║
    ║  • PB < 1: La empresa vale menos que sus activos (¿oportunidad?)          ║
    ║  • PB 1-3: Normal para empresas rentables                                 ║
    ║  • PB > 3: Mercado espera alto crecimiento futuro                         ║
    ║                                                                           ║
    ║  ROE (Return on Equity)                                                   ║
    ║  ─────────────────────────                                                ║
    ║  Fórmula: Ganancias netas / Capital de los accionistas                    ║
    ║                                                                           ║
    ║  Ejemplo: Ganancias = $10M, Capital = $50M                                ║
    ║  ROE = $10M / $50M = 20%                                                  ║
    ║  Significa: por cada $1 de capital, genera $0.20 de ganancia              ║
    ║                                                                           ║
    ║  Interpretación:                                                          ║
    ║  • ROE < 10%: Bajo retorno, no muy eficiente                              ║
    ║  • ROE 10-20%: Buen retorno                                               ║
    ║  • ROE > 20%: Excelente (empresas como Apple, Google)                     ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, db_path: str):
        """
        Inicializa el scanner con la ruta a la base de datos.
        
        PARÁMETROS:
        • db_path: Ruta a la base de datos SQLite (ej: "data/trading.db")
        """
        self.db_path = db_path

    # =========================================================================
    # MÉTODO: load_data (Cargar Datos Fundamentales)
    # =========================================================================
    
    def load_data(self) -> pd.DataFrame:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                       CARGAR DATOS FUNDAMENTALES                      ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Carga el snapshot más reciente de la tabla 'fundamentals'.           ║
        ║                                                                       ║
        ║  QUERY SQL:                                                           ║
        ║  ────────────                                                         ║
        ║  1. Selecciona PE, PB, ROE de tabla 'fundamentals'                    ║
        ║  2. Hace JOIN con 'assets' para obtener el sector                     ║
        ║  3. Filtra solo el snapshot más reciente                              ║
        ║                                                                       ║
        ║  ¿POR QUÉ NECESITAMOS EL SECTOR?                                      ║
        ║  ─────────────────────────────────                                    ║
        ║  Para NEUTRALIZACIÓN: Comparamos cada empresa con las de SU sector.   ║
        ║                                                                       ║
        ║  Un PE de 25 es BAJO para tecnología, pero ALTO para bancos.          ║
        ║  Por eso normalizamos dentro de cada sector (manzanas con manzanas).  ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Query con JOIN para obtener sector desde tabla 'assets'
        query = """
        SELECT f.symbol, f.pe_ratio, f.pb_ratio, f.roe, a.sector 
        FROM fundamentals f
        LEFT JOIN assets a ON f.symbol = a.symbol
        WHERE f.date = (SELECT MAX(date) FROM fundamentals)
        """
        # LEFT JOIN: incluye empresas aunque no tengan sector definido
        # MAX(date): solo el snapshot más reciente
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn)

    # =========================================================================
    # MÉTODO: compute_factors (Calcular Z-Scores)
    # =========================================================================
    
    def compute_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    CÁLCULO VECTORIZADO DE Z-SCORES                    ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Normaliza las métricas fundamentales para hacerlas comparables.      ║
        ║                                                                       ║
        ║  PROCESO:                                                             ║
        ║  ─────────                                                            ║
        ║  1. Limpiar datos (convertir a numérico, eliminar NaN)                ║
        ║  2. Calcular Z-Score de cada métrica DENTRO de cada sector            ║
        ║  3. Invertir PE y PB (queremos valores BAJOS)                         ║
        ║  4. Combinar en un score final ponderado                              ║
        ║                                                                       ║
        ║  ¿QUÉ ES UN Z-SCORE?                                                  ║
        ║  ─────────────────────                                                ║
        ║                                                                       ║
        ║  Z = (X - μ) / σ                                                      ║
        ║                                                                       ║
        ║  Donde:                                                               ║
        ║  • X = valor de la métrica                                            ║
        ║  • μ = media del sector                                               ║
        ║  • σ = desviación estándar del sector                                 ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Sector Tecnología:                                                   ║
        ║  PE de AAPL = 25, Media sector = 30, Std = 5                          ║
        ║  Z = (25 - 30) / 5 = -1.0                                             ║
        ║  → AAPL está 1 desviación BAJO el promedio (¡barato para el sector!)  ║
        ║                                                                       ║
        ║  INVERSIÓN DE PE Y PB:                                                ║
        ║  ───────────────────────                                              ║
        ║  Multiplicamos por -1 porque:                                         ║
        ║  • Queremos PE BAJO (más barato)                                      ║
        ║  • Queremos PB BAJO (más barato)                                      ║
        ║  • Queremos ROE ALTO (más rentable)                                   ║
        ║                                                                       ║
        ║  PONDERACIÓN FINAL:                                                   ║
        ║  ────────────────────                                                 ║
        ║  alpha_score = 0.4×z_pe + 0.3×z_pb + 0.3×z_roe                        ║
        ║                                                                       ║
        ║  PE tiene más peso (40%) porque es la métrica más importante          ║
        ║  para Value Investing según la evidencia empírica.                    ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # ─────────────────────────────────────────────────────────────────────
        # PASO 1: LIMPIEZA DE DATOS
        # ─────────────────────────────────────────────────────────────────────
        
        # Convertir a numérico (SQLite puede devolver texto)
        cols_to_numeric = ['pe_ratio', 'pb_ratio', 'roe']
        for col in cols_to_numeric:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # errors='coerce': convierte valores inválidos a NaN
        
        # Eliminar filas con valores faltantes
        df = df.dropna(subset=cols_to_numeric)

        if df.empty:
            return df

        # ─────────────────────────────────────────────────────────────────────
        # PASO 2: FUNCIÓN AUXILIAR PARA Z-SCORE
        # ─────────────────────────────────────────────────────────────────────
        
        def zscore(x):
            """
            Calcula el Z-Score de una serie.
            Retorna 0 si la desviación estándar es 0 (todos los valores iguales).
            """
            if x.std() == 0 or np.isnan(x.std()): 
                return 0
            return (x - x.mean()) / x.std()

        # ─────────────────────────────────────────────────────────────────────
        # PASO 3: NEUTRALIZACIÓN POR SECTOR
        # ─────────────────────────────────────────────────────────────────────
        
        # Llenar sectores vacíos con 'Unknown' para que groupby no falle
        df['sector'] = df['sector'].fillna('Unknown')

        # Calcular Z-Scores por sector
        # transform() aplica la función a cada grupo y devuelve resultado alineado
        
        # PE: Invertido (* -1) porque queremos valores BAJOS
        df['z_pe'] = df.groupby('sector')['pe_ratio'].transform(zscore) * -1 
        
        # PB: Invertido (* -1) porque queremos valores BAJOS
        df['z_pb'] = df.groupby('sector')['pb_ratio'].transform(zscore) * -1
        
        # ROE: NO invertido porque queremos valores ALTOS
        df['z_roe'] = df.groupby('sector')['roe'].transform(zscore) 

        # ─────────────────────────────────────────────────────────────────────
        # PASO 4: SCORE COMPUESTO
        # ─────────────────────────────────────────────────────────────────────
        
        # Rellenar NaN en Z-Scores (ej: sector con solo 1 empresa)
        df[['z_pe', 'z_pb', 'z_roe']] = df[['z_pe', 'z_pb', 'z_roe']].fillna(0)
        
        # Calcular score final ponderado
        # 40% PE + 30% PB + 30% ROE
        df['alpha_score'] = (0.4 * df['z_pe']) + (0.3 * df['z_pb']) + (0.3 * df['z_roe'])
        
        return df

    # =========================================================================
    # MÉTODO: update_universe (Filtrar Universo - Interfaz IStrategy)
    # =========================================================================
    
    def update_universe(self, candidates: Optional[List[str]] = None, data_context: Any = None) -> List[str]:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      FILTRAR UNIVERSO                                 ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Implementación de la interfaz IStrategy.                             ║
        ║  Retorna el Top N activos ordenados por score fundamental.            ║
        ║                                                                       ║
        ║  PROCESO:                                                             ║
        ║  ─────────                                                            ║
        ║  1. Cargar datos fundamentales de la base de datos                    ║
        ║  2. Calcular scores (Z-Scores normalizados por sector)                ║
        ║  3. Ordenar por alpha_score descendente                               ║
        ║  4. Retornar lista de símbolos                                        ║
        ║                                                                       ║
        ║  NOTA: Esta capa NO usa 'candidates' como entrada.                    ║
        ║  Es el INICIO del embudo, analiza TODOS los activos disponibles.      ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Cargar datos fundamentales
        raw_data = self.load_data()
        
        if raw_data.empty:
            print("⚠️ WARNING: No hay datos en tabla 'fundamentals'.")
            return []

        # Calcular scores
        scored_data = self.compute_factors(raw_data)
        
        if scored_data.empty:
            print("⚠️ WARNING: Datos insuficientes tras limpieza.")
            return []

        # Ordenar por score (mejores primero)
        top_candidates = scored_data.sort_values(by='alpha_score', ascending=False)
        
        # Mostrar ranking para transparencia
        print("\n--- Ranking Fundamental (Capa 1) ---")
        print(top_candidates[['symbol', 'pe_ratio', 'roe', 'alpha_score']].head(5).to_string(index=False))
        
        # Retornar lista de símbolos
        return top_candidates['symbol'].tolist()

    # =========================================================================
    # MÉTODO: generate_signal (Generar Señal - Interfaz IStrategy)
    # =========================================================================
    
    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        """
        Esta capa no genera señales de trading directas.
        Solo filtra el universo para las capas siguientes.
        
        Retorna 0.0 (neutral).
        """
        return 0.0


# =============================================================================
# EJEMPLO DE USO
# =============================================================================
#
# from src.strategies.alpha.macro import MacroScannerStrategy
#
# # Crear scanner
# scanner = MacroScannerStrategy("data/trading.db")
#
# # Obtener mejores candidatos
# top_stocks = scanner.update_universe()
# print(f"Top candidatos: {top_stocks}")
#
# # Estos candidatos pasan a Capa 2 (Filtro Técnico)
#
# =============================================================================