import pytest
from unittest.mock import MagicMock
from src.core.events import SignalEvent
from src.execution.router import OrderRouter

class TestRouter:

    @pytest.fixture
    def router(self):
        oms = MagicMock()
        sizer = MagicMock()

        oms.connector.get_tick.return_value = {'ask': 150.0, 'bid': 149.9}
        oms.connector.get_symbol_info.return_value = MagicMock(volume_step=1.0, volume_min=1.0)

        sizer.fixed_percentage.return_value = 1500.0

        return OrderRouter(oms, sizer)

    def test_on_signal_entry_long(self, router):
        signal = SignalEvent(
            type="SIGNAL",
            symbol="AAPL",
            signal_strength=0.8,
            strategy_id="Micro"
        )

        router.on_signal(signal)


        router.oms.submit_order.assert_called_with(
            "AAPL",
            "BUY",
            8.0,
            pytest.approx(147.75, abs=0.1),
            pytest.approx(154.5, abs=0.1)
        )

    def test_on_signal_exit_long(self, router):
        pos = MagicMock()
        pos.ticket = 999
        pos.symbol = "MSFT"
        pos.type = 0

        router.oms.active_positions = {999: pos}

        signal = SignalEvent(
            type="SIGNAL",
            symbol="MSFT",
            signal_strength=0.1,
            strategy_id="Tech"
        )

        router.on_signal(signal)

        router.oms.close_position.assert_called_with(999)

    def test_on_signal_monitor_existing(self, router):
        pos = MagicMock()
        pos.ticket = 777
        pos.symbol = "GOOGL"
        pos.type = 0

        router.oms.active_positions = {777: pos}

        signal = SignalEvent(type="SIGNAL", symbol="GOOGL", signal_strength=0.9, strategy_id="Tech")

        router.on_signal(signal)

        router.oms.submit_order.assert_not_called()
        router.oms.close_position.assert_not_called()
