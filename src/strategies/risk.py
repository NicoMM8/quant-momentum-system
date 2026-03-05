# =============================================================================
# RISK.PY - GESTIÓN DE RIESGO Y POSITION SIZING
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este es probablemente el archivo MÁS IMPORTANTE del sistema de trading.
# Contiene la lógica de GESTIÓN DE RIESGO, que determina:
#
# 1. ¿CUÁNTO ARRIESGAR? → PositionSizer (tamaño de posición)
# 2. ¿PODEMOS OPERAR? → PortfolioRiskManager (límites del portfolio)
# 3. ¿CÓMO VAMOS? → RiskMetrics (métricas de rendimiento)
#
# ¿POR QUÉ ES TAN IMPORTANTE?
# ----------------------------
# "El trading no es sobre ganar dinero, es sobre NO PERDERLO."
#
# Una buena estrategia con mala gestión de riesgo = RUINA
# Una estrategia mediocre con buena gestión de riesgo = SOBREVIVIR
#
# El 90% de los traders pierden dinero. La diferencia entre el 10%
# ganador y el 90% perdedor NO es la estrategia, es la gestión de riesgo.
#
# ANALOGÍA DEL CASINO:
# --------------------
# El casino SIEMPRE gana a largo plazo, pero no porque gane cada apuesta.
# Los casinos pierden constantemente (pagan premios).
# Pero tienen LÍMITES estrictos (máximo de apuesta) y una VENTAJA estadística.
# Este archivo te da esos límites.
#
# REGLA DE ORO: No arriesgar más del 1-2% del capital en un solo trade.
# Si tienes $100,000 → máximo $1,000-$2,000 en riesgo por trade.
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

from dataclasses import dataclass
# @dataclass es un decorador que genera automáticamente __init__, __repr__, etc.
# Ideal para clases que principalmente almacenan datos

from typing import Optional, Dict, List
# Optional[X] = puede ser X o None
# Dict[K, V] = diccionario con claves tipo K y valores tipo V
# List[X] = lista de elementos tipo X

import pandas as pd
# Pandas para trabajar con series de datos (retornos, equity curves)

import numpy as np
# NumPy para cálculos matemáticos (sqrt, inf)

import yaml
# YAML para cargar configuración desde archivos

import os
# os para verificar si existen archivos


# =============================================================================
# DATACLASS: RiskParameters (Parámetros de Riesgo)
# =============================================================================

@dataclass
class RiskParameters:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    PARÁMETROS DE RIESGO CONFIGURABLES                     ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase contiene TODOS los parámetros de riesgo del sistema.          ║
    ║  Usar @dataclass simplifica la creación de clases de datos.               ║
    ║                                                                           ║
    ║  PARÁMETROS DE POSICIÓN:                                                  ║
    ║  ─────────────────────────                                                ║
    ║  • max_position_pct (10%): Máximo % del capital en UNA posición           ║
    ║    → Si tienes $100K, máximo $10K por trade                               ║
    ║                                                                           ║
    ║  • max_portfolio_risk (2%): Riesgo máximo del portfolio                   ║
    ║    → Si pierdes 2% del capital, algo anda mal                             ║
    ║                                                                           ║
    ║  PARÁMETROS DE KELLY:                                                     ║
    ║  ─────────────────────                                                    ║
    ║  • kelly_fraction (25%): Qué fracción de Kelly usar                       ║
    ║    → Kelly completo es muy agresivo, usamos 1/4                           ║
    ║                                                                           ║
    ║  PARÁMETROS DE STOPS:                                                     ║
    ║  ─────────────────────                                                    ║
    ║  • stop_loss_pct (0.5%): Cuánto perder por trade                          ║
    ║  • take_profit_pct (1.5%): Cuánto ganar por trade (ratio 1:3)             ║
    ║                                                                           ║
    ║  LÍMITES DE PÉRDIDA:                                                      ║
    ║  ─────────────────────                                                    ║
    ║  • max_daily_loss (3%): Límite de pérdida por día                         ║
    ║  • max_weekly_loss (6%): Límite de pérdida por semana                     ║
    ║    → Si pierdes esto, PARAS DE OPERAR                                     ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    max_position_pct: float = 0.10      # 10% máximo por posición
    max_portfolio_risk: float = 0.02    # 2% máximo de riesgo total
    kelly_fraction: float = 0.25        # 25% del Kelly (más conservador)
    stop_loss_pct: float = 0.005        # 0.5% de stop loss
    take_profit_pct: float = 0.015      # 1.5% de take profit (ratio 1:3)
    max_daily_loss: float = 0.03        # 3% límite diario
    max_weekly_loss: float = 0.06       # 6% límite semanal


