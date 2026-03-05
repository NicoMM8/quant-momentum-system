# tests/test_indicators.py
"""
Tests unitarios para el módulo de indicadores técnicos.
Ejecutar con: pytest tests/ -v
"""
import pytest
import pandas as pd
import numpy as np
from src.utils.indicators import TechnicalMath


class TestRSI:
    """Tests para el cálculo de RSI."""
    
    def test_rsi_basic_calculation(self):
        """RSI debería retornar valores entre 0 y 100."""
        prices = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 
                           45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])
        rsi = TechnicalMath.rsi(prices, period=14)
        
        # Verificar que todos los valores válidos estén en rango
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()
    
    def test_rsi_overbought(self):
        """RSI debería ser alto (>70) después de ganancias consecutivas."""
        # Serie que solo sube
        prices = pd.Series(range(50, 100))
        rsi = TechnicalMath.rsi(prices, period=14)
        
        # Los últimos valores deberían indicar sobrecompra
        assert rsi.iloc[-1] > 70
    
    def test_rsi_oversold(self):
        """RSI debería ser bajo (<30) después de pérdidas consecutivas."""
        # Serie que solo baja
        prices = pd.Series(range(100, 50, -1))
        rsi = TechnicalMath.rsi(prices, period=14)
        
        # Los últimos valores deberían indicar sobreventa
        assert rsi.iloc[-1] < 30
    
    def test_rsi_no_losses_returns_100(self):
        """RSI debería ser 100 cuando no hay pérdidas (división por cero manejada)."""
        # Serie que solo sube constantemente
        prices = pd.Series([10.0 + i * 0.1 for i in range(30)])
        rsi = TechnicalMath.rsi(prices, period=14)
        
        # Debería retornar 100, no inf o NaN
        assert not np.isnan(rsi.iloc[-1])
        assert not np.isinf(rsi.iloc[-1])
        assert rsi.iloc[-1] == 100.0
    
    def test_rsi_empty_series(self):
        """RSI debería manejar series vacías sin error."""
        prices = pd.Series(dtype=float)
        rsi = TechnicalMath.rsi(prices, period=14)
        assert len(rsi) == 0


class TestEMA:
    """Tests para Media Móvil Exponencial."""
    
    def test_ema_basic(self):
        """EMA debería retornar valores suavizados."""
        prices = pd.Series([10, 12, 11, 13, 14, 12, 15, 16, 14, 17])
        ema = TechnicalMath.ema(prices, period=5)
        
        assert len(ema) == len(prices)
        # EMA debería estar entre min y max de precios
        assert ema.iloc[-1] >= prices.min()
        assert ema.iloc[-1] <= prices.max()
    
    def test_ema_follows_trend(self):
        """EMA debería seguir la tendencia del precio."""
        # Tendencia alcista
        prices = pd.Series(range(1, 51))
        ema = TechnicalMath.ema(prices, period=10)
        
        # EMA final debería ser menor que el precio (lag)
        assert ema.iloc[-1] < prices.iloc[-1]
        # Pero mayor que el EMA anterior (siguiendo tendencia)
        assert ema.iloc[-1] > ema.iloc[-2]
    
    def test_ema_different_periods(self):
        """EMA corta debería ser más sensible que EMA larga."""
        prices = pd.Series([10] * 20 + [20] * 10)
        ema_short = TechnicalMath.ema(prices, period=5)
        ema_long = TechnicalMath.ema(prices, period=15)
        
        # EMA corta debería estar más cerca del precio actual
        assert abs(ema_short.iloc[-1] - 20) < abs(ema_long.iloc[-1] - 20)


class TestATR:
    """Tests para Average True Range."""
    
    def test_atr_basic(self):
        """ATR debería calcular la volatilidad correctamente."""
        # Crear datos OHLC simulados
        np.random.seed(42)
        n = 50
        close = pd.Series(100 + np.cumsum(np.random.randn(n)))
        high = close + abs(np.random.randn(n)) * 2
        low = close - abs(np.random.randn(n)) * 2
        
        atr = TechnicalMath.atr(high, low, close, period=14)
        
        # ATR debería ser positivo
        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()
    
    def test_atr_increases_with_volatility(self):
        """ATR debería aumentar cuando aumenta la volatilidad."""
        # Período de baja volatilidad
        close_low_vol = pd.Series([100] * 30)
        high_low_vol = close_low_vol + 0.5
        low_low_vol = close_low_vol - 0.5
        
        # Período de alta volatilidad
        close_high_vol = pd.Series([100 + (i % 10 - 5) * 2 for i in range(30)])
        high_high_vol = close_high_vol + 3
        low_high_vol = close_high_vol - 3
        
        atr_low = TechnicalMath.atr(high_low_vol, low_low_vol, close_low_vol, period=14)
        atr_high = TechnicalMath.atr(high_high_vol, low_high_vol, close_high_vol, period=14)
        
        # ATR debería ser mayor en período volátil
        assert atr_high.iloc[-1] > atr_low.iloc[-1]


class TestRelativeVolume:
    """Tests para Relative Volume."""
    
    def test_rvol_basic(self):
        """RVOL debería ser 1.0 cuando el volumen es igual a la media."""
        # Volumen constante
        volume = pd.Series([1000] * 30)
        rvol = TechnicalMath.relative_volume(volume, period=20)
        
        # RVOL debería ser 1.0 (volumen = media)
        assert abs(rvol.iloc[-1] - 1.0) < 0.01
    
    def test_rvol_spike(self):
        """RVOL debería ser > 1 cuando hay spike de volumen."""
        # Volumen normal seguido de spike
        volume = pd.Series([1000] * 25 + [5000] * 5)
        rvol = TechnicalMath.relative_volume(volume, period=20)
        
        # RVOL debería ser alto en el spike
        assert rvol.iloc[-1] > 2.0
    
    def test_rvol_handles_zero_volume(self):
        """RVOL debería manejar volumen cero sin división por cero."""
        volume = pd.Series([0] * 30)
        rvol = TechnicalMath.relative_volume(volume, period=20)
        
        # No debería haber inf o NaN
        assert not np.isinf(rvol.iloc[-1])
