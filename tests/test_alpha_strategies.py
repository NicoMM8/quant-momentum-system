import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sqlite3
import tempfile
import os

from src.core.interfaces import IUniverseFilter, ISignalGenerator, IStrategy


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    n = 50
    base = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        'open': base,
        'high': base + abs(np.random.randn(n)),
        'low': base - abs(np.random.randn(n)),
        'close': base + np.random.randn(n) * 0.3,
        'volume': np.random.randint(500_000, 5_000_000, n).astype(float)
    })


@pytest.fixture
def sample_data_dict(sample_ohlcv):
    return {
        'AAPL': sample_ohlcv.copy(),
        'MSFT': sample_ohlcv.copy(),
    }


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)

    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='B')
    rows = []
    for symbol in ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']:
        base = 100 + np.cumsum(np.random.randn(100) * 0.5)
        for i, date in enumerate(dates):
            rows.append({
                'datetime': str(date),
                'symbol': symbol,
                'open': float(base[i]),
                'high': float(base[i] + abs(np.random.randn())),
                'low': float(base[i] - abs(np.random.randn())),
                'close': float(base[i] + np.random.randn() * 0.3),
                'volume': int(np.random.randint(500_000, 5_000_000))
            })

    df = pd.DataFrame(rows)
    df.to_sql('market_data', conn, if_exists='replace', index=False)

    fund_rows = []
    sectors = ['Technology', 'Technology', 'Technology', 'Technology', 'Consumer Discretionary']
    for i, symbol in enumerate(['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']):
        fund_rows.append({
            'symbol': symbol,
            'date': '2024-06-01',
            'pe_ratio': float(np.random.uniform(10, 40)),
            'pb_ratio': float(np.random.uniform(1, 15)),
            'debt_to_equity': float(np.random.uniform(0.2, 2.0)),
            'roe': float(np.random.uniform(0.05, 0.40)),
            'revenue_growth': float(np.random.uniform(-0.1, 0.5)),
            'free_cash_flow': float(np.random.uniform(1e9, 1e11)),
            'market_cap': float(np.random.uniform(1e11, 3e12)),
        })

    fund_df = pd.DataFrame(fund_rows)
    fund_df.to_sql('fundamentals', conn, if_exists='replace', index=False)

    assets_rows = []
    for i, symbol in enumerate(['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']):
        assets_rows.append({'symbol': symbol, 'sector': sectors[i]})
    assets_df = pd.DataFrame(assets_rows)
    assets_df.to_sql('assets', conn, if_exists='replace', index=False)

    conn.close()
    yield path
    import gc; gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


class TestInterfaceHierarchy:

    def test_istrategy_inherits_both(self):
        assert issubclass(IStrategy, IUniverseFilter)
        assert issubclass(IStrategy, ISignalGenerator)

    def test_iuniversefilter_is_abstract(self):
        with pytest.raises(TypeError):
            IUniverseFilter()

    def test_isignalgenerator_is_abstract(self):
        with pytest.raises(TypeError):
            ISignalGenerator()


class TestMacroScanner:

    def test_macro_is_universe_filter(self, temp_db):
        from src.strategies.alpha.macro import MacroScannerStrategy
        scanner = MacroScannerStrategy(temp_db)
        assert isinstance(scanner, IUniverseFilter)

    def test_macro_update_universe_returns_list(self, temp_db):
        from src.strategies.alpha.macro import MacroScannerStrategy
        scanner = MacroScannerStrategy(temp_db)
        result = scanner.update_universe(['AAPL', 'MSFT', 'GOOGL'])
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_macro_filters_candidates(self, temp_db):
        from src.strategies.alpha.macro import MacroScannerStrategy
        scanner = MacroScannerStrategy(temp_db)
        candidates = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
        result = scanner.update_universe(candidates)
        assert set(result).issubset(set(candidates))

    def test_macro_empty_candidates(self, temp_db):
        from src.strategies.alpha.macro import MacroScannerStrategy
        scanner = MacroScannerStrategy(temp_db)
        result = scanner.update_universe([])
        assert isinstance(result, list)
        assert len(result) > 0


