from dataclasses import dataclass

from typing import Dict, List, Optional, Tuple

import pandas as pd

import numpy as np

from src.core.interfaces import ISignalGenerator


@dataclass
class OrderFlowSignal:
    symbol: str
    timestamp: pd.Timestamp
    signal_type: str
    strength: float
    obi: float
    delta: float
    confidence: float


class OrderFlowAnalyzer:

    def __init__(self, obi_threshold: float = 0.4):
        self.obi_threshold = obi_threshold


    def calculate_obi(self, bid_volume: float, ask_volume: float) -> float:
        total = bid_volume + ask_volume
        if total == 0:
            return 0.0
        return (bid_volume - ask_volume) / total


    def calculate_delta(self, df: pd.DataFrame) -> pd.Series:
        buy_volume = df['volume'].where(df['close'] > df['open'], 0)

        sell_volume = df['volume'].where(df['close'] < df['open'], 0)

        return (buy_volume - sell_volume).cumsum()


    def detect_absorption(
        self,
        df: pd.DataFrame,
        threshold: float = 2.0
    ) -> pd.Series:
        price_range = (df['high'] - df['low']).abs()

        avg_range = price_range.rolling(20).mean()
        avg_volume = df['volume'].rolling(20).mean()

        high_volume = df['volume'] > avg_volume * threshold

        low_range = price_range < avg_range * 0.5

        return high_volume & low_range


    def detect_exhaustion(
        self,
        df: pd.DataFrame,
        lookback: int = 5
    ) -> pd.Series:
        returns = df['close'].pct_change()

        strong_move = returns.abs() > returns.rolling(20).std() * 2

        vol_change = df['volume'].pct_change(lookback)

        declining_volume = vol_change < -0.3

        return strong_move & declining_volume


class SmartMoneyConcepts:


    @staticmethod
    def identify_swing_points(
        df: pd.DataFrame,
        sensitivity: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        highs = df['high']
        lows = df['low']

        swing_highs = pd.Series(False, index=df.index)
        swing_lows = pd.Series(False, index=df.index)

        for i in range(sensitivity, len(df) - sensitivity):
            if all(highs.iloc[i] > highs.iloc[i-sensitivity:i]) and \
               all(highs.iloc[i] > highs.iloc[i+1:i+sensitivity+1]):
                swing_highs.iloc[i] = True

            if all(lows.iloc[i] < lows.iloc[i-sensitivity:i]) and \
               all(lows.iloc[i] < lows.iloc[i+1:i+sensitivity+1]):
                swing_lows.iloc[i] = True

        return swing_highs, swing_lows


    @staticmethod
    def detect_bos(df: pd.DataFrame, swing_highs: pd.Series, swing_lows: pd.Series) -> pd.Series:
        bos = pd.Series(0, index=df.index)

        last_sh = None
        last_sl = None

        for i in range(len(df)):
            if swing_highs.iloc[i]:
                last_sh = df['high'].iloc[i]

            if swing_lows.iloc[i]:
                last_sl = df['low'].iloc[i]

            if last_sh is not None and df['close'].iloc[i] > last_sh:
                bos.iloc[i] = 1
                last_sh = df['high'].iloc[i]

            if last_sl is not None and df['close'].iloc[i] < last_sl:
                bos.iloc[i] = -1
                last_sl = df['low'].iloc[i]

        return bos


    @staticmethod
    def identify_order_blocks(
        df: pd.DataFrame,
        lookback: int = 10
    ) -> pd.DataFrame:
        result = pd.DataFrame(index=df.index)
        result['ob_bullish'] = False
        result['ob_bearish'] = False

        returns = df['close'].pct_change()
        avg_return = returns.rolling(20).std()

        for i in range(lookback, len(df)):
            if returns.iloc[i] > avg_return.iloc[i] * 2:
                for j in range(i-1, max(0, i-lookback), -1):
                    if df['close'].iloc[j] < df['open'].iloc[j]:
                        result['ob_bullish'].iloc[j] = True
                        break

            if returns.iloc[i] < -avg_return.iloc[i] * 2:
                for j in range(i-1, max(0, i-lookback), -1):
                    if df['close'].iloc[j] > df['open'].iloc[j]:
                        result['ob_bearish'].iloc[j] = True
                        break

        return result


class MicroStructureStrategy(ISignalGenerator):

    def __init__(self, obi_threshold: float = 0.4):
        self.obi_threshold = obi_threshold
        self.order_flow = OrderFlowAnalyzer(obi_threshold)
        self.smc = SmartMoneyConcepts()

    def update_universe(
        self,
        candidates: List[str],
        data_context: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[str]:
        return candidates


    def analyze_orderflow(self, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty or len(df) < 20:
            return {'obi': 0.0, 'delta': 0.0, 'absorption': 0.0}

        bullish_candles = (df['close'] > df['open']).sum()
        bearish_candles = (df['close'] < df['open']).sum()

        obi = self.order_flow.calculate_obi(bullish_candles, bearish_candles)
        delta = self.order_flow.calculate_delta(df).iloc[-1]
        absorption = self.order_flow.detect_absorption(df).sum() / len(df)

        return {
            'obi': obi,
            'delta': delta,
            'absorption': absorption
        }


    def analyze_structure(self, df: pd.DataFrame) -> Dict[str, any]:
        if df.empty or len(df) < 20:
            return {'trend': 'neutral', 'bos': 0, 'order_blocks': 0}

        swing_highs, swing_lows = self.smc.identify_swing_points(df)

        bos = self.smc.detect_bos(df, swing_highs, swing_lows)

        order_blocks = self.smc.identify_order_blocks(df)

        recent_bos = bos.tail(20).sum()
        if recent_bos > 0:
            trend = 'bullish'
        elif recent_bos < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'

        return {
            'trend': trend,
            'bos': bos.iloc[-1],
            'order_blocks_bullish': order_blocks['ob_bullish'].sum(),
            'order_blocks_bearish': order_blocks['ob_bearish'].sum()
        }


    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        if not data:
            return 0.0

        signals = []

        for symbol, df in data.items():
            if df.empty:
                continue

            of_analysis = self.analyze_orderflow(df)
            of_signal = of_analysis['obi']

            struct_analysis = self.analyze_structure(df)
            if struct_analysis['trend'] == 'bullish':
                struct_signal = 0.5
            elif struct_analysis['trend'] == 'bearish':
                struct_signal = -0.5
            else:
                struct_signal = 0.0

            bos_signal = struct_analysis['bos'] * 0.5

            combined = (
                of_signal * 0.4 +
                struct_signal * 0.4 +
                bos_signal * 0.2
            )

            signals.append(combined)

        if not signals:
            return 0.0

        avg_signal = sum(signals) / len(signals)

        if abs(avg_signal) < 0.2:
            return 0.0

        return max(-1.0, min(1.0, avg_signal))


