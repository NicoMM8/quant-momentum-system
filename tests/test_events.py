import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from src.core.events import Event, MarketDataEvent, SignalEvent


class TestEvent:

    def test_event_creation(self):
        event = Event(type='TEST')
        assert event.type == 'TEST'
        assert isinstance(event.timestamp, datetime)

    def test_event_payload(self):
        payload = {'key': 'value', 'numbers': [1, 2, 3]}
        event = Event(type='DATA', payload=payload)
        assert event.payload == payload

    def test_event_default_payload_none(self):
        event = Event(type='TEST')
        assert event.payload is None

    def test_event_timestamp_auto(self):
        event = Event(type='TEST')
        assert isinstance(event.timestamp, datetime)


class TestMarketDataEvent:

    def test_market_data_event_creation(self):
        df = pd.DataFrame({
            'open': [150.0], 'high': [152.0], 'low': [149.0],
            'close': [151.0], 'volume': [1_000_000]
        })
        event = MarketDataEvent(type='MARKET_DATA', symbol='AAPL', data=df)
        assert event.symbol == 'AAPL'
        assert len(event.data) == 1
        assert event.data['close'].iloc[0] == 151.0

    def test_market_data_event_type(self):
        event = MarketDataEvent(type='_', symbol='MSFT', data=pd.DataFrame())
        assert event.type == 'MARKET_DATA'

    def test_market_data_event_has_timestamp(self):
        event = MarketDataEvent(type='_', symbol='GOOGL', data=pd.DataFrame())
        assert isinstance(event.timestamp, datetime)

    def test_market_data_event_defaults_with_required_type(self):
        event = MarketDataEvent(type='MARKET_DATA')
        assert event.symbol == ""
        assert isinstance(event.data, pd.DataFrame)
        assert len(event.data) == 0


class TestSignalEvent:

    def test_signal_event_creation(self):
        event = SignalEvent(
            type='SIGNAL',
            symbol='AAPL',
            signal_strength=0.75,
            strategy_id='micro_v1'
        )
        assert event.symbol == 'AAPL'
        assert event.signal_strength == 0.75
        assert event.strategy_id == 'micro_v1'

    def test_signal_event_type(self):
        event = SignalEvent(
            type='_',
            symbol='TSLA',
            signal_strength=-0.5,
            strategy_id='technical'
        )
        assert event.type == 'SIGNAL'

    def test_signal_event_negative_strength(self):
        event = SignalEvent(
            type='SIGNAL',
            symbol='GME',
            signal_strength=-0.9,
            strategy_id='macro'
        )
        assert event.signal_strength == -0.9

    def test_signal_event_defaults(self):
        event = SignalEvent(type='SIGNAL')
        assert event.symbol == ""
        assert event.signal_strength == 0.0
        assert event.strategy_id == ""
