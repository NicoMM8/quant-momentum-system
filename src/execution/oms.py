"""
═══════════════════════════════════════════════════════════════════════════════
  ORDER MANAGEMENT SYSTEM (OMS)
  
  Coordinador central de ejecución:
  - Recibe solicitudes de orden (Buy/Sell)
  - Verifica riesgos (RiskManager)
  - Ejecuta en Broker (MT5Connector)
  - Gestiona ciclo de vida (Open -> Trailing -> Closed)
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import threading
from typing import Dict, Optional, List
from datetime import datetime

from src.execution.mt5_connector import MT5Connector, OrderResult, PositionInfo
from src.strategies.risk import PortfolioRiskManager, RiskParameters
from src.utils.logger import get_logger, LogEmoji

logger = get_logger("oms")

class OrderManagementSystem:
    """
    Sistema de Gestión de Órdenes.
    
    Orquestra la ejecución segura de operaciones:
    1. Valida riesgo (capital, drawdown, exposición)
    2. Enruta a MT5
    3. Mantiene estado local de posiciones
    4. Ejecuta bucle de mantenimiento (trailing stops)
    """
    
    def __init__(self, connector: MT5Connector, risk_manager: PortfolioRiskManager):
        self.connector = connector
        self.risk_manager = risk_manager
        self.active_positions: Dict[int, PositionInfo] = {}  # ticket -> info
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Configuración de trailing
        self.trailing_enabled = True
        self.trailing_trigger_pct = 0.008  # Activar si gana 0.8%
        self.trailing_dist_pct = 0.003     # Mantener a 0.3%
        
        # Estado
        self.running = False

    def start(self):
        """Inicia el bucle de monitoreo de posiciones."""
        if self.running:
            return
            
        logger.info(f"{LogEmoji.SYNC} Iniciando OMS...")
        
        # Sincronizar estado inicial con MT5
        self.sync_positions()
        
        self.running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"{LogEmoji.INFO} OMS activo y monitoreando")

    def stop(self):
        """Detiene el OMS."""
        if not self.running:
            return
            
        logger.info(f"{LogEmoji.SYNC} Deteniendo OMS...")
        self.running = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info(f"{LogEmoji.INFO} OMS detenido")

    def sync_positions(self):
        """Sincroniza posiciones locales con lo que hay en MT5."""
        if not self.connector.is_connected:
            return
            
        params = self.risk_manager.params  # type: ignore # Acceso a params del risk manager
        mt5_positions = self.connector.get_positions()
        
        # Actualizar diccionario local
        current_tickets = set()
        for pos in mt5_positions:
            self.active_positions[pos.ticket] = pos
            current_tickets.add(pos.ticket)
            
            # Registrar en RiskManager para tracking de exposición
            # Nota: RiskManager espera 'symbol' y 'value'.
            # MT5 da value = volumen * contract_size * price, pero simplificamos:
            # Asumimos value approx = margin user o equity exposure
            # Para stocks: price * volume
            position_value = pos.price_current * pos.volume
            # Hack: RiskManager trackea por símbolo, MT5 por ticket. 
            # Si hay múltiples posiciones del mismo símbolo, RiskManager debe saberlo.
            # Por ahora simplificamos: RiskManager solo valida "puedo abrir nueva?"
            
        # Limpiar cerradas
        to_remove = [t for t in self.active_positions if t not in current_tickets]
        for t in to_remove:
            del self.active_positions[t]
            
        logger.info(f"{LogEmoji.SYNC} Sincronizado: {len(self.active_positions)} posiciones activas")

    def submit_order(self, symbol: str, signal_type: str, volume: float, 
                    sl_price: float = 0.0, tp_price: float = 0.0) -> bool:
        """
        Punto de entrada para nuevas órdenes.
        
        Args:
            symbol: Ticker (AAPL)
            signal_type: "BUY" o "SELL"
            volume: Lotes
            sl_price: Precio Stop Loss
            tp_price: Precio Take Profit
        """
        if not self.running:
            logger.warning(f"{LogEmoji.WARNING} OMS detenido. Rechazando orden {symbol}")
            return False

        # 1. Validación de Riesgo
        # Estimar valor nocional: precio actual * volumen
        # Necesitamos precio actual.
        tick = self.connector.get_tick(symbol)
        if not tick:
            logger.error(f"{LogEmoji.LOSS} No hay precio para {symbol}, abortando orden")
            return False
            
        price = tick['ask'] if signal_type == "BUY" else tick['bid']
        notional_value = price * volume
        
        # Risk Check
        if not self.risk_manager.can_open_position(100000.0, notional_value): # TODO: Pasar capital real
             # Obtener capital real de MT5
            account = self.connector.get_account_info()
            if not self.risk_manager.can_open_position(account.equity, notional_value):
                logger.warning(f"{LogEmoji.WARNING} RiskManager rechazó orden {symbol} (Exposición/DD excesivo)")
                return False

        # 2. Ejecución
        result = self.connector.place_order(
            symbol=symbol,
            order_type=signal_type,
            volume=volume,
            sl=sl_price,
            tp=tp_price
        )
        
        if result.success:
            # 3. Registro inmediato (la sincronización completa vendrá en el loop)
            # Solo podemos registrar si tenemos ticket real. En paper mode ticket es dummy o real?
            # Connector devuelve ticket simulado en paper mode.
            logger.info(f"{LogEmoji.PROFIT} Orden enviada: {result.ticket}")
            # Risk manager add position
            self.risk_manager.add_position(symbol, notional_value)
            return True
        else:
            logger.error(f"{LogEmoji.LOSS} Fallo de ejecución: {result.comment}")
            return False

    def close_position(self, ticket: int) -> bool:
        """Cierra una posición específica."""
        result = self.connector.close_position(ticket)
        if result.success:
            # Update local state
            if ticket in self.active_positions:
                pos = self.active_positions.pop(ticket)
                self.risk_manager.remove_position(pos.symbol)
                # Registrar PnL en RiskManager
                # Necesitamos saber el profit final. MT5 devuelve deal price, no profit.
                # En trading real, el profit se calcula post-deal. 
                # Aquí estimamos o esperamos al próximo sync para ver historial (complejo).
                # Por ahora, simplemente liberamos el slot de posición.
            return True
        return False

    def close_all_positions(self):
        """Cierra TODAS las posiciones (Pánico / Cierre de día)."""
        logger.warning(f"{LogEmoji.WARNING} CERRANDO TODAS LAS POSICIONES")
        self.sync_positions() # Asegurar estado fresco
        
        for ticket in list(self.active_positions.keys()):
            self.close_position(ticket)

    def _monitor_loop(self):
        """Bucle en segundo plano: Sync estados + Trailing Stop."""
        while not self._stop_event.is_set():
            try:
                # 1. Sincronizar con broker
                self.sync_positions()
                
                # 2. Gestión de Trailing Stop
                self._apply_trailing_stops()
                
                # 3. Dormir
                time.sleep(5) # Check cada 5 seg
                
            except Exception as e:
                logger.error(f"{LogEmoji.ERROR} Error en monitor loop: {e}")
                time.sleep(10)

    def _apply_trailing_stops(self):
        """Aplica lógica de Trailing Stop a posiciones en beneficio."""
        if not self.trailing_enabled:
            return

        for ticket, pos in self.active_positions.items():
            # Solo para BUY por ahora (simplificación inicial)
            if pos.type == 0: # BUY
                # Calcular % ganancia
                if pos.price_open <= 0: continue
                profit_pct = (pos.price_current - pos.price_open) / pos.price_open
                
                # Si supera el trigger (ej. 0.8%)
                if profit_pct >= self.trailing_trigger_pct:
                    # Nuevo SL deseado: Current Price - Distancia
                    desired_sl_price = pos.price_current * (1 - self.trailing_dist_pct)
                    
                    # Solo subir el SL, nunca bajarlo
                    # Y debe ser mayor que el SL actual
                    if desired_sl_price > pos.sl and desired_sl_price > pos.price_open:
                        
                        logger.info(f"{LogEmoji.SYNC} Trailing Stop #{ticket}: SL {pos.sl:.2f} -> {desired_sl_price:.2f}")
                        
                        success = self.connector.modify_position(
                            ticket=ticket,
                            sl=desired_sl_price,
                            tp=pos.tp
                        )
                        if success:
                            # Actualizar localmente para no reintentar inmediatamente
                            pos.sl = desired_sl_price
                            self.active_positions[ticket] = pos
