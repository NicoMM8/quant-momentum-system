# =============================================================================
# MICRO.PY - CAPA 3: ESTRATEGIA DE MICROESTRUCTURA
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este es el TERCER y ÚLTIMO FILTRO del embudo de trading (Capa 3).
# Analiza la MICROESTRUCTURA del mercado para encontrar el TIMING preciso.
#
# ¿QUÉ ES MICROESTRUCTURA DE MERCADO?
# ────────────────────────────────────
# Es el estudio de CÓMO se forman los precios a nivel granular:
# • ¿Quién está comprando/vendiendo?
# • ¿Los institucionales están acumulando o distribuyendo?
# • ¿Hay más presión compradora o vendedora?
#
# Mientras que el análisis técnico mira el "bosque" (tendencias),
# la microestructura mira cada "árbol" (cada transacción).
#
# COMPONENTES DE ESTE ARCHIVO:
# ────────────────────────────
#
# 1. ORDER FLOW ANALYZER
#    → Analiza el flujo de órdenes de compra/venta
#    → Detecta presión compradora vs vendedora
#
# 2. SMART MONEY CONCEPTS (SMC)
#    → Técnicas para detectar actividad institucional
#    → Order Blocks, Break of Structure, etc.
#
# 3. MICROSTRUCTURE STRATEGY
#    → Combina todo para generar señales de entrada
#
# ¿POR QUÉ ES IMPORTANTE?
# ─────────────────────────
# Un activo puede ser:
# • Fundamentalmente bueno (Capa 1) ✓
# • Técnicamente en tendencia (Capa 2) ✓
# • PERO aún así perder dinero si entras en mal momento
#
# La microestructura te dice CUÁNDO entrar.
#
# =============================================================================

# src/strategies/alpha/micro.py
"""
Capa 3 del Sistema: Estrategia de Microestructura.
Analiza Order Flow, Order Book Imbalance y Smart Money Concepts.
"""

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

from dataclasses import dataclass
# @dataclass para clases de datos simples

from typing import Dict, List, Optional, Tuple
# Type hints para mejor legibilidad

import pandas as pd
# Pandas para manipulación de datos

import numpy as np
# NumPy para cálculos numéricos

from src.core.interfaces import ISignalGenerator
# Interfaz para estrategias que generan señales de trading


# =============================================================================
# DATACLASS: OrderFlowSignal (Señal de Order Flow)
# =============================================================================

@dataclass
class OrderFlowSignal:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    SEÑAL DE ORDER FLOW                                    ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Representa una señal generada por análisis de Order Flow.                ║
    ║                                                                           ║
    ║  CAMPOS:                                                                  ║
    ║  ─────────                                                                ║
    ║  • symbol: Ticker del activo (ej: "AAPL")                                 ║
    ║  • timestamp: Momento de la señal                                         ║
    ║  • signal_type: 'BUY', 'SELL', o 'NEUTRAL'                                ║
    ║  • strength: Fuerza (-1.0 a 1.0)                                          ║
    ║  • obi: Order Book Imbalance (-1 a 1)                                     ║
    ║  • delta: Diferencia Buy Volume - Sell Volume                             ║
    ║  • confidence: Nivel de confianza en la señal (0-1)                       ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    symbol: str
    timestamp: pd.Timestamp
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    strength: float   # -1.0 a 1.0
    obi: float        # Order Book Imbalance
    delta: float      # Buy Volume - Sell Volume
    confidence: float # Confianza en la señal (0-1)


# =============================================================================
# CLASE: OrderFlowAnalyzer (Analizador de Order Flow)
# =============================================================================

