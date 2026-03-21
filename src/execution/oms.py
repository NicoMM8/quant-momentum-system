import time
import threading
from typing import Dict, Optional, List
from datetime import datetime

from src.execution.mt5_connector import MT5Connector, OrderResult, PositionInfo
from src.strategies.risk import PortfolioRiskManager, RiskParameters
from src.utils.logger import get_logger, LogEmoji

logger = get_logger("oms")

class OrderManagementSystem:

    def __init__(self, connector: MT5Connector, risk_manager: PortfolioRiskManager):
        self.connector = connector
        self.risk_manager = risk_manager
        self.active_positions: Dict[int, PositionInfo] = {}
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

        self.trailing_enabled = True
        self.trailing_trigger_pct = 0.008
        self.trailing_dist_pct = 0.003

        self.running = False

    def start(self):
        if self.running:
            return

        logger.info(f"{LogEmoji.SYNC} Iniciando OMS...")

        self.sync_positions()

        self.running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"{LogEmoji.INFO} OMS activo y monitoreando")

    def stop(self):
        if not self.running:
            return

        logger.info(f"{LogEmoji.SYNC} Deteniendo OMS...")
        self.running = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info(f"{LogEmoji.INFO} OMS detenido")

    def sync_positions(self):
        if not self.connector.is_connected:
            return

        params = self.risk_manager.params
        mt5_positions = self.connector.get_positions()

        current_tickets = set()
        for pos in mt5_positions:
            self.active_positions[pos.ticket] = pos
            current_tickets.add(pos.ticket)

            position_value = pos.price_current * pos.volume

        to_remove = [t for t in self.active_positions if t not in current_tickets]
        for t in to_remove:
            del self.active_positions[t]

        logger.info(f"{LogEmoji.SYNC} Sincronizado: {len(self.active_positions)} posiciones activas")

    def submit_order(self, symbol: str, signal_type: str, volume: float,
                    sl_price: float = 0.0, tp_price: float = 0.0) -> bool:
        if not self.running:
            logger.warning(f"{LogEmoji.WARNING} OMS detenido. Rechazando orden {symbol}")
            return False

        tick = self.connector.get_tick(symbol)
        if not tick:
            logger.error(f"{LogEmoji.LOSS} No hay precio para {symbol}, abortando orden")
            return False

        price = tick['ask'] if signal_type == "BUY" else tick['bid']
        notional_value = price * volume

        if not self.risk_manager.can_open_position(100000.0, notional_value):
            account = self.connector.get_account_info()
            if not self.risk_manager.can_open_position(account.equity, notional_value):
                logger.warning(f"{LogEmoji.WARNING} RiskManager rechazó orden {symbol} (Exposición/DD excesivo)")
                return False

        result = self.connector.place_order(
            symbol=symbol,
            order_type=signal_type,
            volume=volume,
            sl=sl_price,
            tp=tp_price
        )

        if result.success:
            logger.info(f"{LogEmoji.PROFIT} Orden enviada: {result.ticket}")
            self.risk_manager.add_position(symbol, notional_value)
            return True
        else:
            logger.error(f"{LogEmoji.LOSS} Fallo de ejecución: {result.comment}")
            return False

    def close_position(self, ticket: int) -> bool:
        result = self.connector.close_position(ticket)
        if result.success:
            if ticket in self.active_positions:
                pos = self.active_positions.pop(ticket)
                self.risk_manager.remove_position(pos.symbol)
            return True
        return False

    def close_all_positions(self):
        logger.warning(f"{LogEmoji.WARNING} CERRANDO TODAS LAS POSICIONES")
        self.sync_positions()

        for ticket in list(self.active_positions.keys()):
            self.close_position(ticket)

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                self.sync_positions()

                self._apply_trailing_stops()

                time.sleep(5)

            except Exception as e:
                logger.error(f"{LogEmoji.ERROR} Error en monitor loop: {e}")
                time.sleep(10)

    def _apply_trailing_stops(self):
        if not self.trailing_enabled:
            return

        for ticket, pos in self.active_positions.items():
            if pos.type == 0:
                if pos.price_open <= 0: continue
                profit_pct = (pos.price_current - pos.price_open) / pos.price_open

                if profit_pct >= self.trailing_trigger_pct:
                    desired_sl_price = pos.price_current * (1 - self.trailing_dist_pct)

                    if desired_sl_price > pos.sl and desired_sl_price > pos.price_open:

                        logger.info(f"{LogEmoji.SYNC} Trailing Stop #{ticket}: SL {pos.sl:.2f} -> {desired_sl_price:.2f}")

                        success = self.connector.modify_position(
                            ticket=ticket,
                            sl=desired_sl_price,
                            tp=pos.tp
                        )
                        if success:
                            pos.sl = desired_sl_price
                            self.active_positions[ticket] = pos
