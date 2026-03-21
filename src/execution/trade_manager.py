from dataclasses import dataclass

from enum import Enum

from typing import Optional

import pandas as pd

from pandas import Timestamp

import yaml

import os

import logging


logger = logging.getLogger(__name__)


class TradeState(Enum):
    WAITING = 0
    OPEN = 1
    CLOSED = 2


@dataclass
class TradeRecord:
    symbol: str
    entry_price: float
    entry_time: pd.Timestamp
    exit_price: float = 0.0
    exit_time: Optional[pd.Timestamp] = None
    pnl_pct: float = 0.0
    status: str = "OPEN"


class TradeManager:

    def __init__(self, symbol: str, config_path: str = "config/settings.yaml"):

        self.symbol = symbol

        self.state = TradeState.WAITING

        self.position: Optional[TradeRecord] = None


        risk_config = self._load_risk_config(config_path)

        self.stop_loss_pct = risk_config.get('stop_loss_pct', 0.005)
        self.take_profit_pct = risk_config.get('take_profit_pct', 0.015)

        self.trailing_trigger = risk_config.get('trailing_trigger', 0.008)

        self.trailing_distance = risk_config.get('trailing_distance', 0.003)


        self.highest_price = 0.0

        self.dynamic_sl = 0.0

        logger.debug(f"[{symbol}] TradeManager inicializado: SL={self.stop_loss_pct:.2%}, TP={self.take_profit_pct:.2%}")

    def _load_risk_config(self, config_path: str) -> dict:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('risk', {})
            except Exception as e:
                logger.warning(f"No se pudo cargar config: {e}. Usando defaults.")
        return {}


    def on_tick(self, row: pd.Series):
        current_price = row['close']
        current_time = row['datetime']
        obi = row['obi']


        if self.state == TradeState.WAITING:

            if obi > 0.4:
                self._enter_market(current_price, current_time)

        elif self.state == TradeState.OPEN:
            self._manage_position(current_price, current_time)


    def _enter_market(self, price, time):
        if price <= 0:
            print(f"[{self.symbol}] ❌ Error: Precio de entrada inválido ({price}).")
            return

        print(f"[{self.symbol}] 🚀 ENTRY LONG @ {price:.2f} | OBI High | Time: {time.time()}")

        self.position = TradeRecord(
            symbol=self.symbol,
            entry_price=price,
            entry_time=time
        )

        self.state = TradeState.OPEN

        self.dynamic_sl = price * (1 - self.stop_loss_pct)

        self.highest_price = price


    def _manage_position(self, current_price, time):

        if current_price > self.highest_price:
            self.highest_price = current_price

            if self.position:
                profit_pct = (self.highest_price / self.position.entry_price) - 1

                if profit_pct > self.trailing_trigger:
                    new_sl = self.highest_price * (1 - self.trailing_distance)

                    if new_sl > self.dynamic_sl:
                        self.dynamic_sl = new_sl


        if current_price <= self.dynamic_sl:
            self._close_position(current_price, time, reason="STOP_LOSS")
            return


        if self.position:
            tp_price = self.position.entry_price * (1 + self.take_profit_pct)

            if current_price >= tp_price:
                self._close_position(current_price, time, reason="TAKE_PROFIT")


    def _close_position(self, price, time, reason):

        if price <= 0:
            print(f"[{self.symbol}] ❌ Error: Precio de salida inválido ({price}).")
            return

        if not self.position or self.position.entry_price <= 0:
            print(f"[{self.symbol}] ❌ Error: No se puede cerrar una posición sin entrada válida.")
            return


        try:
            pnl = (price - self.position.entry_price) / self.position.entry_price
        except ZeroDivisionError:
            print(f"[{self.symbol}] ❌ Error: División por cero al calcular P&L.")
            pnl = 0.0


        self.position.exit_price = price
        self.position.exit_time = time
        self.position.pnl_pct = pnl

        valid_reasons = {"STOP_LOSS", "TAKE_PROFIT", "MANUAL"}
        if reason not in valid_reasons:
            print(f"[{self.symbol}] ❌ Error: Razón de cierre inválida ({reason}).")
            reason = "UNKNOWN"

        self.position.status = reason


        self.state = TradeState.CLOSED

        icon = "✅" if pnl > 0 else "❌"
        print(f"[{self.symbol}] {icon} CLOSE ({reason}) @ {price:.2f} | PnL: {pnl*100:.2f}%")


