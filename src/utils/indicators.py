import pandas as pd

import numpy as np


class TechnicalMath:


    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()


        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()

        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()


        rs = gain / loss.replace(0, np.nan)

        rsi = 100 - (100 / (1 + rs))

        return rsi.fillna(100)


    @staticmethod
    def ema(series: pd.Series, period: int = 200) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()


    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:

        h_l = high - low

        h_pc = (high - close.shift(1)).abs()

        l_pc = (low - close.shift(1)).abs()

        tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)

        return tr.ewm(alpha=1/period, adjust=False).mean()


    @staticmethod
    def relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
        avg_vol = volume.rolling(window=period).mean()

        return volume / avg_vol.replace(0, 1)


