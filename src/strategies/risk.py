from dataclasses import dataclass

from typing import Optional, Dict, List

import pandas as pd

import numpy as np

import yaml

import os


@dataclass
class RiskParameters:
    max_position_pct: float = 0.10
    max_portfolio_risk: float = 0.02
    kelly_fraction: float = 0.25
    stop_loss_pct: float = 0.005
    take_profit_pct: float = 0.015
    max_daily_loss: float = 0.03
    max_weekly_loss: float = 0.06


class PositionSizer:

    def __init__(self, params: Optional[RiskParameters] = None):
        self.params = params or RiskParameters()

    @staticmethod
    def load_from_config(config_path: str = "config/settings.yaml") -> 'PositionSizer':
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                risk_config = config.get('risk', {})
                params = RiskParameters(
                    max_position_pct=risk_config.get('max_position_pct', 0.10),
                    max_portfolio_risk=risk_config.get('max_portfolio_risk', 0.02),
                    kelly_fraction=risk_config.get('kelly_fraction', 0.25),
                    stop_loss_pct=risk_config.get('stop_loss_pct', 0.005),
                    take_profit_pct=risk_config.get('take_profit_pct', 0.015),
                    max_daily_loss=risk_config.get('max_daily_loss', 0.03),
                    max_weekly_loss=risk_config.get('max_weekly_loss', 0.06)
                )
                return PositionSizer(params)
        return PositionSizer()


    def fixed_percentage(self, capital: float, risk_pct: Optional[float] = None) -> float:
        pct = risk_pct or self.params.max_position_pct
        return capital * pct


    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: float
    ) -> float:
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            return self.fixed_percentage(capital)

        b = avg_win / avg_loss

        p = win_rate
        q = 1 - p

        kelly_pct = (b * p - q) / b

        fractional_kelly = kelly_pct * self.params.kelly_fraction

        final_pct = max(0, min(fractional_kelly, self.params.max_position_pct))

        return capital * final_pct


    def volatility_adjusted(
        self,
        capital: float,
        atr: float,
        price: float,
        risk_per_trade: Optional[float] = None
    ) -> float:
        risk_amount = capital * (risk_per_trade or self.params.max_portfolio_risk)

        if atr == 0:
            return 0

        units = risk_amount / atr

        position_value = units * price

        max_position = capital * self.params.max_position_pct

        if position_value > max_position:
            units = max_position / price

        return units


class PortfolioRiskManager:

    def __init__(self, params: Optional[RiskParameters] = None):
        self.params = params or RiskParameters()

        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0

        self.open_positions: Dict[str, float] = {}

    def can_open_position(self, capital: float, position_value: float) -> bool:
        if position_value > capital * self.params.max_position_pct:
            return False

        if self.daily_pnl < -capital * self.params.max_daily_loss:
            return False

        if self.weekly_pnl < -capital * self.params.max_weekly_loss:
            return False

        total_exposure = sum(self.open_positions.values()) + position_value
        max_exposure = capital * 0.80

        if total_exposure > max_exposure:
            return False

        return True

    def record_trade(self, pnl: float) -> None:
        self.daily_pnl += pnl
        self.weekly_pnl += pnl

    def reset_daily(self) -> None:
        self.daily_pnl = 0.0

    def reset_weekly(self) -> None:
        self.weekly_pnl = 0.0
        self.daily_pnl = 0.0

    def add_position(self, symbol: str, value: float) -> None:
        self.open_positions[symbol] = value

    def remove_position(self, symbol: str) -> None:
        self.open_positions.pop(symbol, None)

    def get_portfolio_exposure(self) -> float:
        return sum(self.open_positions.values())


class RiskMetrics:

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        if returns.std() == 0:
            return 0.0

        daily_rf = risk_free_rate / 252

        excess_returns = returns.mean() - daily_rf

        return (excess_returns / returns.std()) * np.sqrt(252)

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        excess_returns = returns.mean() - (risk_free_rate / 252)

        return (excess_returns / downside_returns.std()) * np.sqrt(252)

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        rolling_max = equity_curve.expanding().max()

        drawdowns = (equity_curve - rolling_max) / rolling_max

        return drawdowns.min()

    @staticmethod
    def calmar_ratio(returns: pd.Series, equity_curve: pd.Series) -> float:
        annual_return = returns.mean() * 252

        mdd = abs(RiskMetrics.max_drawdown(equity_curve))

        if mdd == 0:
            return 0.0

        return annual_return / mdd

    @staticmethod
    def win_rate(trades: List[float]) -> float:
        if not trades:
            return 0.0

        winning = sum(1 for t in trades if t > 0)

        return winning / len(trades)

    @staticmethod
    def profit_factor(trades: List[float]) -> float:
        gross_profit = sum(t for t in trades if t > 0)

        gross_loss = abs(sum(t for t in trades if t < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss


