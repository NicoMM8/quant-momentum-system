# =============================================================================
# CONNECTORS.PY - CONEXIÓN A LA BASE DE DATOS
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo maneja la conexión a la base de datos SQLite donde guardamos
# todos los datos de trading: precios históricos, fundamentales, trades, etc.
#
# ¿QUÉ ES SQLite?
# ---------------
# SQLite es una base de datos "ligera" que guarda todo en un solo archivo.
# No necesita instalación de servidores ni configuración complicada.
# Es perfecta para proyectos pequeños y medianos.
#
# El archivo de nuestra base de datos se llama "quant.db"
#
# ¿QUÉ ES EL PATRÓN SINGLETON?
# ----------------------------
# Este código usa el patrón "Singleton" (Único en inglés).
# 
# Imagina que tienes una llave maestra de tu casa. No tiene sentido tener
# 100 copias de la misma llave, ¿verdad? Solo necesitas UNA.
#
# Lo mismo pasa con la conexión a la base de datos:
# - Crear muchas conexiones consume memoria y recursos
# - Puede causar conflictos si dos partes del código escriben al mismo tiempo
# - Es ineficiente
#
# El patrón Singleton garantiza que SOLO EXISTA UNA conexión, y todos
# los que la necesiten usen esa misma conexión.
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

import sqlite3
# sqlite3 es la librería de Python para trabajar con bases de datos SQLite
# Viene incluida con Python, no necesitas instalarla

import threading
# threading permite trabajar con múltiples "hilos" de ejecución
# Un hilo es como un trabajador independiente dentro de tu programa
# Usamos esto para que la conexión sea segura cuando hay varios hilos

import os
# os permite interactuar con el sistema operativo
# Lo usamos para construir la ruta al archivo de base de datos


# =============================================================================
# CLASE: DatabaseConnection (Conexión a Base de Datos)
# =============================================================================

