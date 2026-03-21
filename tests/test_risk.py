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

    def test_fixed_percentage_default(self):
        sizer = PositionSizer()
        capital = 100000

        position = sizer.fixed_percentage(capital)

        assert position == 10000

    def test_fixed_percentage_custom(self):
        sizer = PositionSizer()
        capital = 100000

        position = sizer.fixed_percentage(capital, risk_pct=0.05)

        assert position == 5000

    def test_kelly_criterion_positive_edge(self):
        sizer = PositionSizer()
        capital = 100000

        position = sizer.kelly_criterion(
            win_rate=0.6,
            avg_win=150,
            avg_loss=100,
            capital=capital
        )

        assert position > 0
        assert position <= capital * sizer.params.max_position_pct

    def test_kelly_criterion_no_edge(self):
        sizer = PositionSizer()
        capital = 100000

        position = sizer.kelly_criterion(
            win_rate=0.5,
            avg_win=100,
            avg_loss=100,
            capital=capital
        )

        assert position >= 0

    def test_kelly_handles_edge_cases(self):
        sizer = PositionSizer()
        capital = 100000

        position = sizer.kelly_criterion(0.5, 100, 0, capital)
        assert position > 0

        position = sizer.kelly_criterion(0, 100, 100, capital)
        assert position >= 0

    def test_volatility_adjusted_basic(self):
        sizer = PositionSizer()
        capital = 100000
        price = 100

        units_high_atr = sizer.volatility_adjusted(capital, atr=5, price=price)

        units_low_atr = sizer.volatility_adjusted(capital, atr=1, price=price)

        assert units_low_atr >= units_high_atr

    def test_volatility_adjusted_respects_max(self):
        sizer = PositionSizer()
        capital = 100000
        price = 10

        units = sizer.volatility_adjusted(capital, atr=0.01, price=price)
        position_value = units * price

        assert position_value <= capital * sizer.params.max_position_pct


class TestPortfolioRiskManager:

    def test_can_open_position_normal(self):
        manager = PortfolioRiskManager()
        capital = 100000

        can_open = manager.can_open_position(capital, 5000)

        assert can_open is True

    def test_blocks_oversized_position(self):
        manager = PortfolioRiskManager()
        capital = 100000

        can_open = manager.can_open_position(capital, 15000)

        assert can_open is False

    def test_blocks_after_daily_loss(self):
        manager = PortfolioRiskManager()
        capital = 100000

        manager.record_trade(-4000)

        can_open = manager.can_open_position(capital, 5000)

        assert can_open is False

    def test_tracks_open_positions(self):
        manager = PortfolioRiskManager()

        manager.add_position("AAPL", 10000)
        manager.add_position("MSFT", 8000)

        assert manager.get_portfolio_exposure() == 18000

        manager.remove_position("AAPL")
        assert manager.get_portfolio_exposure() == 8000

    def test_blocks_excessive_exposure(self):
        manager = PortfolioRiskManager()
        capital = 100000

        manager.add_position("AAPL", 25000)
        manager.add_position("MSFT", 25000)
        manager.add_position("NVDA", 25000)

        can_open = manager.can_open_position(capital, 10000)

        assert can_open is False

    def test_reset_daily(self):
        manager = PortfolioRiskManager()

        manager.record_trade(-1000)
        manager.reset_daily()

        assert manager.daily_pnl == 0.0


class TestRiskMetrics:

    def test_sharpe_ratio_positive(self):
        returns = pd.Series([0.01, 0.02, 0.015, 0.012, 0.018] * 50)

        sharpe = RiskMetrics.sharpe_ratio(returns)

        assert sharpe > 0

    def test_sharpe_ratio_negative(self):
        returns = pd.Series([-0.01, -0.02, -0.015, -0.012, -0.018] * 50)

        sharpe = RiskMetrics.sharpe_ratio(returns)

        assert sharpe < 0

    def test_max_drawdown(self):
        equity = pd.Series([100, 110, 120, 110, 100, 90, 95, 100])

        mdd = RiskMetrics.max_drawdown(equity)

        assert abs(mdd - (-0.25)) < 0.01

    def test_win_rate(self):
        trades = [100, -50, 75, -25, 30, 40, -10]

        win_rate = RiskMetrics.win_rate(trades)

        assert abs(win_rate - 4/7) < 0.01

    def test_profit_factor(self):
        trades = [100, -50, 200, -100]

        pf = RiskMetrics.profit_factor(trades)

        assert pf == 2.0

    def test_profit_factor_no_losses(self):
        trades = [100, 200, 50]

        pf = RiskMetrics.profit_factor(trades)

        assert pf == float('inf')

    def test_sortino_ratio(self):
        returns = pd.Series([0.05, 0.08, -0.01, 0.06, 0.10, -0.005] * 40)

        sharpe = RiskMetrics.sharpe_ratio(returns)
        sortino = RiskMetrics.sortino_ratio(returns)

        assert sortino > sharpe
