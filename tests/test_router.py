"""
Tests unitarios para el Order Router.
"""

import pytest
from unittest.mock import MagicMock
from src.core.events import SignalEvent
from src.execution.router import OrderRouter

class TestRouter:
    
    @pytest.fixture
    def router(self):
        oms = MagicMock()
        sizer = MagicMock()
        
        # Mocks
        oms.connector.get_tick.return_value = {'ask': 150.0, 'bid': 149.9}
        oms.connector.get_symbol_info.return_value = MagicMock(volume_step=1.0, volume_min=1.0)
        
        # Sizer logic: return notional value for position
        # e.g., $1000 per trade
        sizer.fixed_percentage.return_value = 1500.0
        
        return OrderRouter(oms, sizer)

    def test_on_signal_entry_long(self, router):
        """Prueba entrada LONG."""
        # Signal 0.8 (Strong Buy)
        signal = SignalEvent(
            type="SIGNAL",
            symbol="AAPL",
            signal_strength=0.8,
            strategy_id="Micro"
        )
        
        router.on_signal(signal)
        
        # Verify size calculation
        # Risk % = 0.8%
        # Target Value = 1500 * 0.8 = 1200
        # Volume = 1200 / 150 (ask) = 8 lotes
        
        router.oms.submit_order.assert_called_with(
            "AAPL", 
            "BUY", 
            8.0, 
            pytest.approx(147.75, abs=0.1), # SL 1.5% below 150
            pytest.approx(154.5, abs=0.1)   # TP 3% above 150
        )

    def test_on_signal_exit_long(self, router):
        """Prueba salida LONG por señal débil."""
        # Mock existing position
        pos = MagicMock()
        pos.ticket = 999
        pos.symbol = "MSFT"
        pos.type = 0 # BUY
        
        router.oms.active_positions = {999: pos}
        
        # Weak signal (0.1) -> Close
        signal = SignalEvent(
            type="SIGNAL",
            symbol="MSFT",
            signal_strength=0.1,
            strategy_id="Tech"
        )
        
        router.on_signal(signal)
        
        router.oms.close_position.assert_called_with(999)

    def test_on_signal_monitor_existing(self, router):
        """Prueba que ignora señal si ya existe y confirma."""
        pos = MagicMock()
        pos.ticket = 777
        pos.symbol = "GOOGL"
        pos.type = 0 # BUY
        
        router.oms.active_positions = {777: pos}
        
        # Confirming signal (0.9)
        signal = SignalEvent(type="SIGNAL", symbol="GOOGL", signal_strength=0.9, strategy_id="Tech")
        
        router.on_signal(signal)
        
        # Should do nothing (hold)
        router.oms.submit_order.assert_not_called()
        router.oms.close_position.assert_not_called()
