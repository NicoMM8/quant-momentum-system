# =============================================================================
# TRADE_MANAGER.PY - GESTOR DEL CICLO DE VIDA DE UN TRADE
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo gestiona el "CICLO DE VIDA" de un trade individual:
# - ENTRADA: ¿Cuándo entrar al mercado?
# - GESTIÓN: ¿Qué hacer mientras estamos dentro?
# - SALIDA: ¿Cuándo cerrar la posición?
#
# Es como un "piloto automático" que ejecuta tu plan de trading.
# Una vez que defines las reglas, él las sigue sin emociones.
#
# ¿QUÉ ES UN TRADE?
# -----------------
# Un trade es una operación de compra-venta en el mercado:
# 1. COMPRAR (entrada) esperando que suba
# 2. ESPERAR mientras el precio se mueve
# 3. VENDER (salida) cuando alcances tu objetivo o pérdida máxima
#
# ¿QUÉ ES UNA MÁQUINA DE ESTADOS?
# --------------------------------
# Una máquina de estados (State Machine) es un patrón de programación
# donde el objeto solo puede estar en UNO de varios estados definidos.
#
# Estados del TradeManager:
# 
#    ┌──────────────────────────────────────────────────────────┐
#    │                                                          │
#    │   WAITING         OPEN            CLOSED                 │
#    │  ┌───────┐      ┌──────┐        ┌───────┐               │
#    │  │Buscando│─────►│Trade │───────►│Trade  │               │
#    │  │entrada │      │activo│        │cerrado│               │
#    │  └───────┘      └──────┘        └───────┘               │
#    │       │             │                                    │
#    │       │ Señal de    │ Stop Loss                          │
#    │       │ compra (OBI)│ Take Profit                        │
#    │                     │ Trailing Stop                      │
#    │                                                          │
#    └──────────────────────────────────────────────────────────┘
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

from dataclasses import dataclass
# @dataclass genera automáticamente __init__, __repr__, __eq__, etc.
# Ideal para clases que principalmente almacenan datos

from enum import Enum
# Enum permite crear tipos enumerados (estados finitos)
# Es más seguro que usar strings o números arbitrarios

from typing import Optional
# Optional[X] significa "puede ser X o None"

import pandas as pd
# Pandas para trabajar con Series de datos

from pandas import Timestamp
# Timestamp es el tipo de dato para fechas/horas en pandas

import yaml
# YAML para cargar configuración

import os
# os para verificar existencia de archivos

import logging
# logging para registro de eventos profesional


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
# __name__ = 'src.execution.trade_manager'
# Esto permite identificar de dónde vienen los mensajes


# =============================================================================
# ENUMERACIÓN: TradeState (Estados del Trade)
# =============================================================================

class TradeState(Enum):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                      ESTADOS DEL TRADE                                    ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Define los tres estados posibles de un trade.                            ║
    ║                                                                           ║
    ║  ¿QUÉ ES UN ENUM?                                                         ║
    ║  ──────────────────                                                       ║
    ║  Un Enum (Enumeración) es un tipo de dato que solo puede tener            ║
    ║  valores específicos predefinidos. Es como un "menú cerrado".             ║
    ║                                                                           ║
    ║  En vez de usar strings ("WAITING", "OPEN", "CLOSED") que                 ║
    ║  pueden tener errores de tipeo, usamos un Enum.                           ║
    ║                                                                           ║
    ║  ESTADOS:                                                                 ║
    ║  ──────────                                                               ║
    ║                                                                           ║
    ║  WAITING (0) = Esperando señal de entrada                                 ║
    ║  ─────────────────────────────────────────                                ║
    ║  El TradeManager está monitoreando el mercado, buscando                   ║
    ║  una oportunidad de entrada según las reglas definidas.                   ║
    ║                                                                           ║
    ║  OPEN (1) = Trade activo                                                  ║
    ║  ─────────────────────────                                                ║
    ║  Ya compramos y estamos "dentro" del mercado.                             ║
    ║  Esperando que el precio suba (Take Profit) o baje (Stop Loss).           ║
    ║                                                                           ║
    ║  CLOSED (2) = Trade cerrado                                               ║
    ║  ───────────────────────────                                              ║
    ║  El trade terminó. Ya vendimos (por TP, SL o manualmente).                ║
    ║  El resultado (ganancia/pérdida) ya está registrado.                      ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    WAITING = 0  # Buscando entrada
    OPEN = 1     # Posición activa
    CLOSED = 2   # Trade finalizado (TP/SL)


