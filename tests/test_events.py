# tests/test_events.py
"""
Tests para el sistema de eventos del trading.
Ejecutar con: pytest tests/test_events.py -v
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from src.core.events import Event, MarketDataEvent, SignalEvent


# =============================================================================
# TESTS: Event (base)
# =============================================================================

class TestEvent:
    """Tests para la clase base Event."""
    
    def test_event_creation(self):
        """Event debe crearse con tipo y timestamp."""
        event = Event(type='TEST')
        assert event.type == 'TEST'
        assert isinstance(event.timestamp, datetime)
    
    def test_event_payload(self):
        """Event debe aceptar payload arbitrario."""
        payload = {'key': 'value', 'numbers': [1, 2, 3]}
        event = Event(type='DATA', payload=payload)
        assert event.payload == payload
    
    def test_event_default_payload_none(self):
        """Event sin payload debe tener payload=None."""
        event = Event(type='TEST')
        assert event.payload is None
    
    def test_event_timestamp_auto(self):
        """Event debe auto-generar timestamp."""
        event = Event(type='TEST')
        assert isinstance(event.timestamp, datetime)


# =============================================================================
# TESTS: MarketDataEvent
# =============================================================================

class TestMarketDataEvent:
    """Tests para eventos de datos de mercado."""
    
    def test_market_data_event_creation(self):
        """MarketDataEvent debe crearse con symbol y data."""
        df = pd.DataFrame({
            'open': [150.0], 'high': [152.0], 'low': [149.0],
            'close': [151.0], 'volume': [1_000_000]
        })
        # type is required from parent Event; __post_init__ overrides it
        event = MarketDataEvent(type='MARKET_DATA', symbol='AAPL', data=df)
        assert event.symbol == 'AAPL'
        assert len(event.data) == 1
        assert event.data['close'].iloc[0] == 151.0
    
    def test_market_data_event_type(self):
        """MarketDataEvent debe tener type='MARKET_DATA' después de __post_init__."""
        event = MarketDataEvent(type='_', symbol='MSFT', data=pd.DataFrame())
        assert event.type == 'MARKET_DATA'
    
    def test_market_data_event_has_timestamp(self):
        """MarketDataEvent debe tener timestamp automático."""
        event = MarketDataEvent(type='_', symbol='GOOGL', data=pd.DataFrame())
        assert isinstance(event.timestamp, datetime)
    
    def test_market_data_event_defaults_with_required_type(self):
        """MarketDataEvent con type y defaults funciona."""
        event = MarketDataEvent(type='MARKET_DATA')
        assert event.symbol == ""
        assert isinstance(event.data, pd.DataFrame)
        assert len(event.data) == 0


# =============================================================================
# TESTS: SignalEvent
# =============================================================================

class TestSignalEvent:
    """Tests para eventos de señal de trading."""
    
    def test_signal_event_creation(self):
        """SignalEvent debe crearse con symbol y signal_strength."""
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
        """SignalEvent debe tener type='SIGNAL' después de __post_init__."""
        event = SignalEvent(
            type='_',
            symbol='TSLA',
            signal_strength=-0.5,
            strategy_id='technical'
        )
        assert event.type == 'SIGNAL'
    
    def test_signal_event_negative_strength(self):
        """SignalEvent debe aceptar signal_strength negativo (venta)."""
        event = SignalEvent(
            type='SIGNAL',
            symbol='GME',
            signal_strength=-0.9,
            strategy_id='macro'
        )
        assert event.signal_strength == -0.9
    
    def test_signal_event_defaults(self):
        """SignalEvent debe tener defaults razonables."""
        event = SignalEvent(type='SIGNAL')
        assert event.symbol == ""
        assert event.signal_strength == 0.0
        assert event.strategy_id == ""
