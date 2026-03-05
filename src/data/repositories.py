import pandas as pd
from typing import List
from src.core.interfaces import IDataRepository
from src.data.connectors import DatabaseConnection

class SQLFundamentalRepository(IDataRepository):
    """
    Repositorio para datos fundamentales usando SQLite.
    """
    
    def __init__(self):
        # Obtenemos la conexión cruda de SQLite
        db_connection = DatabaseConnection()
        if db_connection is None or not hasattr(db_connection, 'connection'):
            raise RuntimeError("DatabaseConnection no inicializado correctamente")
        self.conn = db_connection.connection

    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        if not symbols:
            return pd.DataFrame()
        try:
            # Formatear la lista para la query SQL de forma segura
            # En SQLite los placeholders son '?'
            placeholders = ','.join(['?'] * len(symbols))
            
            query = f"""
                SELECT symbol, pe_ratio, market_cap, sector 
                FROM fundamental_data 
                WHERE symbol IN ({placeholders})
            """
            
            # Pandas puede leer directamente usando la conexión de sqlite3
            # params=symbols evita inyección SQL y errores de formato
            return pd.read_sql(query, self.conn, params=tuple(symbols))
        except Exception as e:
            print(f"Error al consultar datos fundamentales: {e}")
            return pd.DataFrame()

class ParquetTickRepository(IDataRepository):
    """
    (Sin cambios) Lee archivos Parquet locales.
    """
    def __init__(self, data_dir: str = "./data/parquet"):
        self.data_dir = data_dir

    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        # Aquí iría la lógica real de lectura de archivos
        print(f"Leyendo Parquet para: {symbols}")
        return pd.DataFrame() # Retorna vacío por ahora

class DataFactory:
    @staticmethod
    def get_repository(data_type: str) -> IDataRepository:
        if data_type == 'fundamental':
            return SQLFundamentalRepository()
        elif data_type == 'tick':
            return ParquetTickRepository()
        else:
            raise ValueError(f"Tipo de dato desconocido: {data_type}")