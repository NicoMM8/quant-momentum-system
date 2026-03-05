# =============================================================================
# LOGGER.PY - SISTEMA DE LOGGING PROFESIONAL
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo implementa un sistema de "logging" (registro de eventos)
# profesional que reemplaza los print() dispersos por el código.
#
# ¿QUÉ ES LOGGING?
# ----------------
# Logging es como llevar un "diario" de todo lo que hace el programa:
# - Qué decisiones tomó
# - Qué errores encontró
# - Qué información procesó
#
# Es ESENCIAL para:
# 1. DEBUGGING: Encontrar y arreglar errores
# 2. MONITOREO: Ver qué está haciendo el sistema en tiempo real
# 3. AUDITORÍA: Revisar qué pasó después de un problema
# 4. ANÁLISIS: Estudiar el comportamiento del sistema
#
# ¿POR QUÉ NO USAR SOLO print()?
# -------------------------------
# print() tiene muchas limitaciones:
#
# | Característica        | print()    | logging        |
# |----------------------|------------|----------------|
# | Guardar en archivo   | ❌ Manual  | ✅ Automático   |
# | Niveles de urgencia  | ❌ No      | ✅ DEBUG/INFO/ERROR |
# | Desactivar mensajes  | ❌ Difícil | ✅ Fácil        |
# | Hora y fecha         | ❌ Manual  | ✅ Automático   |
# | Colores en terminal  | ❌ No      | ✅ Con colorlog |
# | Saber de dónde viene | ❌ Manual  | ✅ Automático   |
#
# EJEMPLO DE SALIDA DE LOGGING:
# 2024-01-15 09:30:15 | INFO     | quant_system | 🚀 ENTRY LONG @ AAPL 150.25
# 2024-01-15 09:31:02 | WARNING  | quant_system | ⚠️ Volumen bajo detectado
# 2024-01-15 09:32:45 | ERROR    | quant_system | ❌ Conexión a API fallida
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

import logging
# 'logging' es el módulo estándar de Python para registro de eventos
# Viene incluido con Python, no necesitas instalarlo

import sys
# 'sys' proporciona acceso a variables del sistema
# sys.stdout = la "consola" donde se imprime texto

from typing import Optional
# Optional = puede ser un tipo específico O None
# Optional[str] significa "str o None"

from datetime import datetime
# datetime para trabajar con fechas y horas

import os
# os para operaciones del sistema operativo (crear carpetas, etc.)

# -----------------------------------------------------------------------------
# IMPORTACIÓN OPCIONAL: colorlog
# -----------------------------------------------------------------------------

try:
    import colorlog
    # colorlog permite mostrar los mensajes de log en colores
    # INFO = verde, WARNING = amarillo, ERROR = rojo
    COLORLOG_AVAILABLE = True
except ImportError:
    # Si colorlog no está instalado, seguimos sin colores
    # type: ignore
    colorlog = None  # type: ignore
    COLORLOG_AVAILABLE = False


# =============================================================================
# CLASE: TradingLogger (Logger de Trading)
# =============================================================================