class TestTechnicalFilter:

    def test_technical_is_universe_filter(self, temp_db):
        from src.strategies.alpha.technical import TechnicalFilterStrategy
        filt = TechnicalFilterStrategy(temp_db)
        assert isinstance(filt, IUniverseFilter)

    def test_technical_update_universe_returns_list(self, temp_db):
        from src.strategies.alpha.technical import TechnicalFilterStrategy
        filt = TechnicalFilterStrategy(temp_db)
        result = filt.update_universe(['AAPL', 'MSFT', 'GOOGL'])
        assert isinstance(result, list)

    def test_technical_filters_reduces_set(self, temp_db):
        from src.strategies.alpha.technical import TechnicalFilterStrategy
        filt = TechnicalFilterStrategy(temp_db)
        candidates = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
        result = filt.update_universe(candidates)
        assert set(result).issubset(set(candidates))


class TestMicroStructure:

    def test_micro_is_signal_generator(self):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        assert isinstance(micro, ISignalGenerator)

    def test_micro_generate_signal_range(self, sample_data_dict):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        signal = micro.generate_signal(sample_data_dict)
        assert -1.0 <= signal <= 1.0

    def test_micro_generate_signal_empty_data(self):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        signal = micro.generate_signal({})
        assert signal == 0.0

    def test_micro_generate_signal_single_stock(self, sample_ohlcv):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        signal = micro.generate_signal({'AAPL': sample_ohlcv})
        assert isinstance(signal, float)
        assert -1.0 <= signal <= 1.0

    def test_micro_orderflow_analysis(self, sample_ohlcv):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        result = micro.analyze_orderflow(sample_ohlcv)
        assert 'obi' in result
        assert 'delta' in result
        assert 'absorption' in result
        assert -1.0 <= result['obi'] <= 1.0

    def test_micro_structure_analysis(self, sample_ohlcv):
        from src.strategies.alpha.micro import MicroStructureStrategy
        micro = MicroStructureStrategy()
        result = micro.analyze_structure(sample_ohlcv)
        assert 'trend' in result
        assert result['trend'] in ('bullish', 'bearish', 'neutral')
        assert 'bos' in result


class TestOrderFlowAnalyzer:

    def test_obi_balanced(self):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        assert analyzer.calculate_obi(1000, 1000) == 0.0

    def test_obi_all_buyers(self):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        assert analyzer.calculate_obi(1000, 0) == 1.0

    def test_obi_all_sellers(self):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        assert analyzer.calculate_obi(0, 1000) == -1.0

    def test_obi_zero_volume(self):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        assert analyzer.calculate_obi(0, 0) == 0.0

    def test_delta_cumulative(self, sample_ohlcv):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        delta = analyzer.calculate_delta(sample_ohlcv)
        assert isinstance(delta, pd.Series)
        assert len(delta) == len(sample_ohlcv)

    def test_absorption_detection(self, sample_ohlcv):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        absorption = analyzer.detect_absorption(sample_ohlcv)
        assert isinstance(absorption, pd.Series)
        assert absorption.dtype == bool

    def test_exhaustion_detection(self, sample_ohlcv):
        from src.strategies.alpha.micro import OrderFlowAnalyzer
        analyzer = OrderFlowAnalyzer()
        exhaustion = analyzer.detect_exhaustion(sample_ohlcv)
        assert isinstance(exhaustion, pd.Series)
        assert exhaustion.dtype == bool


class TestSmartMoneyConcepts:

    def test_swing_points_detection(self, sample_ohlcv):
        from src.strategies.alpha.micro import SmartMoneyConcepts
        smc = SmartMoneyConcepts()
        highs, lows = smc.identify_swing_points(sample_ohlcv)
        assert isinstance(highs, pd.Series)
        assert isinstance(lows, pd.Series)
        assert highs.dtype == bool
        assert lows.dtype == bool

    def test_bos_detection(self, sample_ohlcv):
        from src.strategies.alpha.micro import SmartMoneyConcepts
        smc = SmartMoneyConcepts()
        highs, lows = smc.identify_swing_points(sample_ohlcv)
        bos = smc.detect_bos(sample_ohlcv, highs, lows)
        assert isinstance(bos, pd.Series)
        assert set(bos.unique()).issubset({-1, 0, 1})

    def test_order_blocks_detection(self, sample_ohlcv):
        from src.strategies.alpha.micro import SmartMoneyConcepts
        smc = SmartMoneyConcepts()
        ob = smc.identify_order_blocks(sample_ohlcv)
        assert isinstance(ob, pd.DataFrame)
        assert 'ob_bullish' in ob.columns
        assert 'ob_bearish' in ob.columns