# =============================================================================
# DATACLASS: TradeRecord (Registro del Trade)
# =============================================================================

@dataclass
class TradeRecord:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                     REGISTRO DE UN TRADE                                  ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Almacena toda la información de un trade específico.                     ║
    ║  Es como la "ficha" o "ticket" del trade.                                 ║
    ║                                                                           ║
    ║  CAMPOS:                                                                  ║
    ║  ─────────                                                                ║
    ║                                                                           ║
    ║  INFORMACIÓN DE ENTRADA:                                                  ║
    ║  • symbol: El ticker del activo (ej: "AAPL", "MSFT")                      ║
    ║  • entry_price: Precio al que compramos                                   ║
    ║  • entry_time: Fecha/hora de la compra                                    ║
    ║                                                                           ║
    ║  INFORMACIÓN DE SALIDA (se llena al cerrar):                              ║
    ║  • exit_price: Precio al que vendimos                                     ║
    ║  • exit_time: Fecha/hora de la venta                                      ║
    ║  • pnl_pct: Porcentaje de ganancia/pérdida                                ║
    ║  • status: Razón del cierre (TP, SL, MANUAL)                              ║
    ║                                                                           ║
    ║  EJEMPLO DE TRADE COMPLETO:                                               ║
    ║  ─────────────────────────────                                            ║
    ║  TradeRecord(                                                             ║
    ║      symbol = "AAPL",                                                     ║
    ║      entry_price = 150.00,                                                ║
    ║      entry_time = "2024-01-15 09:30:00",                                  ║
    ║      exit_price = 152.25,                                                 ║
    ║      exit_time = "2024-01-15 10:45:00",                                   ║
    ║      pnl_pct = 0.015,  # +1.5%                                            ║
    ║      status = "TAKE_PROFIT"                                               ║
    ║  )                                                                        ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    symbol: str                              # Símbolo del activo
    entry_price: float                       # Precio de entrada
    entry_time: pd.Timestamp                 # Momento de entrada
    exit_price: float = 0.0                  # Precio de salida (se llena después)
    exit_time: Optional[pd.Timestamp] = None # Momento de salida
    pnl_pct: float = 0.0                     # Ganancia/pérdida en porcentaje
    status: str = "OPEN"                     # Razón de cierre: TP, SL, MANUAL


# =============================================================================
# CLASE: TradeManager (Gestor de Trades)
# =============================================================================

