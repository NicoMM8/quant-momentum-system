from abc import ABC, abstractmethod

from typing import List, Dict, Any

import pandas as pd


class IUniverseFilter(ABC):

    @abstractmethod
    def update_universe(self, candidates: List[str], data_context: Any = None) -> List[str]:
        pass


class ISignalGenerator(ABC):

    @abstractmethod
    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        pass


class IStrategy(IUniverseFilter, ISignalGenerator):
    pass


class IDataRepository(ABC):

    @abstractmethod
    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        pass
