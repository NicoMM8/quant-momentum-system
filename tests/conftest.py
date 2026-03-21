import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_ohlcv_data():
    np.random.seed(42)
    n = 100

    dates = pd.date_range(start='2024-01-01', periods=n, freq='D')
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)

    df = pd.DataFrame({
        'datetime': dates,
        'open': close + np.random.randn(n) * 0.2,
        'high': close + abs(np.random.randn(n) * 0.5),
        'low': close - abs(np.random.randn(n) * 0.5),
        'close': close,
        'volume': np.random.randint(1000, 10000, n)
    })

    return df


@pytest.fixture
def sample_tick_data():
    dates = pd.date_range(start='2024-01-01 09:30', periods=50, freq='1min')

    df = pd.DataFrame({
        'datetime': dates,
        'close': 100 + np.random.randn(50) * 0.5,
        'obi': np.random.uniform(-0.5, 0.5, 50)
    })

    return df


@pytest.fixture
def capital():
    return 100000.0
