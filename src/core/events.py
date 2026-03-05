from dataclasses import dataclass, field
from typing import Any
import pandas as pd
from datetime import datetime

@dataclass
class Event:
    """
    Base Event class underpinning the core event-driven architecture.
    All system events inherit from this class to guarantee routing consistency
    across the messaging bus.
    """
    type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: Any = None


@dataclass
class MarketDataEvent(Event):
    """
    Dispatched when new market data updates are ingested.
    Triggered periodically during live execution or iteratively in backtesting.
    """
    symbol: str = ""
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __post_init__(self):
        self.type = 'MARKET_DATA'


@dataclass
class SignalEvent(Event):
    """
    Dispatched by Alpha Generation models indicating a trading opportunity.
    Routed to the Order Management System (OMS) / Risk modules for execution evaluation.
    
    Attributes:
        symbol (str): Target asset ticker.
        signal_strength (float): Direction and magnitude [-1.0, 1.0].
        strategy_id (str): Identifier of the originating alpha model.
    """
    symbol: str = ""
    signal_strength: float = 0.0
    strategy_id: str = ""

    def __post_init__(self):
        self.type = 'SIGNAL'