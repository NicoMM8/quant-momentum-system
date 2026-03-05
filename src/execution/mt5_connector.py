"""
═══════════════════════════════════════════════════════════════════════════════
  MT5 CONNECTOR — Interfaz con MetaTrader 5 (Admiral Markets)
  
  Abstrae toda la comunicación con el terminal MT5:
  - Conexión / autenticación
  - Consulta de cuenta, posiciones, precios
  - Envío / cierre / modificación de órdenes
  - Mapeo de símbolos (AAPL → AAPL.US para Admiral)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import yaml
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logger import get_logger, LogEmoji

logger = get_logger("mt5_connector")

# ─────────────────────────────────────────────────────────────────────────────
# Importación condicional de MetaTrader5
# ─────────────────────────────────────────────────────────────────────────────

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 no instalado. pip install MetaTrader5")


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AccountInfo:
    """Información de la cuenta de trading."""
    login: int = 0
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    profit: float = 0.0
    currency: str = "USD"
    server: str = ""
    company: str = ""


@dataclass 
class SymbolInfo:
    """Información de un símbolo/instrumento."""
    name: str = ""
    description: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: int = 0
    point: float = 0.0
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0
    trade_mode: int = 0
    currency_profit: str = "USD"


@dataclass
class OrderResult:
    """Resultado de una operación de orden."""
    success: bool = False
    ticket: int = 0
    volume: float = 0.0
    price: float = 0.0
    comment: str = ""
    retcode: int = 0
    retcode_external: int = 0


@dataclass
class PositionInfo:
    """Información de una posición abierta."""
    ticket: int = 0
    symbol: str = ""
    type: int = 0  # 0=BUY, 1=SELL
    volume: float = 0.0
    price_open: float = 0.0
    price_current: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    profit: float = 0.0
    time: Optional[datetime] = None
    comment: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de símbolos
# ─────────────────────────────────────────────────────────────────────────────

# Admiral Markets usa sufijos para diferentes mercados
SYMBOL_SUFFIXES = {
    'us_stocks': '.US',     # AAPL → AAPL.US
    'uk_stocks': '.UK',     # BARC → BARC.UK
    'forex': '',            # EURUSD → EURUSD (sin sufijo)
    'indices': '',          # US500 → US500
    'commodities': '',      # XAUUSD → XAUUSD
}

# Símbolos que NO necesitan sufijo (forex, índices, commodities)
NO_SUFFIX_PATTERNS = [
    'EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD',  # Forex
    'US500', 'US100', 'US30', 'DE40', 'UK100', 'JP225',         # Índices
    'XAUUSD', 'XAGUSD', 'USOIL', 'UKOIL',                      # Commodities
    'BTCUSD', 'ETHUSD',                                          # Crypto
]


def map_symbol_to_mt5(symbol: str, suffix: str = ".US") -> str:
    """
    Convierte símbolo de yfinance a formato MT5/Admiral.
    
    AAPL  → AAPL.US  (US stock)
    EURUSD → EURUSD  (forex, sin cambio)
    """
    symbol_upper = symbol.upper().replace('-', '.')
    
    # Si ya tiene sufijo, no tocar
    if '.' in symbol_upper and any(symbol_upper.endswith(s) for s in ['.US', '.UK', '.EU']):
        return symbol_upper
    
    # Si es forex/índice/commodity, no agregar sufijo
    for pattern in NO_SUFFIX_PATTERNS:
        if pattern in symbol_upper:
            return symbol_upper
            
    # Admiral Markets DEMO and LIVE CFDs
    # Let's try #SYMBOL.US or #SYMBOL
    return f"#{symbol_upper}.US"


def map_symbol_from_mt5(mt5_symbol: str) -> str:
    """
    Convierte símbolo MT5 a formato yfinance.
    
    AAPL.US → AAPL
    EURUSD  → EURUSD
    """
    for suf in ['.US', '.UK', '.EU']:
        if mt5_symbol.endswith(suf):
            mt5_symbol = mt5_symbol[:-len(suf)]
    if mt5_symbol.startswith('#'):
        mt5_symbol = mt5_symbol[1:]
    return mt5_symbol


# ─────────────────────────────────────────────────────────────────────────────
# MT5 CONNECTOR
# ─────────────────────────────────────────────────────────────────────────────

class MT5Connector:
    """
    Conector principal para MetaTrader 5.
    
    Uso:
        connector = MT5Connector()
        connector.connect(login=12345, password="xxx", server="AdmiralMarkets-Demo")
        info = connector.get_account_info()
        result = connector.place_order("AAPL", "BUY", volume=0.1, sl=145.0, tp=160.0)
        connector.disconnect()
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self._connected = False
        self._config = self._load_config(config_path)
        self._symbol_suffix = self._config.get('symbol_suffix', '.US')
        self._paper_mode = self._config.get('paper_mode', True)
        
        if self._paper_mode:
            logger.info(f"{LogEmoji.INFO} Modo PAPER TRADE activo — no se enviarán órdenes reales")
    
    def _load_config(self, config_path: str) -> dict:
        """Carga configuración del broker desde settings.yaml."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get('broker', {})
        except Exception:
            return {}
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def paper_mode(self) -> bool:
        return self._paper_mode
    
    # ─────────────────────────────────────────────────────────────────────
    # CONEXIÓN
    # ─────────────────────────────────────────────────────────────────────
    
    def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        terminal_path: Optional[str] = None,
    ) -> bool:
        """
        Conecta al terminal MT5 y autentica con la cuenta.
        
        Prioridad de credenciales:
        1. Parámetros directos  
        2. Variables de entorno (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
        3. config/settings.yaml
        """
        if not MT5_AVAILABLE:
            logger.error(f"{LogEmoji.LOSS} MetaTrader5 no disponible")
            return False
        
        # Resolver credenciales
        _login = login or int(os.environ.get('MT5_LOGIN', self._config.get('login', 0)))
        _password = password or os.environ.get('MT5_PASSWORD', self._config.get('password', ''))
        _server = server or os.environ.get('MT5_SERVER', self._config.get('server', ''))
        _path = terminal_path or self._config.get('terminal_path', '')
        
        # Inicializar terminal
        init_kwargs = {}
        if _path:
            init_kwargs['path'] = _path
        
        if not mt5.initialize(**init_kwargs):
            error = mt5.last_error()
            logger.error(f"{LogEmoji.LOSS} Error inicializando MT5: {error}")
            return False
        
        logger.info(f"{LogEmoji.SYNC} Terminal MT5 inicializado")
        
        # Login
        if _login and _password:
            login_kwargs = {'login': _login, 'password': _password}
            if _server:
                login_kwargs['server'] = _server
            
            if not mt5.login(**login_kwargs):
                error = mt5.last_error()
                logger.error(f"{LogEmoji.LOSS} Error de login: {error}")
                mt5.shutdown()
                return False
            
            logger.info(f"{LogEmoji.PROFIT} Login exitoso — Cuenta #{_login} @ {_server}")
        
        self._connected = True
        
        # Log cuenta info
        account = self.get_account_info()
        logger.info(
            f"{LogEmoji.MONEY} {account.company} | "
            f"Balance: {account.balance:.2f} {account.currency} | "
            f"Equity: {account.equity:.2f}"
        )
        
        return True
    
    def disconnect(self):
        """Cierra conexión con MT5."""
        if MT5_AVAILABLE and self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info(f"{LogEmoji.INFO} MT5 desconectado")
    
    # ─────────────────────────────────────────────────────────────────────
    # CONSULTAS
    # ─────────────────────────────────────────────────────────────────────
    
    def get_account_info(self) -> AccountInfo:
        """Obtiene información de la cuenta."""
        if not self._connected:
            return AccountInfo()
        
        info = mt5.account_info()
        if info is None:
            return AccountInfo()
        
        return AccountInfo(
            login=info.login,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level if info.margin_level else 0.0,
            profit=info.profit,
            currency=info.currency,
            server=info.server,
            company=info.company,
        )
    
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """
        Obtiene información de un símbolo.
        Acepta formato yfinance (AAPL) o MT5 (AAPL.US).
        """
        if not self._connected:
            return None
        
        mt5_sym = map_symbol_to_mt5(symbol, self._symbol_suffix)
        
        info = mt5.symbol_info(mt5_sym)
        if info is None:
            # Try without .US if it fails
            mt5_sym_alt = f"#{symbol.upper()}"
            info = mt5.symbol_info(mt5_sym_alt)
            if info is None:
                logger.warning(f"{LogEmoji.WARNING} Símbolo no encontrado (probado {mt5_sym} y {mt5_sym_alt})")
                return None
            mt5_sym = mt5_sym_alt
            
        # Asegurar que está visible en Market Watch
        if not info.visible:
            mt5.symbol_select(mt5_sym, True)
        
        return SymbolInfo(
            name=info.name,
            description=info.description,
            bid=info.bid,
            ask=info.ask,
            spread=info.spread,
            point=info.point,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            trade_mode=info.trade_mode,
            currency_profit=info.currency_profit,
        )
    
    def get_tick(self, symbol: str) -> Optional[Dict[str, float]]:
        """Obtiene precio bid/ask actual."""
        if not self._connected:
            return None
        
        info = self.get_symbol_info(symbol)
        if not info:
             return None
             
        # Extract the real mt5 symbol that was resolved inside get_symbol_info
        mt5_sym = info.name
        
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return None
        
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'time': datetime.fromtimestamp(tick.time),
        }
    
    def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """
        Obtiene posiciones abiertas.
        Si symbol es None, retorna todas las posiciones.
        """
        if not self._connected:
            return []
        
        if symbol:
            mt5_sym = map_symbol_to_mt5(symbol, self._symbol_suffix)
            positions = mt5.positions_get(symbol=mt5_sym)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            result.append(PositionInfo(
                ticket=pos.ticket,
                symbol=map_symbol_from_mt5(pos.symbol),
                type=pos.type,
                volume=pos.volume,
                price_open=pos.price_open,
                price_current=pos.price_current,
                sl=pos.sl,
                tp=pos.tp,
                profit=pos.profit,
                time=datetime.fromtimestamp(pos.time),
                comment=pos.comment,
            ))
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────
    # ÓRDENES
    # ─────────────────────────────────────────────────────────────────────
    
    def place_order(
        self,
        symbol: str,
        order_type: str,  # "BUY" o "SELL"
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "quant_system",
        max_slippage: int = 10,
    ) -> OrderResult:
        """
        Envía una orden de mercado.
        """
        info = self.get_symbol_info(symbol)
        if not info:
             return OrderResult(success=False, comment=f"Símbolo no encontrado: {symbol}")
        
        mt5_sym = info.name
        
        # Paper mode
        if self._paper_mode:
            tick = self.get_tick(symbol) if self._connected else None
            price = tick['ask'] if tick and order_type == "BUY" else (tick['bid'] if tick else 0.0)
            logger.info(
                f"{LogEmoji.ENTRY} [PAPER] {order_type} {volume:.2f} lotes de {mt5_sym} "
                f"@ {price:.5f} | SL={sl:.5f} TP={tp:.5f}"
            )
            return OrderResult(success=True, volume=volume, price=price, comment="PAPER_ORDER")
        
        if not self._connected:
            return OrderResult(success=False, comment="No conectado a MT5")
        
        # Obtener precio actual
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return OrderResult(success=False, comment=f"No se pudo obtener precio de {mt5_sym}")
        
        price = tick.ask if order_type == "BUY" else tick.bid
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_sym,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": max_slippage,
            "magic": 234000,  # ID del sistema
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        logger.info(
            f"{LogEmoji.ENTRY} Enviando {order_type} {volume:.2f} lotes {mt5_sym} "
            f"@ {price:.5f} | SL={sl:.5f} TP={tp:.5f}"
        )
        
        result = mt5.order_send(request)
        
        if result is None:
            error = mt5.last_error()
            logger.error(f"{LogEmoji.LOSS} Error enviando orden: {error}")
            return OrderResult(success=False, comment=str(error))
        
        success = result.retcode == mt5.TRADE_RETCODE_DONE
        
        if success:
            logger.info(
                f"{LogEmoji.PROFIT} Orden ejecutada — Ticket #{result.order} | "
                f"{volume:.2f} lotes @ {result.price:.5f}"
            )
        else:
            logger.error(
                f"{LogEmoji.LOSS} Orden rechazada — retcode={result.retcode} | "
                f"{result.comment}"
            )
        
        return OrderResult(
            success=success,
            ticket=result.order,
            volume=result.volume,
            price=result.price,
            comment=result.comment,
            retcode=result.retcode,
        )
    
    def close_position(self, ticket: int) -> OrderResult:
        """Cierra una posición por su ticket."""
        if self._paper_mode:
            logger.info(f"{LogEmoji.EXIT} [PAPER] Cerrando posición #{ticket}")
            return OrderResult(success=True, ticket=ticket, comment="PAPER_CLOSE")
        
        if not self._connected:
            return OrderResult(success=False, comment="No conectado")
        
        # Buscar la posición
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResult(success=False, comment=f"Posición #{ticket} no encontrada")
        
        pos = positions[0]
        
        # Orden inversa para cerrar
        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == 0 else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "quant_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None:
            return OrderResult(success=False, comment=str(mt5.last_error()))
        
        success = result.retcode == mt5.TRADE_RETCODE_DONE
        
        if success:
            logger.info(f"{LogEmoji.EXIT} Posición #{ticket} cerrada @ {result.price:.5f}")
        else:
            logger.error(f"{LogEmoji.LOSS} Error cerrando #{ticket}: {result.comment}")
        
        return OrderResult(
            success=success,
            ticket=result.order,
            price=result.price,
            comment=result.comment,
            retcode=result.retcode,
        )
    
    def modify_position(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """
        Modifica SL/TP de una posición abierta.
        Usado para trailing stop.
        """
        if self._paper_mode:
            logger.info(f"{LogEmoji.SYNC} [PAPER] Modificando #{ticket} SL={sl:.5f} TP={tp:.5f}")
            return True
        
        if not self._connected:
            return False
        
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        pos = positions[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl if sl > 0 else pos.sl,
            "tp": tp if tp > 0 else pos.tp,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"{LogEmoji.SYNC} SL/TP actualizado para #{ticket}")
            return True
        
        logger.warning(f"{LogEmoji.WARNING} Error modificando #{ticket}")
        return False
    
    # ─────────────────────────────────────────────────────────────────────
    # CONTEXT MANAGER
    # ─────────────────────────────────────────────────────────────────────
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
