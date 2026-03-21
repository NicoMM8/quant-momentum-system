import pandas as pd
from typing import List
from src.core.interfaces import IDataRepository
from src.data.connectors import DatabaseConnection

class SQLFundamentalRepository(IDataRepository):

    def __init__(self):
        db_connection = DatabaseConnection()
        if db_connection is None or not hasattr(db_connection, 'connection'):
            raise RuntimeError("DatabaseConnection no inicializado correctamente")
        self.conn = db_connection.connection

    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        if not symbols:
            return pd.DataFrame()
        try:
            placeholders = ','.join(['?'] * len(symbols))

            query = f"""
                SELECT symbol, pe_ratio, market_cap, sector
                FROM fundamental_data
                WHERE symbol IN ({placeholders})
            """

            return pd.read_sql(query, self.conn, params=tuple(symbols))
        except Exception as e:
            print(f"Error al consultar datos fundamentales: {e}")
            return pd.DataFrame()

class ParquetTickRepository(IDataRepository):
    def __init__(self, data_dir: str = "./data/parquet"):
        self.data_dir = data_dir

    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        print(f"Leyendo Parquet para: {symbols}")
        return pd.DataFrame()

class DataFactory:
    @staticmethod
    def get_repository(data_type: str) -> IDataRepository:
        if data_type == 'fundamental':
            return SQLFundamentalRepository()
        elif data_type == 'tick':
            return ParquetTickRepository()
        else:
            raise ValueError(f"Tipo de dato desconocido: {data_type}")
