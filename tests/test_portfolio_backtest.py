# tests/test_portfolio_backtest.py
"""
Tests para el backtester de portafolio con momentum.
Ejecutar con: pytest tests/test_portfolio_backtest.py -v
"""
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


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_with_data():
    """Crea una BD temporal con suficientes datos para el backtester."""
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
    """Crea una BD temporal con tabla 'assets' para test de sector map."""
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
    """Crea una BD temporal vacía."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    import gc; gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


# =============================================================================
# TESTS: _load_sector_map
# =============================================================================

class TestLoadSectorMap:
    """Tests para la función _load_sector_map."""
    
    def test_loads_from_db(self, temp_db_with_assets):
        """Debe cargar sectores desde la tabla 'assets' cuando existe."""
        sector_map = _load_sector_map(temp_db_with_assets)
        assert sector_map['AAPL'] == 'Technology'
        assert sector_map['JPM'] == 'Financials'
        assert sector_map['XOM'] == 'Energy'
    
    def test_fallback_when_no_table(self, temp_db_empty):
        """Debe retornar el fallback cuando no existe tabla 'assets'."""
        sector_map = _load_sector_map(temp_db_empty)
        assert sector_map == _SECTOR_MAP_FALLBACK
    
    def test_fallback_when_invalid_path(self):
        """Debe retornar el fallback con ruta de BD inválida."""
        sector_map = _load_sector_map('/nonexistent/path.db')
        assert sector_map == _SECTOR_MAP_FALLBACK
    
    def test_fallback_is_copy(self, temp_db_empty):
        """El fallback retornado debe ser una copia, no la referencia original."""
        sector_map = _load_sector_map(temp_db_empty)
        sector_map['NEW_TICKER'] = 'NewSector'
        assert 'NEW_TICKER' not in _SECTOR_MAP_FALLBACK


# =============================================================================
# TESTS: PortfolioMomentumBacktester
# =============================================================================

class TestPortfolioMomentumBacktester:
    """Tests para el backtester de momentum."""
    
    def test_init(self, temp_db_with_data):
        """El backtester debe inicializarse correctamente."""
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
        """El backtester debe cargar un mapa de sectores."""
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL'],
        )
        assert isinstance(bt.sector_map, dict)
        assert len(bt.sector_map) > 0
    
    def test_load_data_matrix(self, temp_db_with_data):
        """load_data_matrix debe cargar precios, highs y lows."""
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
        """calculate_atr debe retornar valores positivos."""
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT'],
        )
        prices, highs, lows = bt.load_data_matrix()
        atr = bt.calculate_atr(prices, highs, lows)
        valid = atr.dropna()
        assert (valid >= 0).all().all()
    
    def test_apply_sector_limit(self, temp_db_with_data):
        """apply_sector_limit debe limitar stocks por sector."""
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT'],
        )
        # 5 acciones del mismo sector (Tech)
        ranked = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'CRM']
        result = bt.apply_sector_limit(ranked, max_per_sector=2)
        
        # No debe haber más de 2 del mismo sector
        from collections import Counter
        sector_counts = Counter(bt.sector_map.get(s, 'Other') for s in result)
        for count in sector_counts.values():
            assert count <= 2
    
    def test_backtest_runs(self, temp_db_with_data):
        """run_backtest debe completarse sin errores."""
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
        """La curva de equity no debe ser negativa."""
        bt = PortfolioMomentumBacktester(
            temp_db_with_data,
            universe_list=['AAPL', 'MSFT', 'GOOGL'],
            initial_capital=10000.0
        )
        results = bt.run_backtest(top_n=2, lookback_months=3)
        if results is not None and 'equity' in results.columns:
            assert (results['equity'] >= 0).all()


# =============================================================================
# TESTS: SQL Injection Fix
# =============================================================================

class TestSQLInjectionFix:
    """Verifica que plot_results usa consultas parametrizadas."""
    
    def test_no_fstring_in_plot_results(self):
        """El código de plot_results no debe usar f-strings para SQL."""
        import inspect
        source = inspect.getsource(PortfolioMomentumBacktester.plot_results)
        # No debe contener f-string SQL inseguro
        assert "f\"SELECT" not in source
        assert "f'SELECT" not in source
        # Debe usar parameterized queries
        assert "symbol=?" in source or "params=" in source
