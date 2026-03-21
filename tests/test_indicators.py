import pytest
import pandas as pd
import numpy as np
from src.utils.indicators import TechnicalMath


class TestRSI:

    def test_rsi_basic_calculation(self):
        prices = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10,
                           45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])
        rsi = TechnicalMath.rsi(prices, period=14)

        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    def test_rsi_overbought(self):
        prices = pd.Series(range(50, 100))
        rsi = TechnicalMath.rsi(prices, period=14)

        assert rsi.iloc[-1] > 70

    def test_rsi_oversold(self):
        prices = pd.Series(range(100, 50, -1))
        rsi = TechnicalMath.rsi(prices, period=14)

        assert rsi.iloc[-1] < 30

    def test_rsi_no_losses_returns_100(self):
        prices = pd.Series([10.0 + i * 0.1 for i in range(30)])
        rsi = TechnicalMath.rsi(prices, period=14)

        assert not np.isnan(rsi.iloc[-1])
        assert not np.isinf(rsi.iloc[-1])
        assert rsi.iloc[-1] == 100.0

    def test_rsi_empty_series(self):
        prices = pd.Series(dtype=float)
        rsi = TechnicalMath.rsi(prices, period=14)
        assert len(rsi) == 0


class TestEMA:

    def test_ema_basic(self):
        prices = pd.Series([10, 12, 11, 13, 14, 12, 15, 16, 14, 17])
        ema = TechnicalMath.ema(prices, period=5)

        assert len(ema) == len(prices)
        assert ema.iloc[-1] >= prices.min()
        assert ema.iloc[-1] <= prices.max()

    def test_ema_follows_trend(self):
        prices = pd.Series(range(1, 51))
        ema = TechnicalMath.ema(prices, period=10)

        assert ema.iloc[-1] < prices.iloc[-1]
        assert ema.iloc[-1] > ema.iloc[-2]

    def test_ema_different_periods(self):
        prices = pd.Series([10] * 20 + [20] * 10)
        ema_short = TechnicalMath.ema(prices, period=5)
        ema_long = TechnicalMath.ema(prices, period=15)

        assert abs(ema_short.iloc[-1] - 20) < abs(ema_long.iloc[-1] - 20)


class TestATR:

    def test_atr_basic(self):
        np.random.seed(42)
        n = 50
        close = pd.Series(100 + np.cumsum(np.random.randn(n)))
        high = close + abs(np.random.randn(n)) * 2
        low = close - abs(np.random.randn(n)) * 2

        atr = TechnicalMath.atr(high, low, close, period=14)

        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()

    def test_atr_increases_with_volatility(self):
        close_low_vol = pd.Series([100] * 30)
        high_low_vol = close_low_vol + 0.5
        low_low_vol = close_low_vol - 0.5

        close_high_vol = pd.Series([100 + (i % 10 - 5) * 2 for i in range(30)])
        high_high_vol = close_high_vol + 3
        low_high_vol = close_high_vol - 3

        atr_low = TechnicalMath.atr(high_low_vol, low_low_vol, close_low_vol, period=14)
        atr_high = TechnicalMath.atr(high_high_vol, low_high_vol, close_high_vol, period=14)

        assert atr_high.iloc[-1] > atr_low.iloc[-1]


class TestRelativeVolume:

    def test_rvol_basic(self):
        volume = pd.Series([1000] * 30)
        rvol = TechnicalMath.relative_volume(volume, period=20)

        assert abs(rvol.iloc[-1] - 1.0) < 0.01

    def test_rvol_spike(self):
        volume = pd.Series([1000] * 25 + [5000] * 5)
        rvol = TechnicalMath.relative_volume(volume, period=20)

        assert rvol.iloc[-1] > 2.0

    def test_rvol_handles_zero_volume(self):
        volume = pd.Series([0] * 30)
        rvol = TechnicalMath.relative_volume(volume, period=20)

        assert not np.isinf(rvol.iloc[-1])