class OrderFlowAnalyzer:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                   ANALIZADOR DE ORDER FLOW                                ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Analiza el flujo de órdenes para detectar presión compradora/vendedora.  ║
    ║                                                                           ║
    ║  ¿QUÉ ES ORDER FLOW?                                                      ║
    ║  ─────────────────────                                                    ║
    ║  Es el estudio de cómo las órdenes de compra y venta afectan el precio.   ║
    ║                                                                           ║
    ║  Imagina un mercado de frutas:                                            ║
    ║  • Si llegan 100 compradores y solo 20 vendedores → precio SUBE           ║
    ║  • Si llegan 20 compradores y 100 vendedores → precio BAJA                ║
    ║                                                                           ║
    ║  Order Flow mide esta PRESIÓN antes de que el precio reaccione.           ║
    ║                                                                           ║
    ║  MÉTRICAS ANALIZADAS:                                                     ║
    ║  ─────────────────────                                                    ║
    ║                                                                           ║
    ║  1. OBI (Order Book Imbalance)                                            ║
    ║     → Desequilibrio entre órdenes de compra y venta                       ║
    ║     → OBI > 0: más presión compradora                                     ║
    ║     → OBI < 0: más presión vendedora                                      ║
    ║                                                                           ║
    ║  2. Delta (Volumen Neto)                                                  ║
    ║     → Buy Volume - Sell Volume                                            ║
    ║     → Delta positivo: compradores dominando                               ║
    ║     → Delta negativo: vendedores dominando                                ║
    ║                                                                           ║
    ║  3. Absorción                                                             ║
    ║     → Alto volumen SIN movimiento de precio                               ║
    ║     → Indica que alguien está "absorbiendo" órdenes                       ║
    ║     → Posible cambio de tendencia                                         ║
    ║                                                                           ║
    ║  4. Agotamiento                                                           ║
    ║     → Movimiento fuerte con volumen decreciente                           ║
    ║     → La fuerza se está "agotando"                                        ║
    ║     → Posible reversión                                                   ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, obi_threshold: float = 0.4):
        """
        Inicializa el analizador con un umbral de OBI.
        
        PARÁMETROS:
        • obi_threshold: Umbral para considerar un OBI como significativo
          (0.4 = 40% de desequilibrio, bastante alto)
        """
        self.obi_threshold = obi_threshold
    
    # =========================================================================
    # MÉTODO: calculate_obi (Order Book Imbalance)
    # =========================================================================
    
    def calculate_obi(self, bid_volume: float, ask_volume: float) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                ORDER BOOK IMBALANCE (OBI)                             ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Mide el desequilibrio entre compradores y vendedores.                ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  OBI = (BidVolume - AskVolume) / (BidVolume + AskVolume)              ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • OBI = +1.0: Solo hay compradores (muy alcista)                     ║
        ║  • OBI = +0.5: Compradores dominan 3:1                                ║
        ║  • OBI = 0.0: Equilibrio perfecto                                     ║
        ║  • OBI = -0.5: Vendedores dominan 3:1                                 ║
        ║  • OBI = -1.0: Solo hay vendedores (muy bajista)                      ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Bid Volume = 7,000 acciones queriendo COMPRAR                        ║
        ║  Ask Volume = 3,000 acciones queriendo VENDER                         ║
        ║  OBI = (7000 - 3000) / (7000 + 3000) = 4000/10000 = +0.40             ║
        ║  → Presión compradora significativa                                   ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        total = bid_volume + ask_volume
        if total == 0:
            return 0.0  # Evitar división por cero
        return (bid_volume - ask_volume) / total
    
    # =========================================================================
    # MÉTODO: calculate_delta (Volumen Neto)
    # =========================================================================
    
    def calculate_delta(self, df: pd.DataFrame) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    DELTA (VOLUMEN NETO)                               ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Calcula el Delta acumulativo (Buy Volume - Sell Volume).             ║
        ║                                                                       ║
        ║  ¿QUÉ ES EL DELTA?                                                    ║
        ║  ─────────────────────                                                ║
        ║  Es la diferencia entre volumen agresivo de compra y venta.           ║
        ║                                                                       ║
        ║  APROXIMACIÓN SIN DATOS L2:                                           ║
        ║  ───────────────────────────                                          ║
        ║  Sin datos de Nivel 2 (order book real), aproximamos:                 ║
        ║  • Si close > open → vela alcista → volumen = compra                  ║
        ║  • Si close < open → vela bajista → volumen = venta                   ║
        ║                                                                       ║
        ║  No es perfecto, pero es una buena aproximación.                      ║
        ║                                                                       ║
        ║  INTERPRETACIÓN DEL DELTA ACUMULATIVO:                                ║
        ║  ──────────────────────────────────────                               ║
        ║  • Delta subiendo: Más compradores que vendedores                     ║
        ║  • Delta bajando: Más vendedores que compradores                      ║
        ║  • Divergencia Delta/Precio: Posible cambio de tendencia              ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Volumen de compra: cuando el precio cierra arriba del open
        buy_volume = df['volume'].where(df['close'] > df['open'], 0)
        
        # Volumen de venta: cuando el precio cierra abajo del open
        sell_volume = df['volume'].where(df['close'] < df['open'], 0)
        
        # Delta acumulativo
        return (buy_volume - sell_volume).cumsum()
    
    # =========================================================================
    # MÉTODO: detect_absorption (Detectar Absorción)
    # =========================================================================
    
    def detect_absorption(
        self, 
        df: pd.DataFrame, 
        threshold: float = 2.0
    ) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    DETECTAR ABSORCIÓN                                 ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Detecta velas donde hay ALTO VOLUMEN pero POCO MOVIMIENTO.           ║
        ║                                                                       ║
        ║  ¿QUÉ ES ABSORCIÓN?                                                   ║
        ║  ─────────────────────                                                ║
        ║  Cuando un gran jugador (institucional) está comprando o vendiendo,   ║
        ║  pero el precio no se mueve porque su contraparte también es grande.  ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Imagina que el precio está cayendo y un fondo quiere comprar.        ║
        ║  Hay muchos vendedores, así que puede comprar SIN subir el precio.    ║
        ║  Vemos: Volumen ALTO, pero precio sin moverse.                        ║
        ║  → Absorción de ventas. El fondo está "absorbiendo" las ventas.       ║
        ║  → Cuando se acaben los vendedores, el precio EXPLOTARÁ al alza.      ║
        ║                                                                       ║
        ║  DETECCIÓN:                                                           ║
        ║  • Volumen > 2x el promedio (threshold = 2.0)                         ║
        ║  • Rango H-L < 50% del promedio                                       ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Rango de precio de la vela
        price_range = (df['high'] - df['low']).abs()
        
        # Promedios móviles de 20 períodos
        avg_range = price_range.rolling(20).mean()
        avg_volume = df['volume'].rolling(20).mean()
        
        # Detección de absorción:
        # Alto volumen (más del doble del normal)
        high_volume = df['volume'] > avg_volume * threshold
        
        # Rango bajo (menos de la mitad del normal)
        low_range = price_range < avg_range * 0.5
        
        # Absorción = ambas condiciones
        return high_volume & low_range
    
    # =========================================================================
    # MÉTODO: detect_exhaustion (Detectar Agotamiento)
    # =========================================================================
    
    def detect_exhaustion(
        self, 
        df: pd.DataFrame,
        lookback: int = 5
    ) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    DETECTAR AGOTAMIENTO                               ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Detecta movimientos fuertes seguidos de volumen decreciente.         ║
        ║                                                                       ║
        ║  ¿QUÉ ES AGOTAMIENTO?                                                 ║
        ║  ───────────────────────                                              ║
        ║  Cuando un movimiento de precio pierde fuerza.                        ║
        ║  Es como un coche que acelera fuerte pero se queda sin gasolina.      ║
        ║                                                                       ║
        ║  PATRÓN:                                                              ║
        ║  ─────────                                                            ║
        ║  1. Movimiento fuerte de precio (más de 2 desviaciones estándar)      ║
        ║  2. Volumen decreciente (cayendo más del 30%)                         ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  El precio sube 5% en un día (movimiento fuerte)                      ║
        ║  Pero el volumen es 40% menor que ayer                                ║
        ║  → Los compradores se están "agotando"                                ║
        ║  → Posible reversión a la baja próximamente                           ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Retornos del precio
        returns = df['close'].pct_change()
        
        # Movimiento fuerte = más de 2 desviaciones estándar
        strong_move = returns.abs() > returns.rolling(20).std() * 2
        
        # Cambio de volumen en los últimos N períodos
        vol_change = df['volume'].pct_change(lookback)
        
        # Volumen decreciente = caída de más del 30%
        declining_volume = vol_change < -0.3
        
        # Agotamiento = movimiento fuerte + volumen decreciente
        return strong_move & declining_volume


