import logging

import sys

from typing import Optional

from datetime import datetime

import os


try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    colorlog = None
    COLORLOG_AVAILABLE = False


class TradingLogger:


    _instance: Optional['TradingLogger'] = None

    _initialized: bool = False


    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(
        self,
        name: str = "quant_system",
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_dir: str = "logs"
    ):
        if TradingLogger._initialized:
            return

        self.name = name
        self.level = level
        self.log_dir = log_dir

        if log_to_file and not os.path.exists(log_dir):
            os.makedirs(log_dir)


        self.logger = logging.getLogger(name)

        self.logger.setLevel(level)

        self.logger.handlers = []


        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

        date_format = "%Y-%m-%d %H:%M:%S"


        console_handler = logging.StreamHandler(sys.stdout)

        console_handler.setLevel(level)

        if COLORLOG_AVAILABLE:
            color_format = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_format)
        else:
            console_handler.setFormatter(logging.Formatter(log_format, date_format))

        self.logger.addHandler(console_handler)


        if log_to_file:
            log_filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"

            file_handler = logging.FileHandler(
                os.path.join(log_dir, log_filename),
                encoding='utf-8'
            )

            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))

            self.logger.addHandler(file_handler)

        TradingLogger._initialized = True


    def get_logger(self, module_name: str = None) -> logging.Logger:
        if module_name:
            return logging.getLogger(f"{self.name}.{module_name}")
        return self.logger


    @classmethod
    def reset(cls):
        cls._instance = None
        cls._initialized = False


def get_logger(module_name: str = None) -> logging.Logger:
    trading_logger = TradingLogger()
    return trading_logger.get_logger(module_name)


class LogEmoji:
    ENTRY = "🚀"
    EXIT = "🏁"
    PROFIT = "✅"
    LOSS = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    SIGNAL_BUY = "🟢"
    SIGNAL_SELL = "🔴"
    SIGNAL_NEUTRAL = "⚪"
    DATABASE = "💾"
    SYNC = "🔄"
    CHART = "📊"
    MONEY = "💰"


