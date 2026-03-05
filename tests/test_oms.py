"""
Tests unitarios para el Order Management System (OMS).
"""

import pytest
from unittest.mock import MagicMock
from src.execution.oms import OrderManagementSystem
from src.execution.mt5_connector import OrderResult, PositionInfo

class TestOMS:
    
    @pytest.fixture
    def oms(self):
        # Mocks
        connector = MagicMock()
        risk_manager = MagicMock()
        
        # Default behavior needed for tests
        connector.get_tick.return_value = {'ask': 150.0, 'bid': 149.9}
        connector.place_order.return_value = OrderResult(success=True, ticket=1001)
        # Risk manager always approves
        risk_manager.can_open_position.return_value = True
        
        oms = OrderManagementSystem(connector, risk_manager)
        oms.running = True # Simulate started state
        return oms

    def test_submit_order_success(self, oms):
        """Prueba envío exitoso de orden."""
        success = oms.submit_order("AAPL", "BUY", 1.0)
        
        assert success is True
        oms.connector.place_order.assert_called_with(
            symbol="AAPL", 
            order_type="BUY", 
            volume=1.0, 
            sl=0.0, 
            tp=0.0
        )
        # Verify risk tracking
        oms.risk_manager.add_position.assert_called()

    def test_submit_order_risk_rejected(self, oms):
        """Prueba rechazo por riesgo."""
        # Risk reject
        oms.risk_manager.can_open_position.return_value = False
        
        success = oms.submit_order("TSLA", "SELL", 0.5)
        
        assert success is False
        oms.connector.place_order.assert_not_called()

    def test_trailing_stop_logic(self, oms):
        """Prueba la lógica de trailing stop."""
        oms.trailing_enabled = True
        oms.trailing_trigger_pct = 0.01  # 1% gain trigger
        oms.trailing_dist_pct = 0.005    # 0.5% distance
        
        # Mock active position in profit
        # Entry @ 100, Current @ 102 (+2% gain). SL @ 90.
        # Desired SL = 102 * (1 - 0.005) = 101.49
        pos = PositionInfo(
            ticket=555,
            symbol="NVDA",
            type=0, # BUY
            price_open=100.0,
            price_current=102.0,
            sl=90.0,
            tp=0.0
        )
        oms.active_positions[555] = pos
        oms.connector.modify_position.return_value = True
        
        # Run trailing logic manually
        oms._apply_trailing_stops()
        
        oms.connector.modify_position.assert_called_with(
            ticket=555,
            sl=101.49,
            tp=0.0
        )
        # Check local update
        assert oms.active_positions[555].sl == 101.49
