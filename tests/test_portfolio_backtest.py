import pytest
import pandas as pd
import numpy as np
import sqlite3
import tempfile
import os

from src.analysis.portfolio_backtest import (
    PortfolioMomentumBacktester,
    _load_sector_map,
    _SECTOR_MAP_FALLBACK,
)


@pytest.fixture
def temp_db_with_data():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)

    np.random.seed(42)
    dates = pd.date_range('2022-01-01', periods=500, freq='B')
    rows = []
    for symbol in ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'JPM', 'BAC', 'SPY']:
        base = 100 + np.cumsum(np.random.randn(500) * 0.5)
        for i, date in enumerate(dates):
            rows.append({
                'datetime': str(date),
                'symbol': symbol,
                'open': float(base[i]),
                'high': float(base[i] + abs(np.random.randn()) * 1.5),
                'low': float(base[i] - abs(np.random.randn()) * 1.5),
                'close': float(base[i] + np.random.randn() * 0.3),
                'volume': int(np.random.randint(500_000, 5_000_000))
            })

    df = pd.DataFrame(rows)
    df.to_sql('market_data', conn, if_exists='replace', index=False)
    conn.close()

    yield path
    import gc; gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def temp_db_with_assets():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)

    assets_df = pd.DataFrame([
        {'symbol': 'AAPL', 'sector': 'Technology'},
        {'symbol': 'JPM', 'sector': 'Financials'},
        {'symbol': 'XOM', 'sector': 'Energy'},
    ])
    assets_df.to_sql('assets', conn, if_exists='replace', index=False)
    conn.close()

    yield path
    import gc; gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def temp_db_empty():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    import gc; gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


class TestLoadSectorMap:

    def test_loads_from_db(self, temp_db_with_assets):
        sector_map = _load_sector_map(temp_db_with_assets)
        assert sector_map['AAPL'] == 'Technology'
        assert sector_map['JPM'] == 'Financials'
        assert sector_map['XOM'] == 'Energy'

    def test_fallback_when_no_table(self, temp_db_empty):
        sector_map = _load_sector_map(temp_db_empty)
        assert sector_map == _SECTOR_MAP_FALLBACK

    def test_fallback_when_invalid_path(self):
        sector_map = _load_sector_map('/nonexistent/path.db')
        assert sector_map == _SECTOR_MAP_FALLBACK

    def test_fallback_is_copy(self, temp_db_empty):
        sector_map = _load_sector_map(temp_db_empty)
        sector_map['NEW_TICKER'] = 'NewSector'
        assert 'NEW_TICKER' not in _SECTOR_MAP_FALLBACK


class TestPortfolioMomentumBacktester:

    def test_init(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT', 'GOOGL'],
            initial_capital=10000.0
        )
        assert bt.initial_capital == 10000.0
        assert bt.universe == ['AAPL', 'MSFT', 'GOOGL']
        assert bt.results is None
        assert bt.trade_count == 0
        assert bt.total_costs == 0

    def test_sector_map_loaded(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL'],
        )
        assert isinstance(bt.sector_map, dict)
        assert len(bt.sector_map) > 0

    def test_load_data_matrix(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT'],
        )
        prices, highs, lows = bt.load_data_matrix()
        assert isinstance(prices, pd.DataFrame)
        assert isinstance(highs, pd.DataFrame)
        assert isinstance(lows, pd.DataFrame)
        assert len(prices) > 0

    def test_calculate_atr(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT'],
        )
        prices, highs, lows = bt.load_data_matrix()
        atr = bt.calculate_atr(prices, highs, lows)
        valid = atr.dropna()
        assert (valid >= 0).all().all()

    def test_apply_sector_limit(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT'],
        )
        ranked = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'CRM']
        result = bt.apply_sector_limit(ranked, max_per_sector=2)

        from collections import Counter
        sector_counts = Counter(bt.sector_map.get(s, 'Other') for s in result)
        for count in sector_counts.values():
            assert count <= 2

    def test_backtest_runs(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'],
            initial_capital=10000.0
        )
        results = bt.run_backtest(
            top_n=3,
            lookback_months=3,
            max_per_sector=2,
        )
        assert results is not None
        assert isinstance(results, pd.DataFrame)
        assert len(results) > 0

    def test_backtest_equity_positive(self, temp_db_with_data):
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT', 'GOOGL'],
            initial_capital=10000.0
        )
        results = bt.run_backtest(top_n=2, lookback_months=3)
        if results is not None and 'equity' in results.columns:
            assert (results['equity'] >= 0).all()


class TestSQLInjectionFix:

    def test_no_fstring_in_plot_results(self):
        import inspect
        source = inspect.getsource(PortfolioMomentumBacktester.plot_results)
        assert "f\"SELECT" not in source
        assert "f'SELECT" not in source
        assert "symbol=?" in source or "params=" in source
