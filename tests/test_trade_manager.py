import pytest
import pandas as pd
import numpy as np
from src.execution.trade_manager import TradeManager, TradeState, TradeRecord


class TestTradeManagerInit:

    def test_init_default_state(self):
        tm = TradeManager("AAPL")

        assert tm.state == TradeState.WAITING
        assert tm.position is None
        assert tm.symbol == "AAPL"

    def test_init_loads_defaults_without_config(self):
        tm = TradeManager("MSFT", config_path="nonexistent.yaml")

        assert tm.stop_loss_pct == 0.005
        assert tm.take_profit_pct == 0.015
        assert tm.trailing_trigger == 0.008


class TestTradeManagerEntry:

    def test_entry_on_high_obi(self):
        tm = TradeManager("AAPL")

        tick = pd.Series({
            'close': 150.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.5
        })

        tm.on_tick(tick)

        assert tm.state == TradeState.OPEN
        assert tm.position is not None
        assert tm.position.entry_price == 150.0

    def test_no_entry_on_low_obi(self):
        tm = TradeManager("AAPL")

        tick = pd.Series({
            'close': 150.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })

        tm.on_tick(tick)

        assert tm.state == TradeState.WAITING
        assert tm.position is None

    def test_rejects_invalid_price(self):
        tm = TradeManager("AAPL")

        tick = pd.Series({
            'close': 0.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.5
        })

        tm.on_tick(tick)

        assert tm.state == TradeState.WAITING


class TestTradeManagerStopLoss:

    def create_open_position(self, tm: TradeManager, entry_price: float = 100.0):
        tick = pd.Series({
            'close': entry_price,
            'datetime': pd.Timestamp.now(),
            'obi': 0.5
        })
        tm.on_tick(tick)
        return tm

    def test_stop_loss_triggers(self):
        tm = TradeManager("AAPL")
        tm = self.create_open_position(tm, entry_price=100.0)

        tick_sl = pd.Series({
            'close': 99.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })

        tm.on_tick(tick_sl)

        assert tm.state == TradeState.CLOSED
        assert tm.position.status == "STOP_LOSS"
        assert tm.position.pnl_pct < 0

    def test_no_stop_loss_above_threshold(self):
        tm = TradeManager("AAPL")
        tm = self.create_open_position(tm, entry_price=100.0)

        tick = pd.Series({
            'close': 99.8,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })

        tm.on_tick(tick)

        assert tm.state == TradeState.OPEN


class TestTradeManagerTakeProfit:

    def create_open_position(self, tm: TradeManager, entry_price: float = 100.0):
        tick = pd.Series({
            'close': entry_price,
            'datetime': pd.Timestamp.now(),
            'obi': 0.5
        })
        tm.on_tick(tick)
        return tm

    def test_take_profit_triggers(self):
        tm = TradeManager("AAPL")
        tm = self.create_open_position(tm, entry_price=100.0)

        tick_tp = pd.Series({
            'close': 102.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })

        tm.on_tick(tick_tp)

        assert tm.state == TradeState.CLOSED
        assert tm.position.status == "TAKE_PROFIT"
        assert tm.position.pnl_pct > 0


class TestTradeManagerTrailingStop:

    def create_open_position(self, tm: TradeManager, entry_price: float = 100.0):
        tick = pd.Series({
            'close': entry_price,
            'datetime': pd.Timestamp.now(),
            'obi': 0.5
        })
        tm.on_tick(tick)
        return tm

    def test_trailing_stop_moves_up(self):
        tm = TradeManager("AAPL")
        tm = self.create_open_position(tm, entry_price=100.0)

        initial_sl = tm.dynamic_sl

        tick_up = pd.Series({
            'close': 101.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })

        tm.on_tick(tick_up)

        assert tm.dynamic_sl > initial_sl
        assert tm.highest_price == 101.0
        assert tm.state == TradeState.OPEN

    def test_trailing_stop_locks_profit(self):
        tm = TradeManager("AAPL")
        tm = self.create_open_position(tm, entry_price=100.0)

        tick_up = pd.Series({
            'close': 102.0,
            'datetime': pd.Timestamp.now(),
            'obi': 0.3
        })
        tm.on_tick(tick_up)

        if tm.state == TradeState.CLOSED:
            assert tm.position.pnl_pct > 0


class TestTradeRecord:

    def test_trade_record_defaults(self):
        record = TradeRecord(
            symbol="AAPL",
            entry_price=100.0,
            entry_time=pd.Timestamp.now()
        )

        assert record.exit_price == 0.0
        assert record.exit_time is None
        assert record.pnl_pct == 0.0
        assert record.status == "OPEN"

    def test_trade_record_full(self):
        entry = pd.Timestamp("2024-01-01 10:00:00")
        exit = pd.Timestamp("2024-01-01 11:00:00")

        record = TradeRecord(
            symbol="MSFT",
            entry_price=300.0,
            entry_time=entry,
            exit_price=305.0,
            exit_time=exit,
            pnl_pct=0.0167,
            status="TAKE_PROFIT"
        )

        assert record.symbol == "MSFT"
        assert record.pnl_pct == pytest.approx(0.0167, rel=1e-3)
