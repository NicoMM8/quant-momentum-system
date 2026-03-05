# =============================================================================
# EVENTS.PY - SISTEMA DE EVENTOS DEL TRADING
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo define los "eventos" que ocurren en el sistema de trading.
# Un evento es como un "mensaje" que una parte del sistema envía a otras
# partes para informar que algo pasó.
#
# ¿POR QUÉ USAMOS EVENTOS?
# -------------------------
# En un sistema de trading hay muchas cosas pasando simultáneamente:
# - Llegan nuevos datos de precios cada segundo
# - Las estrategias generan señales de compra/venta
# - Se ejecutan órdenes en el mercado
#
# Los eventos permiten que cada parte del sistema funcione de forma
# independiente pero coordinada, como músicos en una orquesta.
#
# ANALOGÍA SIMPLE:
# ----------------
# Imagina una cocina de restaurante:
# - El mesero grita "¡Orden de pasta!" (EVENT: Nueva Orden)
# - El chef recibe el mensaje y empieza a cocinar
# - Cuando termina, grita "¡Pasta lista!" (EVENT: Orden Completada)
# - El mesero la recoge y la lleva a la mesa
#
# Nadie necesita saber exactamente qué hace el otro, solo responden
# a los eventos/mensajes que les corresponden.
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

from dataclasses import dataclass, field
# 'dataclass' es un decorador de Python que simplifica la creación de clases
# que principalmente almacenan datos. Automáticamente genera:
# - __init__: Constructor para crear objetos
# - __repr__: Representación en texto del objeto
# - __eq__: Comparación entre objetos
#
# 'field' permite personalizar cómo se inicializan los atributos

from typing import Any
# 'Any' significa que el valor puede ser de cualquier tipo

import pandas as pd
# Pandas: Librería para trabajar con datos en tablas

from datetime import datetime
# datetime: Para trabajar con fechas y horas


# =============================================================================
# CLASE BASE: Event (Evento)
# =============================================================================

@dataclass  # Este decorador convierte la clase en una "dataclass"
class Event:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                         EVENTO BASE                                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta es la clase PADRE de todos los eventos del sistema.                 ║
    ║  Todos los tipos de eventos heredan de aquí.                              ║
    ║                                                                           ║
    ║  Es como una "plantilla" básica que dice:                                 ║
    ║  "Todo evento DEBE tener: un tipo, una hora, y datos adicionales"         ║
    ║                                                                           ║
    ║  ATRIBUTOS (datos que guarda cada evento):                                ║
    ║  ─────────────────────────────────────────                                ║
    ║  • type (str): El tipo de evento                                          ║
    ║    Ejemplos: 'MARKET_DATA', 'SIGNAL', 'ORDER', 'FILL'                     ║
    ║                                                                           ║
    ║  • timestamp (datetime): Cuándo ocurrió el evento                         ║
    ║    Ejemplo: 2024-01-15 09:30:00.123456                                    ║
    ║                                                                           ║
    ║  • payload (Any): Información adicional del evento                        ║
    ║    Puede ser cualquier cosa: un número, texto, diccionario, etc.          ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # -------------------------------------------------------------------------
    # ATRIBUTO 1: type (tipo de evento)
    # -------------------------------------------------------------------------
    type: str
    # Ejemplos de tipos:
    # - 'MARKET_DATA' = Llegaron nuevos datos de precios
    # - 'SIGNAL' = Una estrategia generó una señal de compra/venta
    # - 'ORDER' = Se creó una orden para ejecutar
    # - 'FILL' = Una orden se ejecutó en el mercado
    
    # -------------------------------------------------------------------------
    # ATRIBUTO 2: timestamp (marca de tiempo)
    # -------------------------------------------------------------------------
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # 'default_factory=datetime.utcnow' significa:
    # "Si no me das una hora, usa la hora actual automáticamente"
    #
    # datetime.utcnow() retorna la hora en formato UTC (hora universal)
    # Ejemplo: 2024-01-15 14:30:00.123456
    #
    # ¿Por qué UTC? Porque los mercados están en diferentes zonas horarias.
    # Usar UTC evita confusiones: NYSE (Nueva York), LSE (Londres), TSE (Tokio)
    
    # -------------------------------------------------------------------------
    # ATRIBUTO 3: payload (carga de datos)
    # -------------------------------------------------------------------------
    payload: Any = None
    # 'payload' viene del inglés "carga útil"
    # Es información adicional que el evento puede llevar
    # 
    # El valor por defecto es None (nada)
    #
    # Ejemplos de payload según el tipo de evento:
    # - MARKET_DATA: Los datos de precios OHLCV
    # - SIGNAL: La intensidad de la señal (ej: 0.75)
    # - ORDER: Detalles de la orden (símbolo, cantidad, precio)