# =============================================================================
# CLASE: PositionSizer (Calculador de Tamaño de Posición)
# =============================================================================

class PositionSizer:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    CALCULADOR DE TAMAÑO DE POSICIÓN                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase responde a la pregunta: "¿Cuánto dinero pongo en este trade?" ║
    ║                                                                           ║
    ║  ¿POR QUÉ ES IMPORTANTE EL TAMAÑO?                                        ║
    ║  ───────────────────────────────────                                      ║
    ║  Muy poco = pierdes oportunidades de ganar                                ║
    ║  Demasiado = un mal trade te arruina                                      ║
    ║                                                                           ║
    ║  Es como apostar en el casino:                                            ║
    ║  • Si apuestas $1 en cada mano, ganarás poco aunque tengas buena racha    ║
    ║  • Si apuestas TODO en una mano, una mala te deja sin nada                ║
    ║  • El tamaño ÓPTIMO maximiza ganancias sin arriesgar la ruina             ║
    ║                                                                           ║
    ║  MÉTODOS DISPONIBLES:                                                     ║
    ║  ─────────────────────                                                    ║
    ║                                                                           ║
    ║  1. PORCENTAJE FIJO (fixed_percentage)                                    ║
    ║     → Siempre el mismo % del capital                                      ║
    ║     → Simple pero no óptimo                                               ║
    ║                                                                           ║
    ║  2. CRITERIO DE KELLY (kelly_criterion)                                   ║
    ║     → Matemáticamente óptimo                                              ║
    ║     → Usa tu win rate y ratio ganancia/pérdida                            ║
    ║                                                                           ║
    ║  3. AJUSTADO POR VOLATILIDAD (volatility_adjusted)                        ║
    ║     → Menos tamaño en mercados volátiles                                  ║
    ║     → Más tamaño en mercados calmados                                     ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, params: Optional[RiskParameters] = None):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                             __INIT__                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Inicializa el PositionSizer con parámetros de riesgo.                  │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  • params: Objeto RiskParameters con la configuración                   │
        │    Si no se proporciona, usa los valores por defecto                    │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        self.params = params or RiskParameters()
        # "or" funciona como: si params es None, usa RiskParameters()
    
    @staticmethod
    def load_from_config(config_path: str = "config/settings.yaml") -> 'PositionSizer':
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                        LOAD_FROM_CONFIG                                 │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Factory method que crea un PositionSizer desde archivo YAML.           │
        │                                                                         │
        │  USO:                                                                   │
        │  sizer = PositionSizer.load_from_config("config/settings.yaml")         │
        │                                                                         │
        │  El archivo YAML debería tener esta estructura:                         │
        │  risk:                                                                  │
        │    max_position_pct: 0.10                                               │
        │    stop_loss_pct: 0.005                                                 │
        │    ...                                                                  │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                risk_config = config.get('risk', {})
                params = RiskParameters(
                    max_position_pct=risk_config.get('max_position_pct', 0.10),
                    max_portfolio_risk=risk_config.get('max_portfolio_risk', 0.02),
                    kelly_fraction=risk_config.get('kelly_fraction', 0.25),
                    stop_loss_pct=risk_config.get('stop_loss_pct', 0.005),
                    take_profit_pct=risk_config.get('take_profit_pct', 0.015),
                    max_daily_loss=risk_config.get('max_daily_loss', 0.03),
                    max_weekly_loss=risk_config.get('max_weekly_loss', 0.06)
                )
                return PositionSizer(params)
        return PositionSizer()
    
    # =========================================================================
    # MÉTODO 1: Porcentaje Fijo
    # =========================================================================
    
    def fixed_percentage(self, capital: float, risk_pct: Optional[float] = None) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      MÉTODO: PORCENTAJE FIJO                          ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  El método más simple: invertir siempre el mismo % del capital.       ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Tamaño de Posición = Capital × Porcentaje                            ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Capital = $100,000                                                   ║
        ║  Porcentaje = 10%                                                     ║
        ║  Tamaño = $100,000 × 0.10 = $10,000                                   ║
        ║                                                                       ║
        ║  VENTAJAS:                                                            ║
        ║  • Simple de implementar                                              ║
        ║  • Fácil de entender                                                  ║
        ║                                                                       ║
        ║  DESVENTAJAS:                                                         ║
        ║  • No considera la volatilidad del mercado                            ║
        ║  • No considera tu ventaja estadística                                ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  • capital: Tu capital total disponible                               ║
        ║  • risk_pct: Porcentaje a invertir (opcional, usa max_position_pct)   ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • Monto en $ para invertir en esta posición                          ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        pct = risk_pct or self.params.max_position_pct
        return capital * pct
    
    # =========================================================================
    # MÉTODO 2: Criterio de Kelly
    # =========================================================================
    
    def kelly_criterion(
        self, 
        win_rate: float, 
        avg_win: float, 
        avg_loss: float,
        capital: float
    ) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    MÉTODO: CRITERIO DE KELLY                          ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  El Criterio de Kelly es una fórmula matemática que calcula el        ║
        ║  tamaño ÓPTIMO de apuesta para maximizar el crecimiento del capital.  ║
        ║                                                                       ║
        ║  HISTORIA:                                                            ║
        ║  ──────────                                                           ║
        ║  Desarrollado por John Kelly en 1956 en los Bell Labs.                ║
        ║  Originalmente diseñado para optimizar señales telefónicas,           ║
        ║  pero se aplica perfectamente a apuestas y trading.                   ║
        ║                                                                       ║
        ║  ¿QUÉ HACE KELLY?                                                     ║
        ║  ──────────────────                                                   ║
        ║  Encuentra el punto óptimo entre:                                     ║
        ║  • Apostar muy poco (creces lento)                                    ║
        ║  • Apostar demasiado (riesgo de ruina)                                ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  f* = (b × p - q) / b                                                 ║
        ║                                                                       ║
        ║  Donde:                                                               ║
        ║  • f* = fracción óptima del capital a apostar                         ║
        ║  • b = ratio ganancia/pérdida (avg_win / avg_loss)                    ║
        ║  • p = probabilidad de ganar (win_rate)                               ║
        ║  • q = probabilidad de perder (1 - p)                                 ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Win rate = 55% (ganas 55 de cada 100 trades)                         ║
        ║  Avg win = $2 por cada $1 arriesgado                                  ║
        ║  Avg loss = $1                                                        ║
        ║                                                                       ║
        ║  b = 2/1 = 2                                                          ║
        ║  p = 0.55, q = 0.45                                                   ║
        ║  f* = (2 × 0.55 - 0.45) / 2 = 0.325 = 32.5%                          ║
        ║                                                                       ║
        ║  ⚠️ ADVERTENCIA: Kelly completo es MUY AGRESIVO                       ║
        ║  Por eso usamos "Kelly fraccionado" (típicamente 1/4 o 1/2)           ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  • win_rate: Tu tasa de acierto histórica (ej: 0.55 = 55%)            ║
        ║  • avg_win: Ganancia promedio cuando ganas                            ║
        ║  • avg_loss: Pérdida promedio cuando pierdes (valor positivo)         ║
        ║  • capital: Tu capital total                                          ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • Monto en $ para invertir según Kelly                               ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Validación de parámetros
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            # Si los parámetros no tienen sentido, usar método simple
            return self.fixed_percentage(capital)
        
        # Calcular el ratio ganancia/pérdida
        b = avg_win / avg_loss
        # Si ganas $2 por cada $1 que pierdes, b = 2
        
        # Probabilidades
        p = win_rate      # Probabilidad de ganar
        q = 1 - p         # Probabilidad de perder
        
        # FÓRMULA DE KELLY
        # f* = (bp - q) / b
        kelly_pct = (b * p - q) / b
        
        # Aplicar fracción de Kelly (más conservador)
        # Kelly completo puede recomendar 30%+, lo cual es muy agresivo
        # Usamos típicamente 1/4 Kelly (kelly_fraction = 0.25)
        fractional_kelly = kelly_pct * self.params.kelly_fraction
        
        # Limitar al máximo permitido
        # Nunca exceder el max_position_pct aunque Kelly diga más
        final_pct = max(0, min(fractional_kelly, self.params.max_position_pct))
        # max(0, ...) asegura que no sea negativo
        # min(..., max_position) asegura que no exceda el límite
        
        return capital * final_pct
    
    # =========================================================================
    # MÉTODO 3: Ajustado por Volatilidad (ATR)
    # =========================================================================
    
    def volatility_adjusted(
        self, 
        capital: float, 
        atr: float, 
        price: float,
        risk_per_trade: Optional[float] = None
    ) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║               MÉTODO: AJUSTADO POR VOLATILIDAD (ATR)                  ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Este método ajusta el tamaño de la posición según la volatilidad     ║
        ║  actual del activo, medida por el ATR (Average True Range).           ║
        ║                                                                       ║
        ║  CONCEPTO:                                                            ║
        ║  ──────────                                                           ║
        ║  • Activo muy volátil (ATR alto) → posición más pequeña               ║
        ║  • Activo poco volátil (ATR bajo) → posición más grande               ║
        ║                                                                       ║
        ║  ¿POR QUÉ AJUSTAR POR VOLATILIDAD?                                    ║
        ║  ─────────────────────────────────────                                ║
        ║  Imagina dos acciones donde quieres arriesgar $1,000:                 ║
        ║                                                                       ║
        ║  ACCIÓN A (poco volátil, ATR = $1 diario):                            ║
        ║  • Puedes comprar muchas acciones                                     ║
        ║  • Es poco probable que pierda $1 de golpe                            ║
        ║                                                                       ║
        ║  ACCIÓN B (muy volátil, ATR = $5 diario):                             ║
        ║  • Debes comprar menos acciones                                       ║
        ║  • Fácilmente puede moverse $5 y superar tu stop loss                 ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Unidades = Riesgo en $ / ATR                                         ║
        ║                                                                       ║
        ║  Esta fórmula asegura que si el precio se mueve 1 ATR en tu contra,   ║
        ║  tu pérdida sea exactamente el "riesgo por trade".                    ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Capital = $100,000                                                   ║
        ║  Risk per trade = 2% = $2,000                                         ║
        ║  ATR de AAPL = $3                                                     ║
        ║  Precio de AAPL = $150                                                ║
        ║                                                                       ║
        ║  Unidades = $2,000 / $3 = 666 acciones                                ║
        ║  Valor total = 666 × $150 = $99,900 (dentro del límite)               ║
        ║                                                                       ║
        ║  Si AAPL cae $3 (1 ATR), perderías: 666 × $3 = $2,000 (exacto!)       ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  • capital: Tu capital total                                          ║
        ║  • atr: Average True Range del activo                                 ║
        ║  • price: Precio actual del activo                                    ║
        ║  • risk_per_trade: % del capital a arriesgar por trade                ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • Número de unidades/acciones a comprar                              ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Calcular cuánto dinero estamos dispuestos a perder en este trade
        risk_amount = capital * (risk_per_trade or self.params.max_portfolio_risk)
        
        # Protección contra ATR = 0 (evitar división por cero)
        if atr == 0:
            return 0
        
        # Calcular número de unidades
        # Si el precio se mueve 1 ATR, perderíamos risk_amount
        units = risk_amount / atr
        
        # Calcular el valor total de la posición
        position_value = units * price
        
        # Verificar que no excedamos el máximo permitido
        max_position = capital * self.params.max_position_pct
        
        if position_value > max_position:
            # Si excede, recalcular unidades basado en el máximo
            units = max_position / price
        
        return units


