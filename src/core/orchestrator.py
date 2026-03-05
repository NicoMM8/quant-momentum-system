"""
═══════════════════════════════════════════════════════════════════════════════
  LIVE ORCHESTRATOR — CORAZÓN DEL SISTEMA
  
  Coordina todos los componentes:
  - Inicializa conexión con MT5
  - Ejecuta las 3 capas de estrategia (Macro, Técnica, Micro)
  - Gestiona ciclo de vida y cierre seguro
  - Envia señales al Router -> OMS -> Connector
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import signal
import sys
import os
import schedule
from datetime import datetime
import pandas as pd

# Core & Utils
from src.utils.logger import get_logger, LogEmoji
from src.data.ingestion import DataIngestor
from src.core.events import SignalEvent

# Execution
from src.execution.mt5_connector import MT5Connector
from src.execution.oms import OrderManagementSystem
from src.execution.router import OrderRouter

# Risk
from src.strategies.risk import PortfolioRiskManager, PositionSizer, RiskParameters

# Strategies
from src.strategies.alpha.macro import MacroScannerStrategy
from src.strategies.alpha.technical import TechnicalFilterStrategy
from src.strategies.alpha.micro import MicroStructureStrategy

logger = get_logger("orchestrator")

class LiveOrchestrator:
    def __init__(self, config_path: str = "config/settings.yaml"):
        logger.info("Inicializando Quant System Pro...")
        self.config_path = config_path
        self.running = False
        
        # 1. Componentes de Ejecución
        self.connector = MT5Connector(config_path)
        self.risk_manager = PortfolioRiskManager() # Carga default de config
        self.oms = OrderManagementSystem(self.connector, self.risk_manager)
        self.sizer = PositionSizer()
        self.router = OrderRouter(self.oms, self.sizer)
        
        # 2. Datos y Estrategias
        # Usamos DB temporal o persistente? Persistente.
        db_path = os.path.join(os.getcwd(), "data", "market_data.db")
        self.ingestor = DataIngestor(db_path, config_path)
        
        # Capas
        self.layer1_macro = MacroScannerStrategy(db_path)
        self.layer2_tech = TechnicalFilterStrategy(db_path)
        self.layer3_micro = MicroStructureStrategy(db_path)
        
        # Estado
        self.universe_l1 = [] # Salida de Macro
        self.universe_l2 = [] # Salida de Técnico (Inputs para Micro)
        
        # Configuración de loops
        self.last_l1_run = None
        self.last_l2_run = None

    def start(self):
        """Inicia el sistema completo."""
        self.running = True
        
        # Setup señales de cierre (Ctrl+C)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        try:
            # 1. Conectar Broker
            if not self.connector.connect():
                logger.error("Fallo crítico: No se pudo conectar a MT5. Abortando.")
                return

            # 2. Iniciar OMS
            self.oms.start()
            
            logger.info(f"{LogEmoji.CHART} Sistema INICIADO. Esperando ticks...")
            
            # 3. Schedule jobs (si quisiéramos usar schedule lib)
            # Pero para control fino, usaremos bucle custom
            
            # Ejecución inicial de capas lentas
            self.run_layer_1_macro()
            self.run_layer_2_technical()
            
            # 4. Main Loop
            while self.running:
                self._tick()
                time.sleep(1) # Pulso de 1 segundo (ajustable)
                
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Excepción en main loop: {e}", exc_info=True)
            self._handle_shutdown(None, None)

    def _tick(self):
        """Lógica ejecutada en cada pulso del sistema."""
        now = datetime.now()
        
        # Scheduler manual
        
        # Layer 1: Diario (ej. al abrir mercado o cada 24h)
        # Por simplicidad: Cada 4 horas en este MVP
        if not self.last_l1_run or (now - self.last_l1_run).total_seconds() > 14400:
            self.run_layer_1_macro()
        
        # Layer 2: Horario
        if not self.last_l2_run or (now - self.last_l2_run).total_seconds() > 3600:
            self.run_layer_2_technical()
            
        # Layer 3: Continuo (Micro estructura)
        # Itera sobre los candidatos de L2
        # Solo si el mercado está abierto (check simple)
        self.run_layer_3_micro()

    # ─────────────────────────────────────────────────────────────────────────
    # STRATEGY LAYERS
    # ─────────────────────────────────────────────────────────────────────────

    def run_layer_1_macro(self):
        """Ejecuta escáner macro (filtro fundamental)."""
        logger.info(f"{LogEmoji.SYNC} Ejecutando Capa 1: Macro Scanner...")
        try:
            # 1. Actualizar datos fundamentales? 
            # (Ingestor debería tener scheduled job, aquí asumimos datos frescos en DB)
            
            # 2. Filtrar
            # Macro scanner escanea toda la DB (ingestor.tickers)
            candidates = self.layer1_macro.update_universe([]) # [] pq es el inicio
            self.universe_l1 = candidates
            self.last_l1_run = datetime.now()
            
            logger.info(f"{LogEmoji.INFO} Capa 1 finalizada. Candidatos: {len(candidates)}")
            if candidates:
                logger.info(f"Top L1: {candidates[:5]}")
                
        except Exception as e:
            logger.error(f"Error en Capa 1: {e}")

    def run_layer_2_technical(self):
        """Ejecuta filtro técnico (trend, vol)."""
        if not self.universe_l1:
            logger.warning("Capa 1 vacía, saltando Capa 2")
            return
            
        logger.info(f"{LogEmoji.SYNC} Ejecutando Capa 2: Filtro Técnico...")
        try:
            # Necesitamos datos OHLCV recientes.
            # En vivo, deberíamos pedir a MT5 o Yfinance los últimos datos.
            # Por ahora, confiamos en lo que hay en DB o hacemos sync rápido.
            self._sync_data_for_symbols(self.universe_l1)
            
            candidates = self.layer2_tech.update_universe(self.universe_l1)
            self.universe_l2 = candidates
            self.last_l2_run = datetime.now()
            
            logger.info(f"{LogEmoji.INFO} Capa 2 finalizada. Candidatos L2: {len(candidates)}")
            if candidates:
                logger.info(f"Top L2: {candidates[:5]}")
                
        except Exception as e:
            logger.error(f"Error en Capa 2: {e}")

    def run_layer_3_micro(self):
        """Ejecuta análisis de micro-estructura (Order Flow / Price Action)."""
        if not self.universe_l2:
            return

        # Para cada activo en el universo filtrado
        for symbol in self.universe_l2:
            try:
                # 1. Obtener datos tick/minuto realtime
                # MT5 Connector nos da el tick actual
                tick = self.connector.get_tick(symbol)
                if not tick:
                    continue
                
                # Necesitamos construir velas o un pequeño dataframe reciente para la estrategia
                # Micro strategy espera un DataFrame con ohlcv para calcular order blocks etc.
                # En live:
                # Opcion A: Mantener buffer en memoria (complejo)
                # Opcion B: Pedir ultimas N velas a MT5 (mejor)
                
                # Como micro.py espera acceso a DB o dataframe pasado...
                # Vamos a adaptar: micro.generate_signal(symbol) lee de DB.
                # Así que primero SINCRONIZAMOS datos recientes a DB.
                # (Esto puede ser lento si L2 es grande. Idealmente L2 <= 10 activos)
                
                # Simulación de flujo:
                # signal = self.layer3_micro.generate_signal(symbol)
                # Si signal != 0 -> Router
                
                # Hack temporal para demo:
                # Generamos señal basada en datos estáticos DB (no Realtime real)
                # TODO: Implementar Realtime Data Feed en MicroStrategy
                
                signal_value = self.layer3_micro.generate_signal(symbol)
                
                if abs(signal_value) > 0.1:
                    # Crear evento
                    event = SignalEvent(
                        type="SIGNAL",
                        symbol=symbol,
                        signal_strength=signal_value,
                        strategy_id="MicroStructure"
                    )
                    
                    # Enviar al Router
                    self.router.on_signal(event)
                    
            except Exception as e:
                # Logar una vez por símbolo/minuto para no floodear
                pass

    def _sync_data_for_symbols(self, symbols: list):
        """
        Descarga datos recientes para los símbolos dados.
        En producción real, esto usaría MT5 copy_rates_from_pos o Stream.
        Aquí usamos el Ingestor (Yfinance) por simplicidad de arquitectura híbrida.
        """
        # Hack: Llamar a ingestor.sync_market_data con un filtro de símbolos
        # ingestor.sync... descarga todo el universo.
        # Asumiremos que el usuario corre el script de datos por separado o que
        # la DB está razonablemente al día.
        # Para LIVE puro, MicroStrategy debería pedir datos a MT5Connector.
        pass

    def _handle_shutdown(self, signum, frame):
        """Manejador de cierre ordenado."""
        if not self.running: return
        self.running = False
        
        logger.warning(f"{LogEmoji.WARNING} Solicitud de cierre recibida...")
        
        if self.oms:
            self.oms.stop()
            # Opcional: Cerrar posiciones intraday?
            # self.oms.close_all_positions() 
            
        if self.connector:
            self.connector.disconnect()
            
        logger.info("Sistema finalizado correctamente.")
        sys.exit(0)

if __name__ == "__main__":
    # Permite ejecutar directamente
    orchestrator = LiveOrchestrator()
    orchestrator.start()