# =============================================================================
# EVENTO ESPECIALIZADO: MarketDataEvent (Evento de Datos de Mercado)
# =============================================================================

@dataclass
class MarketDataEvent(Event):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    EVENTO DE DATOS DE MERCADO                             ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Este evento se dispara cada vez que llegan nuevos datos de precios.      ║
    ║                                                                           ║
    ║  CUÁNDO SE GENERA:                                                        ║
    ║  - Cada segundo/minuto cuando el mercado está abierto                     ║
    ║  - Cuando se descargan datos históricos                                   ║
    ║                                                                           ║
    ║  QUIÉN LO ESCUCHA:                                                        ║
    ║  - Las estrategias (para analizar y generar señales)                      ║
    ║  - El dashboard (para mostrar gráficos actualizados)                      ║
    ║  - El motor de backtesting (para simular trading histórico)               ║
    ║                                                                           ║
    ║  CONTENIDO:                                                               ║
    ║  - symbol: Qué acción (ej: 'AAPL', 'TSLA')                                ║
    ║  - data: Tabla con precios OHLCV (Open, High, Low, Close, Volume)         ║
    ║                                                                           ║
    ║  EJEMPLO DE USO:                                                          ║
    ║  ───────────────                                                          ║
    ║  # Crear un evento cuando llegan datos de Apple                           ║
    ║  evento = MarketDataEvent(symbol='AAPL', data=precios_apple)              ║
    ║  # Ahora el sistema puede reaccionar a estos nuevos datos                 ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # -------------------------------------------------------------------------
    # ATRIBUTO: symbol (símbolo bursátil)
    # -------------------------------------------------------------------------
    symbol: str = ""
    # El "ticker" o símbolo de la acción
    # Ejemplos:
    # - 'AAPL' = Apple Inc.
    # - 'MSFT' = Microsoft Corporation
    # - 'TSLA' = Tesla Inc.
    # - 'GOOGL' = Alphabet (Google)
    # - 'SPY' = ETF que replica el S&P 500
    
    # -------------------------------------------------------------------------
    # ATRIBUTO: data (datos de mercado)
    # -------------------------------------------------------------------------
    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    # Un DataFrame de pandas que contiene los datos de precios
    #
    # 'default_factory=pd.DataFrame' significa:
    # "Si no me das datos, crea un DataFrame vacío"
    #
    # ESTRUCTURA TÍPICA DEL DATAFRAME:
    # ┌────────────────────┬────────┬────────┬────────┬────────┬─────────┐
    # │      datetime      │  open  │  high  │  low   │ close  │ volume  │
    # ├────────────────────┼────────┼────────┼────────┼────────┼─────────┤
    # │ 2024-01-15 09:30   │ 150.00 │ 150.50 │ 149.80 │ 150.25 │  50000  │
    # │ 2024-01-15 09:31   │ 150.25 │ 150.75 │ 150.10 │ 150.60 │  45000  │
    # │ 2024-01-15 09:32   │ 150.60 │ 151.00 │ 150.50 │ 150.90 │  60000  │
    # └────────────────────┴────────┴────────┴────────┴────────┴─────────┘
    #
    # EXPLICACIÓN DE COLUMNAS:
    # - open: Precio al ABRIR el período (la primera transacción)
    # - high: Precio más ALTO durante el período
    # - low: Precio más BAJO durante el período
    # - close: Precio al CERRAR el período (la última transacción)
    # - volume: Cantidad de acciones intercambiadas

    def __post_init__(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                          __POST_INIT__                                  │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Este método especial se ejecuta AUTOMÁTICAMENTE después de crear      │
        │  el objeto. Es como un "segundo constructor".                          │
        │                                                                         │
        │  Lo usamos para establecer el tipo de evento automáticamente.           │
        │  Así no tenemos que escribir type='MARKET_DATA' cada vez.               │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        self.type = 'MARKET_DATA'
        # Establecemos automáticamente que este evento es de tipo 'MARKET_DATA'


# =============================================================================
# EVENTO ESPECIALIZADO: SignalEvent (Evento de Señal de Trading)
# =============================================================================

@dataclass
class SignalEvent(Event):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                      EVENTO DE SEÑAL DE TRADING                           ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Este evento se dispara cuando una estrategia detecta una oportunidad.    ║
    ║                                                                           ║
    ║  CUÁNDO SE GENERA:                                                        ║
    ║  - Cuando la estrategia macro encuentra acciones subvaloradas             ║
    ║  - Cuando la estrategia técnica detecta un cruce de medias móviles        ║
    ║  - Cuando la estrategia micro ve presión compradora en el order book      ║
    ║                                                                           ║
    ║  QUIÉN LO ESCUCHA:                                                        ║
    ║  - El gestor de posiciones (para decidir si ejecutar la operación)        ║
    ║  - El módulo de riesgo (para verificar límites de exposición)             ║
    ║  - El logger (para registrar las señales generadas)                       ║
    ║                                                                           ║
    ║  LA FUERZA DE LA SEÑAL:                                                   ║
    ║  ──────────────────────                                                   ║
    ║     -1.0          0.0          +1.0                                       ║
    ║       │            │             │                                        ║
    ║       ▼            ▼             ▼                                        ║
    ║   ¡VENDE!      NEUTRAL      ¡COMPRA!                                      ║
    ║    AHORA      (esperar)      AHORA                                        ║
    ║                                                                           ║
    ║  EJEMPLO DE SEÑALES:                                                      ║
    ║  - +0.85: "El RSI indica sobreventa y hay cruce alcista. ¡Compra fuerte!" ║
    ║  - +0.30: "Hay algo de momentum positivo, pero no es muy claro"           ║
    ║  -  0.00: "No hay señal, el mercado está lateral"                         ║
    ║  - -0.60: "El precio rompió soporte importante, considera vender"         ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # -------------------------------------------------------------------------
    # ATRIBUTO: symbol (símbolo de la acción)
    # -------------------------------------------------------------------------
    symbol: str = ""
    # ¿Para qué acción es esta señal?
    # Ejemplo: 'AAPL', 'TSLA', 'NVDA'
    
    # -------------------------------------------------------------------------
    # ATRIBUTO: signal_strength (fuerza de la señal)
    # -------------------------------------------------------------------------
    signal_strength: float = 0.0
    # La intensidad y dirección de la señal
    #
    # RANGO: De -1.0 a +1.0
    #
    # INTERPRETACIÓN:
    # ─────────────────────────────────────────────────────────────
    # │ Valor        │ Significado         │ Acción Sugerida     │
    # ─────────────────────────────────────────────────────────────
    # │ +0.8 a +1.0  │ Señal muy fuerte    │ Comprar con tamaño  │
    # │ +0.4 a +0.8  │ Señal moderada      │ Comprar conservador │
    # │ +0.0 a +0.4  │ Señal débil         │ Quizás esperar      │
    # │ -0.0 a -0.4  │ Señal débil bajista │ Quizás esperar      │
    # │ -0.4 a -0.8  │ Señal moderada      │ Vender/reducir      │
    # │ -0.8 a -1.0  │ Señal muy fuerte    │ Vender todo         │
    # ─────────────────────────────────────────────────────────────
    
    # -------------------------------------------------------------------------
    # ATRIBUTO: strategy_id (identificador de la estrategia)
    # -------------------------------------------------------------------------
    strategy_id: str = ""
    # ¿Qué estrategia generó esta señal?
    #
    # Ejemplos:
    # - 'macro_scanner_v1' = Estrategia fundamental Capa 1
    # - 'technical_momentum' = Estrategia técnica de momentum
    # - 'orderflow_micro' = Estrategia de microestructura
    # - 'golden_cross_daily' = Cruce de medias móviles diario
    #
    # ¿Por qué es útil?
    # - Para saber qué tan confiable es la señal (algunas estrategias funcionan mejor)
    # - Para debugging: si algo sale mal, sabemos qué estrategia fue
    # - Para estadísticas: cuántas señales genera cada estrategia

    def __post_init__(self):
        """
        Método que se ejecuta automáticamente después de crear el objeto.
        Establece el tipo de evento como 'SIGNAL'.
        """
        self.type = 'SIGNAL'


# =============================================================================
# NOTAS ADICIONALES PARA DESARROLLADORES
# =============================================================================
#
# CÓMO CREAR NUEVOS TIPOS DE EVENTOS:
# -----------------------------------
# 1. Crea una nueva clase que herede de Event
# 2. Añade los atributos específicos que necesites
# 3. Implementa __post_init__ para establecer el tipo
#
# EJEMPLO:
# @dataclass
# class OrderEvent(Event):
#     symbol: str = ""
#     quantity: int = 0
#     order_type: str = "MARKET"  # o "LIMIT"
#     price: float = 0.0
#     
#     def __post_init__(self):
#         self.type = 'ORDER'
#
# =============================================================================