# =============================================================================
# CLASE: PortfolioRiskManager (Gestor de Riesgo del Portfolio)
# =============================================================================

class PortfolioRiskManager:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                   GESTOR DE RIESGO DEL PORTFOLIO                          ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Gestiona el riesgo a nivel de TODO EL PORTFOLIO, no solo un trade.       ║
    ║                                                                           ║
    ║  ¿POR QUÉ NECESITAMOS ESTO?                                               ║
    ║  ───────────────────────────                                              ║
    ║  Un trader puede tener múltiples posiciones abiertas simultáneamente.     ║
    ║  Esta clase se asegura de que el RIESGO TOTAL esté controlado.            ║
    ║                                                                           ║
    ║  FUNCIONES PRINCIPALES:                                                   ║
    ║  ───────────────────────                                                  ║
    ║  1. VERIFICAR si podemos abrir una nueva posición                         ║
    ║  2. RASTREAR el P&L diario y semanal                                      ║
    ║  3. PARAR de operar si llegamos a límites de pérdida                      ║
    ║                                                                           ║
    ║  LÍMITES QUE VERIFICA:                                                    ║
    ║  ───────────────────────                                                  ║
    ║  • Tamaño máximo de posición individual                                   ║
    ║  • Pérdida máxima diaria (3% → PARA por hoy)                              ║
    ║  • Pérdida máxima semanal (6% → PARA por la semana)                       ║
    ║  • Exposición total del portfolio (máx 80% invertido)                     ║
    ║                                                                           ║
    ║  EJEMPLO:                                                                 ║
    ║  ──────────                                                               ║
    ║  Capital = $100,000                                                       ║
    ║  Ya invertido = $60,000 (60%)                                             ║
    ║  Pérdida hoy = -$2,500 (2.5%)                                             ║
    ║                                                                           ║
    ║  Nueva posición de $25,000?                                               ║
    ║  → Check 1: $25K < $10K límite? ❌ RECHAZADA (muy grande)                 ║
    ║                                                                           ║
    ║  Nueva posición de $8,000?                                                ║
    ║  → Check 1: $8K < $10K? ✅                                                ║
    ║  → Check 2: -2.5% < -3%? ✅ (no hemos llegado al límite diario)           ║
    ║  → Check 3: 60K + 8K = 68K < 80K (80%)? ✅                                 ║
    ║  → APROBADA                                                               ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, params: Optional[RiskParameters] = None):
        """
        Inicializa el gestor de riesgo del portfolio.
        
        Mantiene registro de:
        - P&L diario y semanal
        - Posiciones abiertas actuales
        """
        self.params = params or RiskParameters()
        
        # Rastreo de P&L (Profit & Loss = Ganancias y Pérdidas)
        self.daily_pnl: float = 0.0     # Acumulado del día
        self.weekly_pnl: float = 0.0    # Acumulado de la semana
        
        # Registro de posiciones abiertas
        # Diccionario: símbolo → valor de la posición
        self.open_positions: Dict[str, float] = {}
    
    def can_open_position(self, capital: float, position_value: float) -> bool:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      ¿PODEMOS ABRIR ESTA POSICIÓN?                    ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Verifica si una nueva posición cumple con TODOS los límites.         ║
        ║                                                                       ║
        ║  CHECKS QUE REALIZA:                                                  ║
        ║  ─────────────────────                                                ║
        ║  1. ¿La posición individual es muy grande? (>10% del capital)         ║
        ║  2. ¿Ya perdimos demasiado hoy? (>3% del capital)                     ║
        ║  3. ¿Ya perdimos demasiado esta semana? (>6% del capital)             ║
        ║  4. ¿Tenemos demasiado invertido ya? (>80% del capital)               ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • True: Puedes abrir la posición                                     ║
        ║  • False: NO puedes abrir (describe por qué en los logs)              ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # CHECK 1: Límite de posición individual
        # ─────────────────────────────────────────
        if position_value > capital * self.params.max_position_pct:
            # La posición es más grande que el 10% del capital
            return False
        
        # CHECK 2: Límite de pérdida diaria
        # ─────────────────────────────────────────
        if self.daily_pnl < -capital * self.params.max_daily_loss:
            # Ya perdimos más del 3% hoy → PARAR
            return False
        
        # CHECK 3: Límite de pérdida semanal
        # ─────────────────────────────────────────
        if self.weekly_pnl < -capital * self.params.max_weekly_loss:
            # Ya perdimos más del 6% esta semana → PARAR
            return False
        
        # CHECK 4: Exposición total del portfolio
        # ─────────────────────────────────────────
        total_exposure = sum(self.open_positions.values()) + position_value
        max_exposure = capital * 0.80  # Máximo 80% invertido
        
        if total_exposure > max_exposure:
            # Ya tenemos demasiado dinero en el mercado
            return False
        
        # Todos los checks pasaron
        return True
    
    def record_trade(self, pnl: float) -> None:
        """
        Registra el P&L de un trade cerrado.
        
        PARÁMETROS:
        • pnl: Ganancia o pérdida del trade (positivo o negativo)
        """
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
    
    def reset_daily(self) -> None:
        """
        Reset del P&L diario.
        Llamar al inicio de cada día de trading.
        """
        self.daily_pnl = 0.0
    
    def reset_weekly(self) -> None:
        """
        Reset del P&L semanal.
        Llamar al inicio de cada semana de trading.
        """
        self.weekly_pnl = 0.0
        self.daily_pnl = 0.0  # También reseteamos el diario
    
    def add_position(self, symbol: str, value: float) -> None:
        """Registra una nueva posición abierta."""
        self.open_positions[symbol] = value
    
    def remove_position(self, symbol: str) -> None:
        """Elimina una posición cerrada del registro."""
        self.open_positions.pop(symbol, None)
        # .pop(key, None) elimina la clave si existe, no hace nada si no existe
    
    def get_portfolio_exposure(self) -> float:
        """Retorna la exposición total del portfolio (suma de todas las posiciones)."""
        return sum(self.open_positions.values())


