from src.core.events import SignalEvent
from src.execution.oms import OrderManagementSystem
from src.strategies.risk import PositionSizer, RiskParameters
from src.utils.logger import get_logger, LogEmoji

logger = get_logger("router")

class OrderRouter:

    def __init__(self, oms: OrderManagementSystem, position_sizer: PositionSizer):
        self.oms = oms
        self.sizer = position_sizer
        self.min_signal_strength = 0.5

    def on_signal(self, signal: SignalEvent, current_capital: float = 10000.0):
        symbol = signal.symbol
        strength = signal.signal_strength

        logger.info(f"{LogEmoji.INFO} Procesando señal: {symbol} S={strength:.2f}")


        existing_ticket = None
        existing_pos = None

        for ticket, pos in self.oms.active_positions.items():
            if pos.symbol == symbol:
                existing_ticket = ticket
                existing_pos = pos
                break


        if existing_pos:
            if existing_pos.type == 0:
                if strength < 0.2:
                    logger.info(f"{LogEmoji.EXIT} Señal debilitada ({strength:.2f}). Cerrando LONG {symbol}")
                    self.oms.close_position(existing_ticket)
                    return

            elif existing_pos.type == 1:
                 if strength > -0.2:
                    logger.info(f"{LogEmoji.EXIT} Señal debilitada ({strength:.2f}). Cerrando SHORT {symbol}")
                    self.oms.close_position(existing_ticket)
                    return

            return

        if abs(strength) < self.min_signal_strength:
            return

        direction = "BUY" if strength > 0 else "SELL"

        tick = self.oms.connector.get_tick(symbol)
        if not tick:
            logger.warning(f"No tic price for {symbol}")
            return

        price = tick['ask'] if direction == "BUY" else tick['bid']

        risk_pct = 0.01 * abs(strength)

        sl_dist_pct = 0.015
        sl_price = price * (1 - sl_dist_pct) if direction == "BUY" else price * (1 + sl_dist_pct)
        tp_price = price * (1 + (sl_dist_pct * 2)) if direction == "BUY" else price * (1 - (sl_dist_pct * 2))


        target_pos_value = self.sizer.fixed_percentage(current_capital, risk_pct=None)
        target_pos_value = target_pos_value * abs(strength)


        if target_pos_value <= 0: return

        volume = target_pos_value / price

        sym_info = self.oms.connector.get_symbol_info(symbol)
        if sym_info:
            step = sym_info.volume_step
            if step > 0:
                volume = round(volume / step) * step
                if volume < sym_info.volume_min:
                    logger.info(f"Volumen calculado ({volume}) menor al mínimo ({sym_info.volume_min})")
                    return

        logger.info(f"{LogEmoji.ENTRY} Señal {direction} detectada. Ordenando {volume:.2f} lotes {symbol}")
        self.oms.submit_order(symbol, direction, volume, sl_price, tp_price)
