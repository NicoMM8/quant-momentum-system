import time
import signal
import sys
import os
import schedule
from datetime import datetime
import pandas as pd

from src.utils.logger import get_logger, LogEmoji
from src.data.ingestion import DataIngestor
from src.core.events import SignalEvent

from src.execution.mt5_connector import MT5Connector
from src.execution.oms import OrderManagementSystem
from src.execution.router import OrderRouter

from src.strategies.risk import PortfolioRiskManager, PositionSizer, RiskParameters

from src.strategies.alpha.macro import MacroScannerStrategy
from src.strategies.alpha.technical import TechnicalFilterStrategy
from src.strategies.alpha.micro import MicroStructureStrategy

logger = get_logger("orchestrator")

class LiveOrchestrator:
    def __init__(self, config_path: str = "config/settings.yaml"):
        logger.info("Inicializando Quant System Pro...")
        self.config_path = config_path
        self.running = False

        self.connector = MT5Connector(config_path)
        self.risk_manager = PortfolioRiskManager()
        self.oms = OrderManagementSystem(self.connector, self.risk_manager)
        self.sizer = PositionSizer()
        self.router = OrderRouter(self.oms, self.sizer)

        db_path = os.path.join(os.getcwd(), "data", "market_data.db")
        self.ingestor = DataIngestor(db_path, config_path)

        self.layer1_macro = MacroScannerStrategy(db_path)
        self.layer2_tech = TechnicalFilterStrategy(db_path)
        self.layer3_micro = MicroStructureStrategy(db_path)

        self.universe_l1 = []
        self.universe_l2 = []

        self.last_l1_run = None
        self.last_l2_run = None

    def start(self):
        self.running = True

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        try:
            if not self.connector.connect():
                logger.error("Fallo crítico: No se pudo conectar a MT5. Abortando.")
                return

            self.oms.start()

            logger.info(f"{LogEmoji.CHART} Sistema INICIADO. Esperando ticks...")


            self.run_layer_1_macro()
            self.run_layer_2_technical()

            while self.running:
                self._tick()
                time.sleep(1)

        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Excepción en main loop: {e}", exc_info=True)
            self._handle_shutdown(None, None)

    def _tick(self):
        now = datetime.now()


        if not self.last_l1_run or (now - self.last_l1_run).total_seconds() > 14400:
            self.run_layer_1_macro()

        if not self.last_l2_run or (now - self.last_l2_run).total_seconds() > 3600:
            self.run_layer_2_technical()

        self.run_layer_3_micro()


    def run_layer_1_macro(self):
        logger.info(f"{LogEmoji.SYNC} Ejecutando Capa 1: Macro Scanner...")
        try:

            candidates = self.layer1_macro.update_universe([])
            self.universe_l1 = candidates
            self.last_l1_run = datetime.now()

            logger.info(f"{LogEmoji.INFO} Capa 1 finalizada. Candidatos: {len(candidates)}")
            if candidates:
                logger.info(f"Top L1: {candidates[:5]}")

        except Exception as e:
            logger.error(f"Error en Capa 1: {e}")

    def run_layer_2_technical(self):
        if not self.universe_l1:
            logger.warning("Capa 1 vacía, saltando Capa 2")
            return

        logger.info(f"{LogEmoji.SYNC} Ejecutando Capa 2: Filtro Técnico...")
        try:
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
        if not self.universe_l2:
            return

        for symbol in self.universe_l2:
            try:
                tick = self.connector.get_tick(symbol)
                if not tick:
                    continue


                signal_value = self.layer3_micro.generate_signal(symbol)

                if abs(signal_value) > 0.1:
                    event = SignalEvent(
                        type="SIGNAL",
                        symbol=symbol,
                        signal_strength=signal_value,
                        strategy_id="MicroStructure"
                    )

                    self.router.on_signal(event)

            except Exception as e:
                pass

    def _sync_data_for_symbols(self, symbols: list):
        pass

    def _handle_shutdown(self, signum, frame):
        if not self.running: return
        self.running = False

        logger.warning(f"{LogEmoji.WARNING} Solicitud de cierre recibida...")

        if self.oms:
            self.oms.stop()

        if self.connector:
            self.connector.disconnect()

        logger.info("Sistema finalizado correctamente.")
        sys.exit(0)

if __name__ == "__main__":
    orchestrator = LiveOrchestrator()
    orchestrator.start()