# =============================================================================
# CLASE: RiskMetrics (Métricas de Riesgo y Rendimiento)
# =============================================================================

class RiskMetrics:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    MÉTRICAS DE RIESGO Y RENDIMIENTO                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase calcula las métricas que usamos para evaluar el rendimiento   ║
    ║  de una estrategia de trading.                                            ║
    ║                                                                           ║
    ║  ¿POR QUÉ NO BASTA CON VER LAS GANANCIAS?                                 ║
    ║  ─────────────────────────────────────────                                ║
    ║  Una estrategia que gana 50% pero tiene 80% de drawdown es TERRIBLE.      ║
    ║  Una estrategia que gana 20% con 5% de drawdown es EXCELENTE.             ║
    ║                                                                           ║
    ║  Necesitamos métricas que consideren TANTO el retorno COMO el riesgo.     ║
    ║                                                                           ║
    ║  MÉTRICAS DISPONIBLES:                                                    ║
    ║  ─────────────────────                                                    ║
    ║                                                                           ║
    ║  │ Métrica       │ ¿Qué mide?                               │ Bueno?  │   ║
    ║  ├───────────────┼──────────────────────────────────────────┼─────────┤   ║
    ║  │ Sharpe Ratio  │ Retorno / Riesgo (volatilidad)           │ > 1.5   │   ║
    ║  │ Sortino Ratio │ Retorno / Riesgo negativo                │ > 2.0   │   ║
    ║  │ Max Drawdown  │ Mayor caída desde un máximo              │ < -15%  │   ║
    ║  │ Calmar Ratio  │ Retorno / Max Drawdown                   │ > 1.0   │   ║
    ║  │ Win Rate      │ % de trades ganadores                    │ > 50%   │   ║
    ║  │ Profit Factor │ Ganancias brutas / Pérdidas brutas       │ > 1.5   │   ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                          SHARPE RATIO                                 ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  El Sharpe Ratio es LA métrica más importante en finanzas.            ║
        ║  Fue creada por William Sharpe (Nobel de Economía 1990).              ║
        ║                                                                       ║
        ║  ¿QUÉ MIDE?                                                           ║
        ║  ──────────                                                           ║
        ║  Cuánto rendimiento EXTRA obtienes por cada unidad de riesgo.         ║
        ║                                                                       ║
        ║  "Rendimiento extra" = tu rendimiento - lo que ganarías sin riesgo    ║
        ║  "Riesgo" = volatilidad (qué tanto fluctúan tus retornos)             ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Sharpe = (Rendimiento - Tasa libre de riesgo) / Volatilidad          ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • Sharpe < 0: Pierdes dinero vs. bonos del gobierno. ¡MAL!           ║
        ║  • Sharpe 0-1: Rendimiento positivo pero mediocre                     ║
        ║  • Sharpe 1-2: Buen rendimiento ajustado al riesgo                    ║
        ║  • Sharpe > 2: Excelente (los hedge funds buscan esto)                ║
        ║  • Sharpe > 3: Sospechoso (¿hay trampa o suerte?)                     ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Tu estrategia retorna 15% anual con 10% de volatilidad               ║
        ║  Bonos del gobierno dan 2% (risk free rate)                           ║
        ║  Sharpe = (15% - 2%) / 10% = 1.3 → Buen rendimiento                   ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  • returns: Serie de retornos diarios (ej: [0.01, -0.02, 0.015, ...]) ║
        ║  • risk_free_rate: Tasa libre de riesgo anualizada (2% por defecto)   ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Si no hay volatilidad, no podemos calcular (evitar división por cero)
        if returns.std() == 0:
            return 0.0
        
        # Convertir tasa anual a tasa diaria
        # 252 = días de trading en un año
        daily_rf = risk_free_rate / 252
        
        # Calcular exceso de retorno (rendimiento - tasa libre)
        excess_returns = returns.mean() - daily_rf
        
        # Anualizar el Sharpe Ratio
        # Multiplicamos por sqrt(252) para anualizar
        return (excess_returns / returns.std()) * np.sqrt(252)
    
    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                          SORTINO RATIO                                ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Similar al Sharpe, pero solo penaliza la VOLATILIDAD NEGATIVA.       ║
        ║                                                                       ║
        ║  ¿POR QUÉ ES ÚTIL?                                                    ║
        ║  ──────────────────                                                   ║
        ║  El Sharpe penaliza TODA la volatilidad, incluso la positiva.         ║
        ║  Pero a nosotros solo nos preocupa cuando PERDEMOS, no cuando GANAMOS.║
        ║                                                                       ║
        ║  El Sortino solo mide el riesgo de pérdida (downside risk).           ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Sortino = (Rendimiento - RF) / Volatilidad de retornos negativos     ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  Generalmente más alto que Sharpe si tu estrategia tiene              ║
        ║  más días positivos que negativos.                                    ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Filtrar solo los retornos negativos
        downside_returns = returns[returns < 0]
        
        # Si no hay retornos negativos, no podemos calcular
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        # Exceso de retorno
        excess_returns = returns.mean() - (risk_free_rate / 252)
        
        # Anualizar usando solo la volatilidad de las pérdidas
        return (excess_returns / downside_returns.std()) * np.sqrt(252)
    
    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                        MAXIMUM DRAWDOWN                               ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  El Drawdown máximo mide la PEOR CAÍDA desde un punto alto.           ║
        ║                                                                       ║
        ║  ¿QUÉ ES UN DRAWDOWN?                                                 ║
        ║  ─────────────────────                                                ║
        ║  Es la pérdida desde un máximo histórico hasta un mínimo posterior.   ║
        ║                                                                       ║
        ║  GRÁFICO DE DRAWDOWN:                                                 ║
        ║  ──────────────────────                                               ║
        ║                                                                       ║
        ║     $120K ──────────────►┐ Máximo histórico                           ║
        ║                          │                                            ║
        ║                          │ ─────────────────────                      ║
        ║                          │         │                                  ║
        ║                          ▼         │ Drawdown = -25%                  ║
        ║     $90K ────────────────┼─────────│                                  ║
        ║                          │ Mínimo  │                                  ║
        ║                          └─────────▼                                  ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • Max DD > -10%: Excelente                                           ║
        ║  • Max DD -10% a -20%: Bueno                                          ║
        ║  • Max DD -20% a -30%: Aceptable pero estresante                      ║
        ║  • Max DD < -30%: Peligroso (muchos abandonan)                        ║
        ║  • Max DD < -50%: La mayoría de traders no se recuperan               ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  • Drawdown como número negativo (ej: -0.25 = -25%)                   ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Calcular el máximo acumulado hasta cada punto
        rolling_max = equity_curve.expanding().max()
        # .expanding() crea una ventana que se expande desde el inicio
        # .max() encuentra el máximo de toda la ventana
        
        # Calcular drawdown en cada punto
        # DD = (valor actual - máximo) / máximo
        drawdowns = (equity_curve - rolling_max) / rolling_max
        
        # Retornar el drawdown mínimo (más negativo = peor)
        return drawdowns.min()
    
    @staticmethod
    def calmar_ratio(returns: pd.Series, equity_curve: pd.Series) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                          CALMAR RATIO                                 ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  El Calmar Ratio mide el retorno relativo al peor escenario.          ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Calmar = Retorno Anualizado / |Max Drawdown|                         ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  Responde: "Por cada 1% de drawdown, ¿cuánto retorno obtengo?"        ║
        ║                                                                       ║
        ║  • Calmar > 1.0: Buen balance retorno/riesgo                          ║
        ║  • Calmar > 2.0: Excelente                                            ║
        ║  • Calmar < 0.5: Riesgo alto para el retorno obtenido                 ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Retorno anualizado
        annual_return = returns.mean() * 252
        
        # Max drawdown (en valor absoluto)
        mdd = abs(RiskMetrics.max_drawdown(equity_curve))
        
        # Evitar división por cero
        if mdd == 0:
            return 0.0
        
        return annual_return / mdd
    
    @staticmethod
    def win_rate(trades: List[float]) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                            WIN RATE                                   ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Porcentaje de trades que terminaron en ganancia.                     ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Win Rate = Trades Ganadores / Total de Trades                        ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  100 trades totales, 55 fueron ganadores                              ║
        ║  Win Rate = 55 / 100 = 55%                                            ║
        ║                                                                       ║
        ║  NOTA IMPORTANTE:                                                     ║
        ║  ─────────────────                                                    ║
        ║  Win Rate alto NO significa estrategia rentable.                      ║
        ║  Puedes ganar 80% de trades pero perder dinero si                     ║
        ║  las pérdidas son mucho mayores que las ganancias.                    ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        if not trades:
            return 0.0
        
        # Contar trades ganadores (P&L > 0)
        winning = sum(1 for t in trades if t > 0)
        
        return winning / len(trades)
    
    @staticmethod
    def profit_factor(trades: List[float]) -> float:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                        PROFIT FACTOR                                  ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Ratio entre ganancias brutas y pérdidas brutas.                      ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  Profit Factor = Suma de Ganancias / Suma de Pérdidas                 ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Trades: [+$500, -$200, +$300, -$150, +$400]                          ║
        ║  Ganancias: $500 + $300 + $400 = $1,200                               ║
        ║  Pérdidas: $200 + $150 = $350                                         ║
        ║  PF = $1,200 / $350 = 3.43                                            ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • PF < 1.0: Pierdes más de lo que ganas → NO RENTABLE                ║
        ║  • PF 1.0-1.5: Marginalmente rentable                                 ║
        ║  • PF 1.5-2.0: Rentable                                               ║
        ║  • PF > 2.0: Muy rentable                                             ║
        ║  • PF > 3.0: Excelente                                                ║
        ║                                                                       ║
        ║  Un PF = 1.5 significa que por cada $1 que pierdes, ganas $1.50       ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Suma de todas las ganancias
        gross_profit = sum(t for t in trades if t > 0)
        
        # Suma de todas las pérdidas (en valor absoluto)
        gross_loss = abs(sum(t for t in trades if t < 0))
        
        # Manejar caso de no pérdidas
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
            # Si solo hubo ganancias, PF = infinito
        
        return gross_profit / gross_loss