class TradeManager:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                   GESTOR DEL CICLO DE VIDA DE UN TRADE                    ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Gestiona TODO el proceso de un trade:                                    ║
    ║  • Detecta señales de entrada                                             ║
    ║  • Abre posiciones                                                        ║
    ║  • Monitorea el precio                                                    ║
    ║  • Ejecuta Stop Loss y Take Profit                                        ║
    ║  • Implementa Trailing Stop                                               ║
    ║                                                                           ║
    ║  ¿QUÉ ES UN STOP LOSS?                                                    ║
    ║  ──────────────────────                                                   ║
    ║  Es una orden de venta automática para LIMITAR PÉRDIDAS.                  ║
    ║  Si el precio baja mucho, vendemos automáticamente para no perder más.    ║
    ║                                                                           ║
    ║  EJEMPLO:                                                                 ║
    ║  Compramos AAPL a $100, ponemos Stop Loss a $99.50 (0.5% abajo)           ║
    ║  Si el precio cae a $99.50, vendemos automáticamente.                     ║
    ║  Pérdida máxima controlada: 0.5%                                          ║
    ║                                                                           ║
    ║  ¿QUÉ ES UN TAKE PROFIT?                                                  ║
    ║  ────────────────────────                                                 ║
    ║  Es una orden de venta automática para ASEGURAR GANANCIAS.                ║
    ║  Si el precio sube a nuestro objetivo, vendemos automáticamente.          ║
    ║                                                                           ║
    ║  EJEMPLO:                                                                 ║
    ║  Compramos AAPL a $100, ponemos Take Profit a $101.50 (1.5% arriba)       ║
    ║  Si el precio sube a $101.50, vendemos automáticamente.                   ║
    ║  Ganancia asegurada: 1.5%                                                 ║
    ║                                                                           ║
    ║  ¿QUÉ ES UN TRAILING STOP?                                                ║
    ║  ───────────────────────────                                              ║
    ║  Es un Stop Loss que se "mueve" hacia arriba cuando el precio sube.       ║
    ║  Permite capturar más ganancias mientras protege las ya obtenidas.        ║
    ║                                                                           ║
    ║  EJEMPLO DE TRAILING STOP:                                                ║
    ║  ───────────────────────────                                              ║
    ║                                                                           ║
    ║  Compramos a $100, SL inicial a $99.50                                    ║
    ║                                                                           ║
    ║    $103 ────────────────────────                                          ║
    ║    $102 ───────────────────╮     Precio sube                              ║
    ║    $101 ───────────────╮   │                                              ║
    ║    $100 ───╭───────────┤   │     ← Entrada                                ║
    ║  $99.50 ───┴───────────────┴──── ← SL inicial                             ║
    ║ $100.70 ───────────────────╯     ← Nuevo SL (sigue al precio)             ║
    ║ $101.70 ───────────────────────╯ ← SL final (asegura ganancia)            ║
    ║                                                                           ║
    ║  El SL "persigue" al precio, asegurando ganancias parciales.              ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, symbol: str, config_path: str = "config/settings.yaml"):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                             __INIT__                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Inicializa el TradeManager para un símbolo específico.                 │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  • symbol: El ticker del activo a operar (ej: "AAPL")                   │
        │  • config_path: Ruta al archivo de configuración YAML                   │
        │                                                                         │
        │  CONFIGURACIÓN CARGADA DESDE YAML:                                      │
        │  • stop_loss_pct: Porcentaje de pérdida máxima (0.5% por defecto)       │
        │  • take_profit_pct: Porcentaje de ganancia objetivo (1.5% por defecto)  │
        │  • trailing_trigger: Cuánto debe subir el precio para activar trailing  │
        │  • trailing_distance: Distancia del trailing stop al precio actual      │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # ─────────────────────────────────────────────────────────────────────
        # INICIALIZACIÓN BÁSICA
        # ─────────────────────────────────────────────────────────────────────
        
        self.symbol = symbol
        # El ticker del activo que vamos a operar
        
        self.state = TradeState.WAITING
        # Estado inicial: esperando señal de entrada
        
        self.position: Optional[TradeRecord] = None
        # El registro del trade actual (None si no hay trade abierto)
        
        # ─────────────────────────────────────────────────────────────────────
        # CARGAR CONFIGURACIÓN DESDE YAML
        # ─────────────────────────────────────────────────────────────────────
        
        risk_config = self._load_risk_config(config_path)
        
        # Parámetros de Stop Loss y Take Profit
        self.stop_loss_pct = risk_config.get('stop_loss_pct', 0.005)  # 0.5%
        self.take_profit_pct = risk_config.get('take_profit_pct', 0.015)  # 1.5%
        # Ratio Riesgo:Beneficio = 1:3 (arriesgamos 0.5% para ganar 1.5%)
        
        # Parámetros de Trailing Stop
        self.trailing_trigger = risk_config.get('trailing_trigger', 0.008)  # 0.8%
        # Cuánto debe subir el precio antes de activar el trailing
        
        self.trailing_distance = risk_config.get('trailing_distance', 0.003)  # 0.3%
        # A qué distancia del precio máximo ponemos el trailing stop
        
        # ─────────────────────────────────────────────────────────────────────
        # VARIABLES DE ESTADO PARA TRAILING STOP
        # ─────────────────────────────────────────────────────────────────────
        
        self.highest_price = 0.0
        # El precio más alto alcanzado desde la entrada (High Water Mark)
        
        self.dynamic_sl = 0.0
        # El Stop Loss dinámico (puede moverse hacia arriba con trailing)
        
        logger.debug(f"[{symbol}] TradeManager inicializado: SL={self.stop_loss_pct:.2%}, TP={self.take_profit_pct:.2%}")
    
    def _load_risk_config(self, config_path: str) -> dict:
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                       _LOAD_RISK_CONFIG                                 │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Carga la configuración de riesgo desde archivo YAML.                   │
        │                                                                         │
        │  Busca la sección 'risk' en el archivo de configuración:                │
        │                                                                         │
        │  risk:                                                                  │
        │    stop_loss_pct: 0.005                                                 │
        │    take_profit_pct: 0.015                                               │
        │    trailing_trigger: 0.008                                              │
        │    trailing_distance: 0.003                                             │
        │                                                                         │
        │  Si el archivo no existe o hay error, retorna diccionario vacío         │
        │  y el sistema usará los valores por defecto.                            │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('risk', {})
            except Exception as e:
                logger.warning(f"No se pudo cargar config: {e}. Usando defaults.")
        return {}

    # =========================================================================
    # MÉTODO PRINCIPAL: on_tick (Procesar cada tick de datos)
    # =========================================================================
    
    def on_tick(self, row: pd.Series):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                        ON_TICK (CADA VELA)                            ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Este método se llama CADA VEZ que hay nuevos datos de precio.        ║
        ║  Es el "corazón" del TradeManager que toma decisiones.                ║
        ║                                                                       ║
        ║  ¿QUÉ ES UN TICK?                                                     ║
        ║  ──────────────────                                                   ║
        ║  Un "tick" es cada actualización de precio. Puede ser:                ║
        ║  • Cada segundo (trading de alta frecuencia)                          ║
        ║  • Cada minuto (lo que usamos aquí - velas M1)                        ║
        ║  • Cada hora, día, etc.                                               ║
        ║                                                                       ║
        ║  DATOS QUE RECIBE:                                                    ║
        ║  ──────────────────                                                   ║
        ║  row = una fila de datos con:                                         ║
        ║  • 'close': Precio de cierre de la vela                               ║
        ║  • 'datetime': Fecha/hora de la vela                                  ║
        ║  • 'obi': Order Book Imbalance (señal de microestructura)             ║
        ║                                                                       ║
        ║  LÓGICA DE DECISIÓN:                                                  ║
        ║  ─────────────────────                                                ║
        ║                                                                       ║
        ║  SI estado = WAITING:                                                 ║
        ║     → Buscar señal de entrada (OBI > 0.4)                             ║
        ║     → Si hay señal, COMPRAR                                           ║
        ║                                                                       ║
        ║  SI estado = OPEN:                                                    ║
        ║     → Verificar Stop Loss                                             ║
        ║     → Verificar Take Profit                                           ║
        ║     → Actualizar Trailing Stop                                        ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Extraer datos de la fila
        current_price = row['close']   # Precio actual
        current_time = row['datetime'] # Hora actual
        obi = row['obi']               # Order Book Imbalance

        # ─────────────────────────────────────────────────────────────────────
        # COMPORTAMIENTO SEGÚN EL ESTADO ACTUAL
        # ─────────────────────────────────────────────────────────────────────
        
        if self.state == TradeState.WAITING:
            # ═══════════════════════════════════════════════════════════════
            # ESTADO: WAITING (Buscando entrada)
            # ═══════════════════════════════════════════════════════════════
            # Estamos esperando una señal para entrar al mercado
            
            # LÓGICA DE ENTRADA: Micro-Estructura (Order Book Imbalance)
            # OBI > 0.4 significa que hay más presión compradora que vendedora
            # Es una señal de que el precio podría subir
            if obi > 0.4: 
                self._enter_market(current_price, current_time)

        elif self.state == TradeState.OPEN:
            # ═══════════════════════════════════════════════════════════════
            # ESTADO: OPEN (Trade activo)
            # ═══════════════════════════════════════════════════════════════
            # Tenemos una posición abierta, hay que gestionarla
            self._manage_position(current_price, current_time)

    # =========================================================================
    # MÉTODO PRIVADO: _enter_market (Entrar al mercado)
    # =========================================================================
    
    def _enter_market(self, price, time):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                         ENTRAR AL MERCADO                             ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Ejecuta una entrada LONG (compra esperando que suba).                ║
        ║                                                                       ║
        ║  PASOS:                                                               ║
        ║  ──────                                                               ║
        ║  1. Validar que el precio es válido (> 0)                             ║
        ║  2. Crear registro del trade (TradeRecord)                            ║
        ║  3. Cambiar estado a OPEN                                             ║
        ║  4. Configurar Stop Loss y Take Profit iniciales                      ║
        ║                                                                       ║
        ║  CONFIGURACIÓN DE STOPS:                                              ║
        ║  ─────────────────────────                                            ║
        ║  Precio de entrada: $100.00                                           ║
        ║  Stop Loss (0.5%): $100 × (1 - 0.005) = $99.50                        ║
        ║  Take Profit (1.5%): $100 × (1 + 0.015) = $101.50                     ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # VALIDACIÓN: El precio debe ser positivo
        if price <= 0:
            print(f"[{self.symbol}] ❌ Error: Precio de entrada inválido ({price}).")
            return
        
        # NOTIFICAR ENTRADA
        print(f"[{self.symbol}] 🚀 ENTRY LONG @ {price:.2f} | OBI High | Time: {time.time()}")
        
        # CREAR REGISTRO DEL TRADE
        self.position = TradeRecord(
            symbol=self.symbol, 
            entry_price=price, 
            entry_time=time
        )
        
        # CAMBIAR ESTADO
        self.state = TradeState.OPEN
        
        # CONFIGURAR STOPS INICIALES
        # Stop Loss inicial: precio × (1 - stop_loss_pct)
        self.dynamic_sl = price * (1 - self.stop_loss_pct)
        
        # Inicializar el precio más alto = precio de entrada
        self.highest_price = price

    # =========================================================================
    # MÉTODO PRIVADO: _manage_position (Gestionar posición abierta)
    # =========================================================================
    
    def _manage_position(self, current_price, time):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      GESTIONAR POSICIÓN ABIERTA                       ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Monitorea constantemente la posición y decide si cerrar.             ║
        ║                                                                       ║
        ║  TAREAS:                                                              ║
        ║  ─────────                                                            ║
        ║  1. Actualizar High Water Mark (precio más alto)                      ║
        ║  2. Mover Trailing Stop si corresponde                                ║
        ║  3. Verificar Stop Loss                                               ║
        ║  4. Verificar Take Profit                                             ║
        ║                                                                       ║
        ║  ORDEN DE PRIORIDAD:                                                  ║
        ║  ─────────────────────                                                ║
        ║  1º Stop Loss (proteger capital)                                      ║
        ║  2º Take Profit (asegurar ganancia)                                   ║
        ║                                                                       ║
        ║  TRAILING STOP EN DETALLE:                                            ║
        ║  ───────────────────────────                                          ║
        ║                                                                       ║
        ║  Entrada: $100.00, Trigger: 0.8%, Distancia: 0.3%                     ║
        ║                                                                       ║
        ║  Precio sube a $101.00 (+1.0%)                                        ║
        ║  → 1.0% > 0.8% (trigger) → Trailing activado                          ║
        ║  → Nuevo SL = $101.00 × (1 - 0.003) = $100.70                         ║
        ║                                                                       ║
        ║  Precio sube a $102.00 (+2.0%)                                        ║
        ║  → Nuevo SL = $102.00 × (1 - 0.003) = $101.70                         ║
        ║                                                                       ║
        ║  Precio baja a $101.60                                                ║
        ║  → $101.60 < $101.70 (SL) → CERRAR POSICIÓN                           ║
        ║  → Ganancia: ($101.60 - $100) / $100 = +1.6%                          ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # ═══════════════════════════════════════════════════════════════════
        # PASO 1: ACTUALIZAR HIGH WATER MARK (Precio más alto)
        # ═══════════════════════════════════════════════════════════════════
        
        if current_price > self.highest_price:
            # Nuevo máximo alcanzado
            self.highest_price = current_price
            
            # ─────────────────────────────────────────────────────────────────
            # LÓGICA DE TRAILING STOP
            # ─────────────────────────────────────────────────────────────────
            # Solo activar trailing si tenemos una posición válida
            if self.position:
                # Calcular cuánto ha subido el precio desde la entrada
                profit_pct = (self.highest_price / self.position.entry_price) - 1
                
                # Si el beneficio supera el trigger, mover el Stop Loss
                if profit_pct > self.trailing_trigger:
                    # Nuevo SL = Precio máximo - distancia de trailing
                    new_sl = self.highest_price * (1 - self.trailing_distance)
                    
                    # Solo subir el SL, nunca bajarlo
                    if new_sl > self.dynamic_sl:
                        self.dynamic_sl = new_sl
                        # Descomentado para debug:
                        # print(f"  [{self.symbol}] ⛓️ Trailing SL subido a {self.dynamic_sl:.2f}")

        # ═══════════════════════════════════════════════════════════════════
        # PASO 2: VERIFICAR STOP LOSS
        # ═══════════════════════════════════════════════════════════════════
        
        if current_price <= self.dynamic_sl:
            # El precio cayó por debajo del Stop Loss → VENDER
            self._close_position(current_price, time, reason="STOP_LOSS")
            return  # Salir, el trade terminó

        # ═══════════════════════════════════════════════════════════════════
        # PASO 3: VERIFICAR TAKE PROFIT
        # ═══════════════════════════════════════════════════════════════════
        
        if self.position:
            # Calcular precio objetivo
            tp_price = self.position.entry_price * (1 + self.take_profit_pct)
            
            if current_price >= tp_price:
                # Alcanzamos el objetivo → VENDER con ganancia
                self._close_position(current_price, time, reason="TAKE_PROFIT")

    # =========================================================================
    # MÉTODO PRIVADO: _close_position (Cerrar posición)
    # =========================================================================
    
    def _close_position(self, price, time, reason):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                         CERRAR POSICIÓN                               ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Ejecuta la venta y registra el resultado del trade.                  ║
        ║                                                                       ║
        ║  PASOS:                                                               ║
        ║  ──────                                                               ║
        ║  1. Validar precio de salida                                          ║
        ║  2. Calcular P&L (Profit & Loss)                                      ║
        ║  3. Actualizar el registro del trade                                  ║
        ║  4. Cambiar estado a CLOSED                                           ║
        ║                                                                       ║
        ║  RAZONES DE CIERRE:                                                   ║
        ║  ─────────────────────                                                ║
        ║  • STOP_LOSS: Alcanzamos la pérdida máxima permitida                  ║
        ║  • TAKE_PROFIT: Alcanzamos el objetivo de ganancia                    ║
        ║  • MANUAL: Cierre manual por decisión del trader                      ║
        ║                                                                       ║
        ║  CÁLCULO DE P&L:                                                      ║
        ║  ─────────────────                                                    ║
        ║  P&L (%) = (Precio Salida - Precio Entrada) / Precio Entrada          ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  Entrada: $100, Salida: $102                                          ║
        ║  P&L = ($102 - $100) / $100 = 0.02 = +2%                              ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # ═══════════════════════════════════════════════════════════════════
        # VALIDACIONES DE SEGURIDAD
        # ═══════════════════════════════════════════════════════════════════
        
        # Validar precio de salida
        if price <= 0:
            print(f"[{self.symbol}] ❌ Error: Precio de salida inválido ({price}).")
            return
        
        # Validar que hay una posición con entrada válida
        if not self.position or self.position.entry_price <= 0:
            print(f"[{self.symbol}] ❌ Error: No se puede cerrar una posición sin entrada válida.")
            return

        # ═══════════════════════════════════════════════════════════════════
        # CALCULAR P&L (PROFIT & LOSS)
        # ═══════════════════════════════════════════════════════════════════
        
        try:
            # Fórmula: (precio salida - precio entrada) / precio entrada
            pnl = (price - self.position.entry_price) / self.position.entry_price
        except ZeroDivisionError:
            # Por si acaso, aunque ya validamos arriba
            print(f"[{self.symbol}] ❌ Error: División por cero al calcular P&L.")
            pnl = 0.0

        # ═══════════════════════════════════════════════════════════════════
        # ACTUALIZAR REGISTRO DEL TRADE
        # ═══════════════════════════════════════════════════════════════════
        
        self.position.exit_price = price
        self.position.exit_time = time
        self.position.pnl_pct = pnl

        # Validar la razón de cierre
        valid_reasons = {"STOP_LOSS", "TAKE_PROFIT", "MANUAL"}
        if reason not in valid_reasons:
            print(f"[{self.symbol}] ❌ Error: Razón de cierre inválida ({reason}).")
            reason = "UNKNOWN"
        
        self.position.status = reason
        
        # ═══════════════════════════════════════════════════════════════════
        # CAMBIAR ESTADO A CLOSED
        # ═══════════════════════════════════════════════════════════════════
        
        self.state = TradeState.CLOSED
        
        # Mostrar resultado
        icon = "✅" if pnl > 0 else "❌"
        print(f"[{self.symbol}] {icon} CLOSE ({reason}) @ {price:.2f} | PnL: {pnl*100:.2f}%")


# =============================================================================
# EJEMPLO DE USO
# =============================================================================
#
# from src.execution.trade_manager import TradeManager
# import pandas as pd
# 
# # Crear un TradeManager para AAPL
# tm = TradeManager("AAPL")
# 
# # Simular datos de mercado (velas de 1 minuto)
# tick_data = pd.DataFrame({
#     'datetime': pd.date_range('2024-01-15 09:30', periods=10, freq='1min'),
#     'close': [100, 100.2, 100.5, 100.8, 101.2, 101.5, 101.3, 101.6, 101.8, 102.0],
#     'obi': [0.2, 0.3, 0.45, 0.5, 0.4, 0.3, 0.2, 0.25, 0.3, 0.35]
# })
# 
# # Procesar cada tick
# for _, row in tick_data.iterrows():
#     tm.on_tick(row)
#     print(f"Estado: {tm.state}, Precio: {row['close']}, SL: {tm.dynamic_sl:.2f}")
# 
# # Ver resultado del trade
# if tm.position:
#     print(f"\nResultado: {tm.position.status}, P&L: {tm.position.pnl_pct:.2%}")
#
# =============================================================================