class TradingLogger:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    SISTEMA DE LOGGING CENTRALIZADO                        ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase proporciona un sistema de logging profesional con:            ║
    ║                                                                           ║
    ║  CARACTERÍSTICAS:                                                         ║
    ║  ─────────────────                                                        ║
    ║  • Colores en terminal (si colorlog está instalado)                       ║
    ║  • Guardado automático en archivos .log                                   ║
    ║  • Diferentes niveles de urgencia (DEBUG, INFO, WARNING, ERROR)           ║
    ║  • Formato consistente con fecha, hora y origen del mensaje               ║
    ║  • Patrón Singleton (una sola instancia en toda la app)                   ║
    ║                                                                           ║
    ║  NIVELES DE LOGGING:                                                      ║
    ║  ─────────────────────                                                    ║
    ║                                                                           ║
    ║  │ Nivel    │ Uso                                         │ Color    │   ║
    ║  ├──────────┼─────────────────────────────────────────────┼──────────┤   ║
    ║  │ DEBUG    │ Info detallada para debugging               │ Cyan     │   ║
    ║  │ INFO     │ Confirmaciones de que todo funciona         │ Verde    │   ║
    ║  │ WARNING  │ Algo inesperado pero no crítico             │ Amarillo │   ║
    ║  │ ERROR    │ Algo falló, pero el sistema puede continuar │ Rojo     │   ║
    ║  │ CRITICAL │ Error muy grave, posible crash              │ Rojo/BG  │   ║
    ║                                                                           ║
    ║  EJEMPLO DE USO:                                                          ║
    ║  ─────────────────                                                        ║
    ║  from src.utils.logger import get_logger                                  ║
    ║  logger = get_logger(__name__)                                            ║
    ║                                                                           ║
    ║  logger.debug("Procesando datos...")     # Solo visible en modo debug    ║
    ║  logger.info("Trade ejecutado OK")       # Información normal            ║
    ║  logger.warning("Volumen muy bajo")      # Advertencia                   ║
    ║  logger.error("No se pudo conectar")     # Error                         ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # =========================================================================
    # VARIABLES DE CLASE (Singleton)
    # =========================================================================
    
    _instance: Optional['TradingLogger'] = None
    # La única instancia del logger
    # Optional['TradingLogger'] significa "TradingLogger o None"
    
    _initialized: bool = False
    # Flag para saber si ya inicializamos el logger
    # Evita reinicializar cada vez que alguien pide el logger
    
    # =========================================================================
    # MÉTODO ESPECIAL: __new__ (Patrón Singleton)
    # =========================================================================
    
    def __new__(cls, *args, **kwargs):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                              __NEW__                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Implementa el patrón Singleton: garantiza una sola instancia.          │
        │                                                                         │
        │  Sin importar cuántas veces llames TradingLogger(), siempre             │
        │  recibirás la MISMA instancia.                                          │
        │                                                                         │
        │  ¿Por qué es útil?                                                      │
        │  - Todos los módulos comparten el mismo logger                          │
        │  - Un solo archivo de log, no muchos                                    │
        │  - Configuración centralizada                                           │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        if cls._instance is None:
            # Primera vez: crear la instancia
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # =========================================================================
    # CONSTRUCTOR: __init__
    # =========================================================================
    
    def __init__(
        self, 
        name: str = "quant_system",
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_dir: str = "logs"
    ):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                             __INIT__                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Configura el sistema de logging.                                       │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  ─────────────                                                          │
        │  • name: Nombre del logger (aparece en cada mensaje)                    │
        │    Ejemplo: "quant_system" → [quant_system] mensaje...                  │
        │                                                                         │
        │  • level: Nivel mínimo de mensajes a mostrar                            │
        │    - logging.DEBUG = mostrar TODO (incluso debug)                       │
        │    - logging.INFO = mostrar INFO y más graves                           │
        │    - logging.WARNING = solo warnings y errores                          │
        │    - logging.ERROR = solo errores                                       │
        │                                                                         │
        │  • log_to_file: ¿Guardar mensajes en archivo?                           │
        │    True = crea archivo en carpeta logs/                                 │
        │                                                                         │
        │  • log_dir: Carpeta donde guardar los archivos de log                   │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # Evitar reinicialización (por el patrón Singleton)
        if TradingLogger._initialized:
            return
        
        # Guardar configuración
        self.name = name
        self.level = level
        self.log_dir = log_dir
        
        # ─────────────────────────────────────────────────────────────────────
        # CREAR DIRECTORIO DE LOGS
        # ─────────────────────────────────────────────────────────────────────
        if log_to_file and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            # os.makedirs() crea la carpeta, incluyendo carpetas padre si faltan
        
        # ─────────────────────────────────────────────────────────────────────
        # CONFIGURAR LOGGER
        # ─────────────────────────────────────────────────────────────────────
        
        self.logger = logging.getLogger(name)
        # logging.getLogger() obtiene (o crea) un logger con ese nombre
        
        self.logger.setLevel(level)
        # setLevel() define qué mensajes se procesan
        # Los mensajes con nivel menor se ignoran
        
        self.logger.handlers = []
        # Limpiar handlers existentes para evitar duplicados
        # Un "handler" es el destino de los mensajes (consola, archivo, etc.)
        
        # ─────────────────────────────────────────────────────────────────────
        # FORMATO DE MENSAJES
        # ─────────────────────────────────────────────────────────────────────
        
        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        # %(asctime)s = fecha y hora
        # %(levelname)-8s = nivel (INFO, ERROR, etc.) en 8 caracteres
        # %(name)s = nombre del logger
        # %(message)s = el mensaje en sí
        #
        # Ejemplo de salida:
        # 2024-01-15 09:30:15 | INFO     | quant_system | Trade ejecutado
        
        date_format = "%Y-%m-%d %H:%M:%S"
        # Formato de fecha: 2024-01-15 09:30:15
        
        # ─────────────────────────────────────────────────────────────────────
        # HANDLER DE CONSOLA (muestra mensajes en terminal)
        # ─────────────────────────────────────────────────────────────────────
        
        console_handler = logging.StreamHandler(sys.stdout)
        # StreamHandler envía los mensajes a un "stream" (flujo)
        # sys.stdout = la consola/terminal
        
        console_handler.setLevel(level)
        
        # Configurar colores si colorlog está disponible
        if COLORLOG_AVAILABLE:
            # Formatter con colores
            color_format = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'cyan',      # Cyan para debug
                    'INFO': 'green',      # Verde para info
                    'WARNING': 'yellow',  # Amarillo para warnings
                    'ERROR': 'red',       # Rojo para errores
                    'CRITICAL': 'red,bg_white',  # Rojo con fondo blanco para críticos
                }
            )
            console_handler.setFormatter(color_format)
        else:
            # Formatter sin colores
            console_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Agregar el handler de consola al logger
        self.logger.addHandler(console_handler)
        
        # ─────────────────────────────────────────────────────────────────────
        # HANDLER DE ARCHIVO (guarda mensajes en archivo .log)
        # ─────────────────────────────────────────────────────────────────────
        
        if log_to_file:
            # Crear nombre de archivo con fecha/hora actual
            log_filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
            # Ejemplo: 20240115_093015.log
            
            file_handler = logging.FileHandler(
                os.path.join(log_dir, log_filename),
                encoding='utf-8'
            )
            # FileHandler guarda mensajes en un archivo
            # encoding='utf-8' permite emojis y caracteres especiales
            
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            
            self.logger.addHandler(file_handler)
        
        # Marcar como inicializado
        TradingLogger._initialized = True
    
    # =========================================================================
    # MÉTODO: get_logger (Obtener Logger para un Módulo)
    # =========================================================================
    
    def get_logger(self, module_name: str = None) -> logging.Logger:
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                           GET_LOGGER                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Obtiene un logger para un módulo específico.                           │
        │                                                                         │
        │  ¿Por qué usar loggers por módulo?                                      │
        │  Permite saber EXACTAMENTE de dónde viene cada mensaje.                 │
        │                                                                         │
        │  EJEMPLO:                                                               │
        │  logger = get_logger("execution.trade_manager")                         │
        │  logger.info("Trade ejecutado")                                         │
        │                                                                         │
        │  SALIDA:                                                                │
        │  ... | INFO | quant_system.execution.trade_manager | Trade ejecutado    │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  • module_name: Nombre del módulo (usa __name__ normalmente)            │
        │                                                                         │
        │  RETORNA:                                                               │
        │  • Logger configurado para ese módulo                                   │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        if module_name:
            # Crear logger hijo con nombre combinado
            return logging.getLogger(f"{self.name}.{module_name}")
        return self.logger
    
    # =========================================================================
    # MÉTODO DE CLASE: reset (Reiniciar Singleton)
    # =========================================================================
    
    @classmethod  # @classmethod permite llamar sin crear instancia
    def reset(cls):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                              RESET                                      │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Reinicia el Singleton. Útil principalmente para tests.                 │
        │                                                                         │
        │  Después de llamar reset(), la próxima llamada a TradingLogger()        │
        │  creará una nueva instancia con nueva configuración.                    │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        cls._instance = None
        cls._initialized = False