# =============================================================================
# EJEMPLO DE USO COMPLETO
# =============================================================================
#
# from src.strategies.risk import PositionSizer, PortfolioRiskManager, RiskMetrics
#
# # 1. CONFIGURAR POSITION SIZER
# sizer = PositionSizer.load_from_config("config/settings.yaml")
#
# # 2. CALCULAR TAMAÑO DE POSICIÓN
# capital = 100000
# 
# # Método 1: Porcentaje fijo (10% del capital)
# size_fixed = sizer.fixed_percentage(capital)
# print(f"Porcentaje fijo: ${size_fixed:,.0f}")  # $10,000
#
# # Método 2: Kelly Criterion (basado en tu historial)
# size_kelly = sizer.kelly_criterion(
#     win_rate=0.55,    # 55% de acierto
#     avg_win=200,      # Ganas $200 en promedio
#     avg_loss=100,     # Pierdes $100 en promedio
#     capital=capital
# )
# print(f"Kelly: ${size_kelly:,.0f}")
#
# # 3. VERIFICAR SI PODEMOS OPERAR
# portfolio_mgr = PortfolioRiskManager()
# can_trade = portfolio_mgr.can_open_position(capital, size_kelly)
# print(f"¿Podemos operar? {can_trade}")
#
# # 4. CALCULAR MÉTRICAS DE RENDIMIENTO
# trades = [+500, -200, +300, -150, +400, -100, +250]
# print(f"Win Rate: {RiskMetrics.win_rate(trades):.1%}")         # 57.1%
# print(f"Profit Factor: {RiskMetrics.profit_factor(trades):.2f}")  # 3.22
#
# =============================================================================
