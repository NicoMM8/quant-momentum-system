# tests/test_risk.py
"""
Tests unitarios para el módulo de gestión de riesgo.
"""
import pytest
import pandas as pd
import numpy as np
from src.strategies.risk import (
    RiskParameters, 
    PositionSizer, 
    PortfolioRiskManager,
    RiskMetrics
)


class TestPositionSizer:
    """Tests para el calculador de tamaño de posición."""
    
    def test_fixed_percentage_default(self):
        """Fixed percentage debería usar max_position_pct por defecto."""
        sizer = PositionSizer()
        capital = 100000
        
        position = sizer.fixed_percentage(capital)
        
        # Por defecto es 10%
        assert position == 10000
    
    def test_fixed_percentage_custom(self):
        """Fixed percentage debería aceptar porcentaje custom."""
        sizer = PositionSizer()
        capital = 100000
        
        position = sizer.fixed_percentage(capital, risk_pct=0.05)
        
        assert position == 5000
    
    def test_kelly_criterion_positive_edge(self):
        """Kelly debería calcular posición positiva con edge positivo."""
        sizer = PositionSizer()
        capital = 100000
        
        # Sistema con edge: 60% win rate, 1.5:1 win/loss ratio
        position = sizer.kelly_criterion(
            win_rate=0.6,
            avg_win=150,
            avg_loss=100,
            capital=capital
        )
        
        # Kelly debería dar posición positiva
        assert position > 0
        # No debería exceder el máximo
        assert position <= capital * sizer.params.max_position_pct
    
    def test_kelly_criterion_no_edge(self):
        """Kelly debería dar posición mínima sin edge."""
        sizer = PositionSizer()
        capital = 100000
        
        # Sistema sin edge: 50% win rate, 1:1 ratio
        position = sizer.kelly_criterion(
            win_rate=0.5,
            avg_win=100,
            avg_loss=100,
            capital=capital
        )
        
        # Sin edge, Kelly = 0, debería usar fallback
        assert position >= 0
    
    def test_kelly_handles_edge_cases(self):
        """Kelly debería manejar casos edge sin crash."""
        sizer = PositionSizer()
        capital = 100000
        
        # Avg loss = 0
        position = sizer.kelly_criterion(0.5, 100, 0, capital)
        assert position > 0  # Fallback a fixed
        
        # Win rate = 0
        position = sizer.kelly_criterion(0, 100, 100, capital)
        assert position >= 0
    
    def test_volatility_adjusted_basic(self):
        """Volatility adjusted debería dar posición inversamente proporcional a ATR."""
        sizer = PositionSizer()
        capital = 100000
        price = 100
        
        # Alto ATR = menos unidades
        units_high_atr = sizer.volatility_adjusted(capital, atr=5, price=price)
        
        # Bajo ATR = más unidades
        units_low_atr = sizer.volatility_adjusted(capital, atr=1, price=price)
        
        # Con ATR muy bajo, la posición se limita al max_position_pct
        # Ambos pueden ser iguales si están limitados al máximo
        assert units_low_atr >= units_high_atr
    
    def test_volatility_adjusted_respects_max(self):
        """Volatility adjusted no debería exceder max_position_pct."""
        sizer = PositionSizer()
        capital = 100000
        price = 10
        
        # ATR muy bajo resultaría en posición enorme
        units = sizer.volatility_adjusted(capital, atr=0.01, price=price)
        position_value = units * price
        
        # No debería exceder el máximo
        assert position_value <= capital * sizer.params.max_position_pct