# =============================================================================
# FUNCIÓN DE CONVENIENCIA: get_logger
# =============================================================================

def get_logger(module_name: str = None) -> logging.Logger:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    FUNCIÓN DE CONVENIENCIA                                ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta función hace más fácil obtener un logger desde cualquier archivo.   ║
    ║                                                                           ║
    ║  USO RECOMENDADO:                                                         ║
    ║  ─────────────────                                                        ║
    ║  from src.utils.logger import get_logger                                  ║
    ║  logger = get_logger(__name__)  # __name__ = nombre del módulo actual     ║
    ║                                                                           ║
    ║  logger.debug("Valor de x: %s", x)    # Solo en modo debug                ║
    ║  logger.info("Operación completada")  # Información general               ║
    ║  logger.warning("Algo no está bien")  # Advertencia                       ║
    ║  logger.error("Falló la conexión")    # Error                             ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    trading_logger = TradingLogger()
    return trading_logger.get_logger(module_name)


# =============================================================================
# CLASE: LogEmoji (Emojis para Mensajes de Trading)
# =============================================================================

class LogEmoji:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                       EMOJIS PARA LOGGING                                 ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Constantes con emojis para usar en mensajes de log.                      ║
    ║  Mantienen consistencia visual en toda la aplicación.                     ║
    ║                                                                           ║
    ║  USO:                                                                     ║
    ║  from src.utils.logger import LogEmoji                                    ║
    ║  logger.info(f"{LogEmoji.ENTRY} Entrada LONG @ 150.25")                   ║
    ║                                                                           ║
    ║  EMOJIS DISPONIBLES:                                                      ║
    ║  ─────────────────────                                                    ║
    ║  • ENTRY 🚀 = Entrada a posición                                          ║
    ║  • EXIT 🏁 = Salida de posición                                           ║
    ║  • PROFIT ✅ = Trade con ganancia                                         ║
    ║  • LOSS ❌ = Trade con pérdida                                            ║
    ║  • WARNING ⚠️ = Advertencia                                               ║
    ║  • INFO ℹ️ = Información                                                  ║
    ║  • SIGNAL_BUY 🟢 = Señal de compra                                        ║
    ║  • SIGNAL_SELL 🔴 = Señal de venta                                        ║
    ║  • SIGNAL_NEUTRAL ⚪ = Sin señal                                          ║
    ║  • DATABASE 💾 = Operación de base de datos                               ║
    ║  • SYNC 🔄 = Sincronización                                               ║
    ║  • CHART 📊 = Gráficos/análisis                                           ║
    ║  • MONEY 💰 = Relacionado con dinero/capital                              ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    ENTRY = "🚀"           # Cohete = entrada explosiva
    EXIT = "🏁"            # Bandera de meta = fin del trade
    PROFIT = "✅"          # Check verde = ganancia
    LOSS = "❌"            # X roja = pérdida
    WARNING = "⚠️"          # Triángulo amarillo = cuidado
    INFO = "ℹ️"             # Círculo azul = información
    SIGNAL_BUY = "🟢"      # Círculo verde = comprar
    SIGNAL_SELL = "🔴"     # Círculo rojo = vender
    SIGNAL_NEUTRAL = "⚪"   # Círculo blanco = esperar
    DATABASE = "💾"        # Disco = base de datos
    SYNC = "🔄"            # Flechas circulares = sincronizando
    CHART = "📊"           # Gráfico de barras = análisis
    MONEY = "💰"           # Bolsa de dinero = capital


# =============================================================================
# EJEMPLO DE USO COMPLETO
# =============================================================================
#
# from src.utils.logger import get_logger, LogEmoji
# 
# # Obtener logger para este módulo
# logger = get_logger(__name__)
# 
# # Diferentes niveles de mensajes
# logger.debug("Variables inicializadas")  # Solo visible si level=DEBUG
# logger.info(f"{LogEmoji.ENTRY} ENTRY LONG @ AAPL 150.25")
# logger.warning(f"{LogEmoji.WARNING} Volumen 20% bajo del promedio")
# logger.error(f"{LogEmoji.LOSS} Conexión a broker perdida")
# 
# # Los mensajes se guardan automáticamente en logs/YYYYMMDD_HHMMSS.log
#
# =============================================================================