# =============================================================================
# CLASE: SmartMoneyConcepts (Conceptos de Dinero Inteligente)
# =============================================================================

class SmartMoneyConcepts:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                   SMART MONEY CONCEPTS (SMC)                              ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Técnicas para detectar actividad de institucionales ("Smart Money").     ║
    ║                                                                           ║
    ║  ¿QUÉ ES SMART MONEY?                                                     ║
    ║  ───────────────────────                                                  ║
    ║  Son los grandes jugadores: fondos de inversión, bancos, hedge funds.     ║
    ║  Tienen acceso a mejor información y recursos.                            ║
    ║  La idea: seguir lo que hacen ellos, no luchar contra ellos.              ║
    ║                                                                           ║
    ║  CONCEPTOS CLAVE:                                                         ║
    ║  ─────────────────                                                        ║
    ║                                                                           ║
    ║  1. SWING POINTS (Puntos Pivote)                                          ║
    ║     → Máximos y mínimos locales importantes                               ║
    ║     → Definen la estructura del mercado                                   ║
    ║                                                                           ║
    ║  2. BOS (Break of Structure)                                              ║
    ║     → Cuando el precio rompe un swing point anterior                      ║
    ║     → Confirma cambio de tendencia                                        ║
    ║                                                                           ║
    ║  3. ORDER BLOCKS                                                          ║
    ║     → Zonas donde los institucionales colocaron órdenes grandes           ║
    ║     → El precio tiende a "respetar" estas zonas                           ║
    ║                                                                           ║
    ║  ESTRUCTURA DE MERCADO (SMC):                                             ║
    ║  ──────────────────────────────                                           ║
    ║                                                                           ║
    ║     SH = Swing High, SL = Swing Low, BOS = Break of Structure             ║
    ║                                                                           ║
    ║              SH                                                           ║
    ║             /  \         SH (Higher High)                                 ║
    ║            /    \       /  \                                              ║
    ║           /      \     /    \         ← Tendencia Alcista                 ║
    ║      SL ─╯        \   /      \                                            ║
    ║                    \ /        BOS (rompe SH anterior)                     ║
    ║                     SL (Higher Low)                                       ║
    ║                                                                           ║
    ║  En tendencia alcista: Higher Highs y Higher Lows                         ║
    ║  En tendencia bajista: Lower Highs y Lower Lows                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # =========================================================================
    # MÉTODO: identify_swing_points (Identificar Puntos Pivote)
    # =========================================================================
    
    @staticmethod
    def identify_swing_points(
        df: pd.DataFrame, 
        sensitivity: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    IDENTIFICAR SWING POINTS                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Encuentra los Swing Highs y Swing Lows en los datos.                 ║
        ║                                                                       ║
        ║  ¿QUÉ ES UN SWING POINT?                                              ║
        ║  ─────────────────────────                                            ║
        ║  Es un punto donde el precio "pivota" (cambia de dirección).          ║
        ║                                                                       ║
        ║  SWING HIGH:                                                          ║
        ║  Un máximo que es MÁS ALTO que N velas a cada lado.                   ║
        ║                                                                       ║
        ║        ●  ← Swing High                                                ║
        ║       / \                                                             ║
        ║      /   \                                                            ║
        ║     /     \                                                           ║
        ║                                                                       ║
        ║  SWING LOW:                                                           ║
        ║  Un mínimo que es MÁS BAJO que N velas a cada lado.                   ║
        ║                                                                       ║
        ║     \     /                                                           ║
        ║      \   /                                                            ║
        ║       \ /                                                             ║
        ║        ●  ← Swing Low                                                 ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  • sensitivity: N velas a cada lado para confirmar                    ║
        ║    (3 = necesita 3 velas menores a cada lado)                         ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        highs = df['high']
        lows = df['low']
        
        # Inicializar series booleanas
        swing_highs = pd.Series(False, index=df.index)
        swing_lows = pd.Series(False, index=df.index)
        
        # Iterar por el DataFrame (excluyendo bordes)
        for i in range(sensitivity, len(df) - sensitivity):
            # ─────────────────────────────────────────────────────────────────
            # DETECCIÓN DE SWING HIGH
            # ─────────────────────────────────────────────────────────────────
            # El high en i debe ser MAYOR que los N anteriores Y los N siguientes
            if all(highs.iloc[i] > highs.iloc[i-sensitivity:i]) and \
               all(highs.iloc[i] > highs.iloc[i+1:i+sensitivity+1]):
                swing_highs.iloc[i] = True
            
            # ─────────────────────────────────────────────────────────────────
            # DETECCIÓN DE SWING LOW
            # ─────────────────────────────────────────────────────────────────
            # El low en i debe ser MENOR que los N anteriores Y los N siguientes
            if all(lows.iloc[i] < lows.iloc[i-sensitivity:i]) and \
               all(lows.iloc[i] < lows.iloc[i+1:i+sensitivity+1]):
                swing_lows.iloc[i] = True
        
        return swing_highs, swing_lows
    
    # =========================================================================
    # MÉTODO: detect_bos (Break of Structure)
    # =========================================================================
    
    @staticmethod
    def detect_bos(df: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    BREAK OF STRUCTURE (BOS)                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Detecta cuando el precio rompe la estructura anterior.               ║
        ║                                                                       ║
        ║  ¿QUÉ ES BOS?                                                         ║
        ║  ─────────────                                                        ║
        ║  Es cuando el precio CIERRA por encima del último Swing High          ║
        ║  (BOS alcista) o por debajo del último Swing Low (BOS bajista).       ║
        ║                                                                       ║
        ║  BOS ALCISTA:                                                         ║
        ║  ───────────────                                                      ║
        ║                                                                       ║
        ║           ┌── Último SH ──┐                                           ║
        ║           │               │                                           ║
        ║      ─────┴───────────────┴───────●──── ← Precio CIERRA arriba        ║
        ║                                   ↑                                   ║
        ║                                  BOS! (alcista)                       ║
        ║                                                                       ║
        ║  BOS BAJISTA:                                                         ║
        ║  ───────────────                                                      ║
        ║                                                                       ║
        ║      ───────●──────────────────────── ← Precio CIERRA abajo           ║
        ║             ↓                                                         ║
        ║           ┌── Último SL ──┐  BOS! (bajista)                           ║
        ║           │               │                                           ║
        ║           └───────────────┘                                           ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • +1: BOS alcista (ruptura al alza)                                  ║
        ║  • -1: BOS bajista (ruptura a la baja)                                ║
        ║  •  0: Sin BOS                                                        ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        bos = pd.Series(0, index=df.index)
        
        last_sh = None  # Último Swing High
        last_sl = None  # Último Swing Low
        
        for i in range(len(df)):
            # Actualizar último swing high si hay uno
            if swing_highs.iloc[i]:
                last_sh = df['high'].iloc[i]
            
            # Actualizar último swing low si hay uno
            if swing_lows.iloc[i]:
                last_sl = df['low'].iloc[i]
            
            # ─────────────────────────────────────────────────────────────────
            # CHECK BOS ALCISTA
            # ─────────────────────────────────────────────────────────────────
            if last_sh is not None and df['close'].iloc[i] > last_sh:
                bos.iloc[i] = 1
                last_sh = df['high'].iloc[i]  # Actualizar referencia
            
            # ─────────────────────────────────────────────────────────────────
            # CHECK BOS BAJISTA
            # ─────────────────────────────────────────────────────────────────
            if last_sl is not None and df['close'].iloc[i] < last_sl:
                bos.iloc[i] = -1
                last_sl = df['low'].iloc[i]  # Actualizar referencia
        
        return bos
    
    # =========================================================================
    # MÉTODO: identify_order_blocks (Order Blocks)
    # =========================================================================
    
    @staticmethod
    def identify_order_blocks(
        df: pd.DataFrame, 
        lookback: int = 10
    ) -> pd.DataFrame:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      ORDER BLOCKS                                     ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Identifica zonas donde los institucionales colocaron órdenes.        ║
        ║                                                                       ║
        ║  ¿QUÉ ES UN ORDER BLOCK?                                              ║
        ║  ───────────────────────────                                          ║
        ║  Es la última vela en contra de la tendencia antes de un              ║
        ║  movimiento fuerte a favor de la tendencia.                           ║
        ║                                                                       ║
        ║  ORDER BLOCK ALCISTA:                                                 ║
        ║  ─────────────────────                                                ║
        ║  Última vela BAJISTA antes de un rally fuerte.                        ║
        ║  El institucional "cargó" sus compras en esa zona.                    ║
        ║                                                                       ║
        ║     │              ┌───── Movimiento alcista fuerte                   ║
        ║     │             /                                                   ║
        ║  [▓▓▓▓]  ← Order Block (vela bajista antes del rally)                 ║
        ║     │                                                                 ║
        ║                                                                       ║
        ║  Si el precio vuelve a esa zona, probablemente REBOTE.                ║
        ║                                                                       ║
        ║  ORDER BLOCK BAJISTA:                                                 ║
        ║  ─────────────────────                                                ║
        ║  Última vela ALCISTA antes de una caída fuerte.                       ║
        ║  El institucional "descargó" sus ventas en esa zona.                  ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        result = pd.DataFrame(index=df.index)
        result['ob_bullish'] = False
        result['ob_bearish'] = False
        
        returns = df['close'].pct_change()
        avg_return = returns.rolling(20).std()
        
        for i in range(lookback, len(df)):
            # ─────────────────────────────────────────────────────────────────
            # BUSCAR ORDER BLOCK ALCISTA
            # ─────────────────────────────────────────────────────────────────
            # Movimiento alcista fuerte (más de 2 std)
            if returns.iloc[i] > avg_return.iloc[i] * 2:
                # Buscar última vela BAJISTA antes del movimiento
                for j in range(i-1, max(0, i-lookback), -1):
                    if df['close'].iloc[j] < df['open'].iloc[j]:  # Vela bajista
                        result['ob_bullish'].iloc[j] = True
                        break
            
            # ─────────────────────────────────────────────────────────────────
            # BUSCAR ORDER BLOCK BAJISTA
            # ─────────────────────────────────────────────────────────────────
            # Movimiento bajista fuerte (más de 2 std negativo)
            if returns.iloc[i] < -avg_return.iloc[i] * 2:
                # Buscar última vela ALCISTA antes del movimiento
                for j in range(i-1, max(0, i-lookback), -1):
                    if df['close'].iloc[j] > df['open'].iloc[j]:  # Vela alcista
                        result['ob_bearish'].iloc[j] = True
                        break
        
        return result


# =============================================================================
# CLASE: MicroStructureStrategy (Estrategia de Microestructura)
# =============================================================================

class MicroStructureStrategy(ISignalGenerator):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║              CAPA 3: ESTRATEGIA DE MICROESTRUCTURA                        ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Combina Order Flow y SMC para generar señales de timing precisas.        ║
    ║                                                                           ║
    ║  COMPONENTES DE LA SEÑAL:                                                 ║
    ║  ─────────────────────────                                                ║
    ║  • 40% Order Flow (OBI): Presión compradora/vendedora                     ║
    ║  • 40% Estructura (SMC): Tendencia según swing points                     ║
    ║  • 20% BOS: Confirmación de ruptura de estructura                         ║
    ║                                                                           ║
    ║  RANGO DE SEÑAL:                                                          ║
    ║  ─────────────────                                                        ║
    ║  • +1.0: Señal de COMPRA muy fuerte                                       ║
    ║  • +0.5: Señal de compra moderada                                         ║
    ║  •  0.0: Neutral (no operar)                                              ║
    ║  • -0.5: Señal de venta moderada                                          ║
    ║  • -1.0: Señal de VENTA muy fuerte                                        ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, obi_threshold: float = 0.4):
        """
        Inicializa la estrategia de microestructura.
        
        PARÁMETROS:
        • obi_threshold: Umbral de OBI para considerar señal significativa
        """
        self.obi_threshold = obi_threshold
        self.order_flow = OrderFlowAnalyzer(obi_threshold)
        self.smc = SmartMoneyConcepts()
    
    def update_universe(
        self, 
        candidates: List[str], 
        data_context: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[str]:
        """
        La Capa Micro NO filtra el universo.
        Solo analiza timing para los activos que ya pasaron Capa 1 y 2.
        Retorna los mismos candidatos.
        """
        return candidates
    
    # =========================================================================
    # MÉTODO: analyze_orderflow (Analizar Order Flow)
    # =========================================================================
    
    def analyze_orderflow(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Analiza el order flow de un activo.
        
        RETORNA:
        Dict con:
        • obi: Order Book Imbalance
        • delta: Delta acumulativo
        • absorption: % de velas con absorción
        """
        if df.empty or len(df) < 20:
            return {'obi': 0.0, 'delta': 0.0, 'absorption': 0.0}
        
        # Simular OBI usando precio (en producción usar datos L2)
        bullish_candles = (df['close'] > df['open']).sum()
        bearish_candles = (df['close'] < df['open']).sum()
        
        obi = self.order_flow.calculate_obi(bullish_candles, bearish_candles)
        delta = self.order_flow.calculate_delta(df).iloc[-1]
        absorption = self.order_flow.detect_absorption(df).sum() / len(df)
        
        return {
            'obi': obi,
            'delta': delta,
            'absorption': absorption
        }
    
    # =========================================================================
    # MÉTODO: analyze_structure (Analizar Estructura con SMC)
    # =========================================================================
    
    def analyze_structure(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza la estructura de mercado usando Smart Money Concepts.
        
        RETORNA:
        Dict con:
        • trend: 'bullish', 'bearish', o 'neutral'
        • bos: Último BOS (+1, -1, o 0)
        • order_blocks: Cantidad de OB detectados
        """
        if df.empty or len(df) < 20:
            return {'trend': 'neutral', 'bos': 0, 'order_blocks': 0}
        
        # Identificar swing points
        swing_highs, swing_lows = self.smc.identify_swing_points(df)
        
        # Detectar BOS
        bos = self.smc.detect_bos(df, swing_highs, swing_lows)
        
        # Identificar Order Blocks
        order_blocks = self.smc.identify_order_blocks(df)
        
        # Determinar tendencia basada en BOS recientes
        recent_bos = bos.tail(20).sum()
        if recent_bos > 0:
            trend = 'bullish'
        elif recent_bos < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'trend': trend,
            'bos': bos.iloc[-1],
            'order_blocks_bullish': order_blocks['ob_bullish'].sum(),
            'order_blocks_bearish': order_blocks['ob_bearish'].sum()
        }
    
    # =========================================================================
    # MÉTODO: generate_signal (Generar Señal Final)
    # =========================================================================
    
    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    GENERAR SEÑAL DE TRADING                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Combina Order Flow y SMC para generar señal final.                   ║
        ║                                                                       ║
        ║  CÁLCULO:                                                             ║
        ║  ──────────                                                           ║
        ║  señal = 0.4 × OBI + 0.4 × tendencia_SMC + 0.2 × BOS                  ║
        ║                                                                       ║
        ║  UMBRAL:                                                              ║
        ║  ─────────                                                            ║
        ║  Si |señal| < 0.2, retornamos 0 (no operar).                          ║
        ║  Evita operar con señales débiles.                                    ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        if not data:
            return 0.0
        
        signals = []
        
        for symbol, df in data.items():
            if df.empty:
                continue
            
            # ─────────────────────────────────────────────────────────────────
            # ANÁLISIS DE ORDER FLOW (40% del peso)
            # ─────────────────────────────────────────────────────────────────
            of_analysis = self.analyze_orderflow(df)
            of_signal = of_analysis['obi']
            
            # ─────────────────────────────────────────────────────────────────
            # ANÁLISIS DE ESTRUCTURA SMC (40% del peso)
            # ─────────────────────────────────────────────────────────────────
            struct_analysis = self.analyze_structure(df)
            if struct_analysis['trend'] == 'bullish':
                struct_signal = 0.5
            elif struct_analysis['trend'] == 'bearish':
                struct_signal = -0.5
            else:
                struct_signal = 0.0
            
            # ─────────────────────────────────────────────────────────────────
            # CONFIRMACIÓN DE BOS (20% del peso)
            # ─────────────────────────────────────────────────────────────────
            bos_signal = struct_analysis['bos'] * 0.5
            
            # ─────────────────────────────────────────────────────────────────
            # SEÑAL COMBINADA
            # ─────────────────────────────────────────────────────────────────
            combined = (
                of_signal * 0.4 +
                struct_signal * 0.4 +
                bos_signal * 0.2
            )
            
            signals.append(combined)
        
        if not signals:
            return 0.0
        
        # Promedio de señales
        avg_signal = sum(signals) / len(signals)
        
        # Aplicar threshold (evitar señales débiles)
        if abs(avg_signal) < 0.2:
            return 0.0
        
        # Limitar al rango -1 a +1
        return max(-1.0, min(1.0, avg_signal))


# =============================================================================
# EJEMPLO DE USO
# =============================================================================
#
# from src.strategies.alpha.micro import MicroStructureStrategy
# import pandas as pd
#
# # Datos simulados
# data = {
#     'AAPL': pd.DataFrame({
#         'open': [150, 151, 152, 153, 154],
#         'high': [151, 152, 153, 154, 156],
#         'low': [149, 150, 151, 152, 153],
#         'close': [151, 152, 153, 155, 155.5],
#         'volume': [1000, 1200, 1100, 1500, 1300]
#     })
# }
#
# # Crear estrategia
# micro = MicroStructureStrategy()
#
# # Generar señal
# signal = micro.generate_signal(data)
# print(f"Señal de trading: {signal:.2f}")
#
# # Interpretación:
# # signal > 0.5: Comprar
# # signal < -0.5: Vender
# # -0.2 < signal < 0.2: No operar
#
# =============================================================================