class DatabaseConnection:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║               SINGLETON DE CONEXIÓN A BASE DE DATOS                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase gestiona UNA ÚNICA conexión a nuestra base de datos SQLite.   ║
    ║                                                                           ║
    ║  PATRÓN SINGLETON EXPLICADO:                                              ║
    ║  ───────────────────────────                                              ║
    ║  • Primera vez que la usas: Crea la conexión                              ║
    ║  • Segunda vez que la usas: Te devuelve la MISMA conexión                 ║
    ║  • Tercera vez que la usas: Te devuelve la MISMA conexión                 ║
    ║  • ... y así sucesivamente                                                ║
    ║                                                                           ║
    ║  EJEMPLO DE USO:                                                          ║
    ║  ─────────────────                                                        ║
    ║  # En cualquier parte del código:                                         ║
    ║  db = DatabaseConnection()                                                ║
    ║  conexion = db.connection                                                 ║
    ║  # Ahora puedes usar 'conexion' para hacer consultas SQL                  ║
    ║                                                                           ║
    ║  SEGURIDAD MULTI-HILO:                                                    ║
    ║  ──────────────────────                                                   ║
    ║  Esta clase es "thread-safe" (segura para múltiples hilos).               ║
    ║  Aunque varios trabajadores pidan la conexión al mismo tiempo,            ║
    ║  no habrá problemas.                                                      ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # =========================================================================
    # VARIABLES DE CLASE (compartidas por todas las instancias)
    # =========================================================================
    
    _instance = None
    # Aquí guardamos LA ÚNICA instancia de esta clase
    # Al principio es None porque no hemos creado ninguna
    # Después de crear la primera instancia, esto la referenciará
    
    _lock = threading.Lock()
    # Un "Lock" (candado) para garantizar seguridad en multi-hilo
    # 
    # Imagina una puerta con candado:
    # - Cuando un hilo quiere crear la conexión, "cierra" el candado
    # - Otros hilos tienen que esperar afuera
    # - Cuando termina, "abre" el candado y otro puede entrar
    # 
    # Esto evita que dos hilos creen conexiones al mismo tiempo
    
    _connection = None
    # La conexión real a SQLite se guardará aquí

    # =========================================================================
    # MÉTODO ESPECIAL: __new__ (Controla la creación del objeto)
    # =========================================================================
    
    def __new__(cls):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                              __new__                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Este método especial se ejecuta ANTES del __init__.                    │
        │  Controla SI se crea un nuevo objeto o se reutiliza uno existente.      │
        │                                                                         │
        │  FLUJO DE DECISIÓN:                                                     │
        │                                                                         │
        │    ┌──────────────────────┐                                             │
        │    │ ¿Ya existe una       │                                             │
        │    │ instancia guardada?  │                                             │
        │    └──────────┬───────────┘                                             │
        │               │                                                         │
        │         ┌─────┴─────┐                                                   │
        │         │           │                                                   │
        │         ▼           ▼                                                   │
        │     ┌───────┐   ┌───────────────┐                                       │
        │     │  SÍ   │   │      NO       │                                       │
        │     └───┬───┘   └───────┬───────┘                                       │
        │         │               │                                               │
        │         ▼               ▼                                               │
        │   Devuelve la      Crea UNA nueva                                       │
        │   instancia        instancia y                                          │
        │   existente        guárdala                                             │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # PASO 1: ¿Ya existe una instancia?
        if cls._instance is None:
            # No existe, necesitamos crearla
            
            # PASO 2: Adquirir el candado (por seguridad multi-hilo)
            with cls._lock:
                # 'with' asegura que el candado se libere automáticamente
                
                # PASO 3: Verificar DE NUEVO (otro hilo pudo haberla creado)
                # Esta doble verificación se llama "Double-Checked Locking"
                if cls._instance is None:
                    
                    # PASO 4: Ahora sí, crear la instancia única
                    cls._instance = super(DatabaseConnection, cls).__new__(cls)
                    # super().__new__() es la forma normal de crear objetos
                    
                    # PASO 5: Inicializar la conexión
                    cls._instance._initialize_connection()
        
        # PASO 6: Devolver la instancia (nueva o existente)
        return cls._instance

    # =========================================================================
    # MÉTODO PRIVADO: _initialize_connection (Inicializar Conexión)
    # =========================================================================
    
    def _initialize_connection(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                      _INITIALIZE_CONNECTION                             │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Este método privado (el _ al inicio indica que es privado)             │
        │  crea la conexión real a la base de datos SQLite.                       │
        │                                                                         │
        │  PASOS:                                                                 │
        │  1. Construir la ruta al archivo quant.db                               │
        │  2. Conectarse a SQLite                                                 │
        │  3. Configurar para multi-hilo                                          │
        │  4. Guardar la conexión                                                 │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # PASO 1: Construir la ruta al archivo de base de datos
        # os.getcwd() = "get current working directory" = obtener directorio actual
        # Ejemplo: Si estás en E:\quant_system, esto será E:\quant_system\quant.db
        db_path = os.path.join(os.getcwd(), "quant.db")
        
        try:
            # PASO 2: Intentar conectarse a SQLite
            self._connection = sqlite3.connect(
                db_path,
                check_same_thread=False
                # check_same_thread=False permite que múltiples hilos
                # usen la misma conexión. Normalmente SQLite solo permite
                # un hilo por conexión, pero esto lo desactiva.
            )
            
            # PASO 3: Informar que la conexión fue exitosa
            print(f"--> Conexión a SQLite establecida: {db_path}")
            
        except sqlite3.Error as e:
            # Si algo sale mal (archivo corrupto, permisos, etc.)
            print(f"Error al conectar a la base de datos: {e}")
            self._connection = None  # Dejamos la conexión como None

    # =========================================================================
    # PROPIEDAD: connection (acceso a la conexión)
    # =========================================================================
    
    @property  # Este decorador convierte el método en una "propiedad"
    def connection(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                           CONNECTION                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Esta "propiedad" permite acceder a la conexión SQLite.                 │
        │                                                                         │
        │  ¿QUÉ ES UNA PROPIEDAD (@property)?                                     │
        │  ─────────────────────────────────                                      │
        │  Es una forma de acceder a un dato como si fuera un atributo,           │
        │  pero internamente es un método.                                        │
        │                                                                         │
        │  En lugar de escribir:  db.get_connection()                             │
        │  Escribes simplemente:  db.connection                                   │
        │                                                                         │
        │  EJEMPLO DE USO:                                                        │
        │  ─────────────────                                                      │
        │  db = DatabaseConnection()                                              │
        │  conn = db.connection  # Accedemos como si fuera un atributo            │
        │  cursor = conn.execute("SELECT * FROM market_data")                     │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        return self._connection
    
    # =========================================================================
    # MÉTODO: close (cerrar la conexión)
    # =========================================================================
    
    def close(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                              CLOSE                                      │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Cierra la conexión a la base de datos y limpia el Singleton.           │
        │                                                                         │
        │  ¿CUÁNDO LLAMAR A ESTE MÉTODO?                                          │
        │  ──────────────────────────────                                         │
        │  • Al finalizar el programa                                             │
        │  • Cuando ya no necesites más la base de datos                          │
        │  • Antes de reiniciar/reconfigurar la conexión                          │
        │                                                                         │
        │  ES IMPORTANTE CERRAR:                                                  │
        │  ───────────────────────                                                │
        │  • Libera memoria y recursos del sistema                                │
        │  • Evita "fugas" de conexiones                                          │
        │  • Permite que otros programas accedan al archivo                       │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        if self._connection:
            # Cerrar la conexión SQLite
            self._connection.close()
            self._connection = None
            print("--> Conexión a SQLite cerrada correctamente.")
        
        # Limpiar el Singleton para que pueda crearse de nuevo si es necesario
        DatabaseConnection._instance = None
    
    # =========================================================================
    # MÉTODOS DE CONTEXT MANAGER: __enter__ y __exit__
    # =========================================================================
    
    def __enter__(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                           __ENTER__                                     │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Este método permite usar la clase con 'with' (Context Manager).        │
        │                                                                         │
        │  ¿QUÉ ES UN CONTEXT MANAGER?                                            │
        │  ─────────────────────────────                                          │
        │  Es un patrón que garantiza que un recurso se libere correctamente,     │
        │  incluso si hay errores.                                                │
        │                                                                         │
        │  EJEMPLO:                                                               │
        │  ──────────                                                             │
        │  with DatabaseConnection() as db:                                       │
        │      # Hacer cosas con la base de datos                                 │
        │      conn = db.connection                                               │
        │      datos = conn.execute("SELECT * FROM assets").fetchall()            │
        │  # Aquí, automáticamente se cierra la conexión                          │
        │                                                                         │
        │  Es como decir: "Abre esto, úsalo, y cuando termines, ciérralo          │
        │  automáticamente (aunque haya un error)".                               │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        return self  # Devolvemos la instancia para usar dentro del 'with'
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                            __EXIT__                                     │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Este método se ejecuta automáticamente al salir del bloque 'with'.     │
        │                                                                         │
        │  PARÁMETROS (proporcionados automáticamente por Python):                │
        │  • exc_type: Tipo de excepción (si hubo error)                          │
        │  • exc_val: Valor de la excepción                                       │
        │  • exc_tb: Traceback de la excepción                                    │
        │                                                                         │
        │  Si no hubo error, todos son None.                                      │
        │                                                                         │
        │  RETORNO:                                                               │
        │  • False = Si hubo error, déjalo propagarse                             │
        │  • True = Suprimir el error (no recomendado generalmente)               │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        self.close()  # Cerrar la conexión automáticamente
        return False  # No suprimir errores, dejar que se propaguen


# =============================================================================
# EJEMPLO DE USO (comentado para referencia)
# =============================================================================
#
# FORMA 1: Uso directo
# ---------------------
# db = DatabaseConnection()
# conexion = db.connection
# cursor = conexion.execute("SELECT * FROM market_data WHERE symbol = 'AAPL'")
# datos = cursor.fetchall()
# # ... hacer algo con los datos ...
# db.close()  # ¡No olvidar cerrar!
#
# FORMA 2: Usando Context Manager (recomendado)
# ----------------------------------------------
# with DatabaseConnection() as db:
#     conexion = db.connection
#     cursor = conexion.execute("SELECT * FROM assets")
#     assets = cursor.fetchall()
#     for asset in assets:
#         print(asset)
# # La conexión se cierra automáticamente aquí
#
# =============================================================================