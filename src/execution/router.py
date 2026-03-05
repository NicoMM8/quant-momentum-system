"""
═══════════════════════════════════════════════════════════════════════════════
  ORDER ROUTER
  
  Puente entre la Estrategia (Señales) y la Ejecución (OMS).
  - Recibe SignalEvent
  - Calcula tamaño de posición (PositionSizer)
  - Decide si es ENTRY o EXIT
  - Envía instrucciones al OMS
═══════════════════════════════════════════════════════════════════════════════
"""

from src.core.events import SignalEvent
from src.execution.oms import OrderManagementSystem
from src.strategies.risk import PositionSizer, RiskParameters
from src.utils.logger import get_logger, LogEmoji

logger = get_logger("router")

class OrderRouter:
    """
    Enrutador de Órdenes Inteligente.
    Convierte señales abstractas (0.0 a 1.0) en órdenes concretas (lotes).
    """
    
    def __init__(self, oms: OrderManagementSystem, position_sizer: PositionSizer):
        self.oms = oms
        self.sizer = position_sizer
        self.min_signal_strength = 0.5  # Mínima fuerza para entrar
        
    def on_signal(self, signal: SignalEvent, current_capital: float = 10000.0):
        """
        Procesa una nueva señal de trading.
        """
        symbol = signal.symbol
        strength = signal.signal_strength
        
        logger.info(f"{LogEmoji.INFO} Procesando señal: {symbol} S={strength:.2f}")
        
        # 1. Verificar si ya tenemos posición en este símbolo
        # (El OMS sabe, pero el Router debería decidir si añadir o cerrar)
        # Por simplificación: Si señal opuesta fuerte -> CERRAR. Si señal igual -> NADA (o Pyramiding).
        # Asumimos MODO SIMPLE: 1 Posición por símbolo.
        
        # Buscar posición existente (por ticket, pero necesitamos mapear symbol->ticket)
        # El OMS tiene active_positions dict[ticket, info].
        existing_ticket = None
        existing_pos = None
        
        for ticket, pos in self.oms.active_positions.items():
            # Mapeo inverso de MT5 symbol a app symbol ya hecho en connector?
            # Connector devuelve PositionInfo con symbol limpio.
            if pos.symbol == symbol:
                existing_ticket = ticket
                existing_pos = pos
                break
        
        # 2. Lógica de Salida (Signal opuesta o débil)
        # Si strength baja de umbral o cambia de signo -> Cerrar
        # Aquí asumimos que SignalEvent llega periódicamente.
        # Si strength es 0 -> Neutral (Cerrar si existe)
        
        if existing_pos:
            # Si tenemos posición LONG y señal se vuelve negativa/neutral
            if existing_pos.type == 0: # BUY
                if strength < 0.2: # Umbral de salida
                    logger.info(f"{LogEmoji.EXIT} Señal debilitada ({strength:.2f}). Cerrando LONG {symbol}")
                    self.oms.close_position(existing_ticket)
                    return

            # Si tenemos posición SHORT y señal se vuelve positiva (no implementado short aun, pero por simetria)
            elif existing_pos.type == 1: # SELL
                 if strength > -0.2:
                    logger.info(f"{LogEmoji.EXIT} Señal debilitada ({strength:.2f}). Cerrando SHORT {symbol}")
                    self.oms.close_position(existing_ticket)
                    return
            
            # Si la señal confirma la dirección, mantenemos (no pyramiding por ahora)
            return

        # 3. Lógica de Entrada (Nueva posición)
        if abs(strength) < self.min_signal_strength:
            return  # Señal muy débil
            
        direction = "BUY" if strength > 0 else "SELL"
        
        # Calcular tamaño (Size)
        # Usamos PositionSizer
        # Necesitamos precio actual para calcular lotes
        tick = self.oms.connector.get_tick(symbol)
        if not tick:
            logger.warning(f"No tic price for {symbol}")
            return
            
        price = tick['ask'] if direction == "BUY" else tick['bid']
        
        # Risk % base: 1% * fuerza de señal
        # Ej: Señal 0.8 -> Arriesgamos 0.8% del capital
        risk_pct = 0.01 * abs(strength) 
        
        # SL distance (técnico o fijo). 
        # Por ahora fijo: 1.5% (hardcoded en router o sacado de config)
        # Mejor: usaremos el ATR si estuviera disponible, o un % fijo del precio
        sl_dist_pct = 0.015 
        sl_price = price * (1 - sl_dist_pct) if direction == "BUY" else price * (1 + sl_dist_pct)
        tp_price = price * (1 + (sl_dist_pct * 2)) if direction == "BUY" else price * (1 - (sl_dist_pct * 2))
        
        # Calcular lotes
        # Capital * Risk% / (Price - SL)  <- formula basica
        # PositionSizer.fixed_percentage calcula el monto en $ a arriesgar o la posicion entera?
        # Revisemos risk.py: fixed_percentage devuelve "position_value" (monto total de la posicion)
        
        target_pos_value = self.sizer.fixed_percentage(current_capital, risk_pct=None) # Usa default del config
        # Ajustar por fuerza de señal? Sizer ya lo hace si le pasamos params custom, pero risk.py lee de config.
        # Asumamos Sizer da el tamaño máximo seguro. Modulamos por fuerza de señal.
        target_pos_value = target_pos_value * abs(strength)
        
        # Convertir valor $ a Lotes
        # Lotes = Valor / (Precio * ContractSize)
        # Asumimos ContractSize = 1 para US Stocks (en Admiral suele ser 1 CFDs o Stocks)
        # Para Forex es 100,000.
        # Necesitamos symbol_info para saber contract size (volume_min/step no lo dicen).
        # Connector get_symbol_info da point, pero no contract_size explícito (wrapper simple).
        # Asumamos 1 para Stocks por ahora.
        
        if target_pos_value <= 0: return
        
        volume = target_pos_value / price
        
        # Redondear a step de volumen (ej 0.01 o 1)
        # Sym info
        sym_info = self.oms.connector.get_symbol_info(symbol)
        if sym_info:
            step = sym_info.volume_step
            if step > 0:
                volume = round(volume / step) * step
                # Min check
                if volume < sym_info.volume_min:
                    logger.info(f"Volumen calculado ({volume}) menor al mínimo ({sym_info.volume_min})")
                    return
        
        # Enviar orden
        logger.info(f"{LogEmoji.ENTRY} Señal {direction} detectada. Ordenando {volume:.2f} lotes {symbol}")
        self.oms.submit_order(symbol, direction, volume, sl_price, tp_price)
