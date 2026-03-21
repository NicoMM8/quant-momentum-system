import pytest
from unittest.mock import MagicMock, patch
from src.execution.mt5_connector import MT5Connector, AccountInfo, OrderResult

class TestMT5Connector:

    @pytest.fixture
    def mock_mt5(self):
        with patch('src.execution.mt5_connector.mt5') as mock:
            mock.start = MagicMock(return_value=True)
            mock.initialize = MagicMock(return_value=True)
            mock.login = MagicMock(return_value=True)
            mock.last_error = MagicMock(return_value=(0, "Success"))

            acc_info = MagicMock()
            acc_info.login = 12345
            acc_info.balance = 10000.0
            acc_info.equity = 10000.0
            acc_info.margin = 0.0
            acc_info.margin_free = 10000.0
            acc_info.margin_level = 0.0
            acc_info.profit = 0.0
            acc_info.currency = "USD"
            acc_info.server = "Demo"
            acc_info.company = "Admiral"
            mock.account_info.return_value = acc_info

            yield mock

    def test_connection_flow(self, mock_mt5):
        connector = MT5Connector()
        with patch.object(connector, '_load_config', return_value={}):
            success = connector.connect(login=123, password="abc", server="Demo")

        assert success is True
        assert connector.is_connected is True
        mock_mt5.initialize.assert_called()
        mock_mt5.login.assert_called()

        info = connector.get_account_info()
        assert info.balance == 10000.0
        assert info.currency == "USD"

        connector.disconnect()
        assert connector.is_connected is False
        mock_mt5.shutdown.assert_called()

    def test_paper_mode_order(self):
        with patch('src.execution.mt5_connector.MT5Connector._load_config',
                  return_value={'paper_mode': True}):
            connector = MT5Connector()
            assert connector.paper_mode is True

            res = connector.place_order("AAPL", "BUY", 1.0)

            assert res.success is True
            assert res.comment == "PAPER_ORDER"
            assert connector.is_connected is False

    def test_symbol_mapping(self):
        from src.execution.mt5_connector import map_symbol_to_mt5

        assert map_symbol_to_mt5("AAPL") == "AAPL.US"
        assert map_symbol_to_mt5("EURUSD") == "EURUSD"
        assert map_symbol_to_mt5("TSLA", suffix=".UK") == "TSLA.UK"
