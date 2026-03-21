import sqlite3

import threading

import os


class DatabaseConnection:


    _instance = None

    _lock = threading.Lock()

    _connection = None


    def __new__(cls):
        if cls._instance is None:

            with cls._lock:

                if cls._instance is None:

                    cls._instance = super(DatabaseConnection, cls).__new__(cls)

                    cls._instance._initialize_connection()

        return cls._instance


    def _initialize_connection(self):
        db_path = os.path.join(os.getcwd(), "quant.db")

        try:
            self._connection = sqlite3.connect(
                db_path,
                check_same_thread=False
            )

            print(f"--> Conexión a SQLite establecida: {db_path}")

        except sqlite3.Error as e:
            print(f"Error al conectar a la base de datos: {e}")
            self._connection = None


    @property
    def connection(self):
        return self._connection


    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            print("--> Conexión a SQLite cerrada correctamente.")

        DatabaseConnection._instance = None


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