class TestPortfolioRiskManager:
    """Tests para el gestor de riesgo del portfolio."""
    
    def test_can_open_position_normal(self):
        """Debería permitir abrir posición dentro de límites."""
        manager = PortfolioRiskManager()
        capital = 100000
        
        # Posición del 5% del capital
        can_open = manager.can_open_position(capital, 5000)
        
        assert can_open is True
    
    def test_blocks_oversized_position(self):
        """Debería bloquear posición que excede max_position_pct."""
        manager = PortfolioRiskManager()
        capital = 100000
        
        # Posición del 15% (límite es 10%)
        can_open = manager.can_open_position(capital, 15000)
        
        assert can_open is False
    
    def test_blocks_after_daily_loss(self):
        """Debería bloquear nuevas posiciones después de pérdida diaria excesiva."""
        manager = PortfolioRiskManager()
        capital = 100000
        
        # Registrar pérdida del 4% (límite es 3%)
        manager.record_trade(-4000)  # -4%
        
        can_open = manager.can_open_position(capital, 5000)
        
        assert can_open is False
    
    def test_tracks_open_positions(self):
        """Debería trackear posiciones abiertas correctamente."""
        manager = PortfolioRiskManager()
        
        manager.add_position("AAPL", 10000)
        manager.add_position("MSFT", 8000)
        
        assert manager.get_portfolio_exposure() == 18000
        
        manager.remove_position("AAPL")
        assert manager.get_portfolio_exposure() == 8000
    
    def test_blocks_excessive_exposure(self):
        """Debería bloquear si exposición total excede límite."""
        manager = PortfolioRiskManager()
        capital = 100000
        
        # Agregar posiciones hasta 75% de exposición
        manager.add_position("AAPL", 25000)
        manager.add_position("MSFT", 25000)
        manager.add_position("NVDA", 25000)
        
        # Intentar agregar otra que llevaría a 85% (límite 80%)
        can_open = manager.can_open_position(capital, 10000)
        
        assert can_open is False
    
    def test_reset_daily(self):
        """Reset diario debería limpiar P&L diario pero mantener semanal."""
        manager = PortfolioRiskManager()
        
        manager.record_trade(-1000)
        manager.reset_daily()
        
        assert manager.daily_pnl == 0.0


class TestRiskMetrics:
    """Tests para las métricas de riesgo."""
    
    def test_sharpe_ratio_positive(self):
        """Sharpe debería ser positivo con retornos consistentemente positivos."""
        returns = pd.Series([0.01, 0.02, 0.015, 0.012, 0.018] * 50)  # 1-2% diario
        
        sharpe = RiskMetrics.sharpe_ratio(returns)
        
        assert sharpe > 0
    
    def test_sharpe_ratio_negative(self):
        """Sharpe debería ser negativo con retornos consistentemente negativos."""
        returns = pd.Series([-0.01, -0.02, -0.015, -0.012, -0.018] * 50)
        
        sharpe = RiskMetrics.sharpe_ratio(returns)
        
        assert sharpe < 0
    
    def test_max_drawdown(self):
        """Max drawdown debería calcular la caída máxima correctamente."""
        # Equity que sube a 120, luego cae a 90
        equity = pd.Series([100, 110, 120, 110, 100, 90, 95, 100])
        
        mdd = RiskMetrics.max_drawdown(equity)
        
        # Max drawdown = (90 - 120) / 120 = -25%
        assert abs(mdd - (-0.25)) < 0.01
    
    def test_win_rate(self):
        """Win rate debería calcular el porcentaje de trades ganadores."""
        trades = [100, -50, 75, -25, 30, 40, -10]  # 4 wins, 3 losses
        
        win_rate = RiskMetrics.win_rate(trades)
        
        assert abs(win_rate - 4/7) < 0.01
    
    def test_profit_factor(self):
        """Profit factor debería ser ganancias brutas / pérdidas brutas."""
        trades = [100, -50, 200, -100]  # Ganancias: 300, Pérdidas: 150
        
        pf = RiskMetrics.profit_factor(trades)
        
        assert pf == 2.0
    
    def test_profit_factor_no_losses(self):
        """Profit factor debería ser infinito si no hay pérdidas."""
        trades = [100, 200, 50]
        
        pf = RiskMetrics.profit_factor(trades)
        
        assert pf == float('inf')
    
    def test_sortino_ratio(self):
        """Sortino debería penalizar solo desviación negativa."""
        # Retornos con alta volatilidad alcista pero poca bajista
        returns = pd.Series([0.05, 0.08, -0.01, 0.06, 0.10, -0.005] * 40)
        
        sharpe = RiskMetrics.sharpe_ratio(returns)
        sortino = RiskMetrics.sortino_ratio(returns)
        
        # Sortino debería ser mayor porque ignora volatilidad alcista
        assert sortino > sharpe
