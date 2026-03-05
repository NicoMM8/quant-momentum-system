# =============================================================================
# INGESTION.PY - DESCARGA Y ALMACENAMIENTO DE DATOS DE MERCADO
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo es el "ETL Pipeline" del sistema:
#
#   E = EXTRACT (Extraer)    → Descargar datos de Yahoo Finance
#   T = TRANSFORM (Transformar) → Limpiar y estructurar datos
#   L = LOAD (Cargar)        → Guardar en la base de datos SQLite
#
# Es como tener un robot que cada día:
# 1. Va a la tienda (Yahoo Finance)
# 2. Compra los ingredientes (datos de precios, fundamentales)
# 3. Los limpia y organiza
# 4. Los guarda en la nevera (base de datos)
#
# ¿QUÉ ES YAHOO FINANCE?
# -----------------------
# Yahoo Finance es un servicio gratuito que proporciona datos del mercado
# bursátil: precios de acciones, volúmenes, datos fundamentales, etc.
# La librería 'yfinance' de Python permite acceder a estos datos fácilmente.
#
# ¿QUÉ SON LOS DATOS OHLCV?
# --------------------------
# OHLCV son las siglas de:
# - Open (Apertura): Precio al inicio del período
# - High (Máximo): Precio más alto del período
# - Low (Mínimo): Precio más bajo del período
# - Close (Cierre): Precio al final del período
# - Volume (Volumen): Cantidad de acciones negociadas
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES - Herramientas que necesitamos
# -----------------------------------------------------------------------------

import yfinance as yf
# yfinance es la librería que nos conecta con Yahoo Finance
# Permite descargar datos históricos de acciones, ETFs, criptomonedas, etc.

import pandas as pd
# Pandas es LA librería de Python para análisis de datos
# Un DataFrame es como una hoja de Excel dentro de Python

import sqlite3
# SQLite es una base de datos ligera que guarda todo en un archivo
# No necesita instalación de servidores

import os
# os permite interactuar con el sistema operativo
# Lo usamos para verificar si existen archivos

import time
# time nos permite pausar la ejecución del programa
# Lo usamos para no sobrecargar los servidores de Yahoo (rate limiting)

import yaml
# YAML es un formato de archivos de configuración fácil de leer
# Lo usamos para cargar las configuraciones del sistema

import logging
# logging es la forma profesional de mostrar mensajes en Python
# Mejor que print() porque se puede guardar en archivos, filtrar por nivel, etc.

from tqdm import tqdm
# tqdm muestra barras de progreso bonitas en la terminal
# Ejemplo: Descargando: [████████████░░░░░░░░] 60% | ETA: 10s

from typing import Optional, List
# Anotaciones de tipo que ayudan a documentar el código
# Optional[str] significa "un string o None"
# List[str] significa "una lista de strings"

from src.utils.static_universe import MY_HUGE_UNIVERSE
# Universo curado de ~700 tickers, mantenido en un archivo separado
# para facilitar mantenimiento y evitar duplicación


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
# __name__ es una variable especial de Python que contiene el nombre del módulo
# En este caso sería 'src.data.ingestion'
# Esto permite identificar de dónde vienen los mensajes de log


# =============================================================================
# CLASE: DataIngestor (Descargador de Datos)
# =============================================================================

class DataIngestor:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                       DESCARGADOR DE DATOS DE MERCADO                     ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase es responsable de mantener la base de datos actualizada       ║
    ║  con datos de mercado reales descargados de Yahoo Finance.                ║
    ║                                                                           ║
    ║  FUNCIONALIDADES:                                                         ║
    ║  ─────────────────                                                        ║
    ║  • Descarga información de empresas (sector, industria)                   ║
    ║  • Descarga histórico de precios OHLCV (2 años por defecto)               ║
    ║  • Descarga datos fundamentales (P/E ratio, market cap, etc.)             ║
    ║  • Valida integridad de los datos descargados                             ║
    ║  • Rate limiting para evitar que Yahoo nos bloquee                        ║
    ║                                                                           ║
    ║  EL PROCESO DE DESCARGA:                                                  ║
    ║  ─────────────────────────                                                ║
    ║                                                                           ║
    ║   Yahoo Finance    →    Python (Este archivo)    →    SQLite (quant.db)   ║
    ║   ┌──────────┐          ┌──────────────────┐          ┌──────────┐        ║
    ║   │  API de  │  HTTP    │  1. Descargar    │  SQL     │  Tablas: │        ║
    ║   │  Datos   │ ───────► │  2. Transformar  │ ───────► │  assets  │        ║
    ║   │  Gratis  │          │  3. Validar      │          │  market  │        ║
    ║   └──────────┘          │  4. Insertar     │          │  fund.   │        ║
    ║                         └──────────────────┘          └──────────┘        ║
    ║                                                                           ║
    ║  EJEMPLO DE USO:                                                          ║
    ║  ─────────────────                                                        ║
    ║  ingestor = DataIngestor("quant.db")                                      ║
    ║  ingestor.sync_assets_table()      # Descargar info de empresas           ║
    ║  ingestor.sync_market_data("2y")   # Descargar 2 años de precios          ║
    ║  ingestor.sync_fundamentals()      # Descargar ratios financieros         ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # =========================================================================
    # CONSTRUCTOR: __init__ (Inicialización)
    # =========================================================================
    
    def __init__(self, db_path: str, config_path: str = "config/settings.yaml"):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                            __INIT__                                     │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Constructor: Se ejecuta automáticamente al crear un nuevo objeto.     │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  • db_path (str): Ruta al archivo de base de datos                      │
        │    Ejemplo: "quant.db" o "C:/data/mi_sistema.db"                        │
        │                                                                         │
        │  • config_path (str): Ruta al archivo de configuración YAML             │
        │    Por defecto: "config/settings.yaml"                                  │
        │                                                                         │
        │  LO QUE HACE:                                                           │
        │  1. Guarda la ruta de la base de datos                                  │
        │  2. Carga la configuración desde el archivo YAML                        │
        │  3. Extrae la lista de tickers (acciones) a descargar                   │
        │  4. Configura el rate limiting (tiempo entre peticiones)                │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # Guardar la ruta de la base de datos
        self.db_path = db_path
        
        # Cargar configuración desde archivo YAML
        self.config = self._load_config(config_path)
        
        # ─────────────────────────────────────────────────────────────────────
        # CONFIGURACIÓN DEL UNIVERSO DE ACCIONES
        # ─────────────────────────────────────────────────────────────────────
        # "Universo" = la lista de acciones que vamos a analizar
        
        universe_config = self.config.get('universe', {})
        # .get() busca la clave 'universe' en el diccionario
        # Si no existe, devuelve {} (diccionario vacío)
        
        self.tickers = universe_config.get('default_tickers', MY_HUGE_UNIVERSE)
        # Lista de símbolos bursátiles a descargar
        # Si no hay configuración, usamos estos 8 por defecto:
        # - AAPL: Apple
        # - MSFT: Microsoft
        # - GOOGL: Alphabet/Google
        # - AMZN: Amazon
        # - NVDA: NVIDIA
        # - TSLA: Tesla
        # - SPY: ETF del S&P 500
        # - QQQ: ETF del NASDAQ 100
        
        # ─────────────────────────────────────────────────────────────────────
        # CONFIGURACIÓN DE RATE LIMITING
        # ─────────────────────────────────────────────────────────────────────
        # Rate limiting = poner pausas entre peticiones para no ser bloqueado
        
        ingestion_config = self.config.get('ingestion', {})
        
        self.delay_ms = ingestion_config.get('yahoo_delay_ms', 500)
        # Tiempo de espera entre peticiones en milisegundos
        # 500ms = 0.5 segundos = máximo 2 peticiones por segundo
        # Yahoo Finance puede bloquearte si haces demasiadas peticiones rápidas
        
        self.max_retries = ingestion_config.get('max_retries', 3)
        # Si una descarga falla, cuántas veces reintentar antes de rendirse
    
    # =========================================================================
    # MÉTODO PRIVADO: _load_config (Cargar Configuración)
    # =========================================================================
    
    def _load_config(self, config_path: str) -> dict:
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                          _LOAD_CONFIG                                   │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Carga la configuración desde un archivo YAML.                          │
        │                                                                         │
        │  ¿QUÉ ES YAML?                                                          │
        │  YAML es un formato de archivo fácil de leer, ideal para configuración. │
        │                                                                         │
        │  EJEMPLO DE ARCHIVO YAML:                                               │
        │  ─────────────────────────                                              │
        │  universe:                                                              │
        │    default_tickers:                                                     │
        │      - AAPL                                                             │
        │      - MSFT                                                             │
        │  ingestion:                                                             │
        │    yahoo_delay_ms: 500                                                  │
        │    max_retries: 3                                                       │
        │                                                                         │
        │  MANEJO DE ERRORES:                                                     │
        │  Si el archivo no existe o está corrupto, devuelve un diccionario       │
        │  vacío {} y el sistema usará valores por defecto.                       │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        # Verificar si el archivo de configuración existe
        if os.path.exists(config_path):
            try:
                # Abrir el archivo en modo lectura con codificación UTF-8
                with open(config_path, 'r', encoding='utf-8') as f:
                    # yaml.safe_load() convierte el texto YAML a un diccionario de Python
                    return yaml.safe_load(f)
                    
            except Exception as e:
                # Si hay cualquier error (archivo corrupto, permisos, etc.)
                logger.warning(f"No se pudo cargar config: {e}. Usando defaults.")
        
        # Si el archivo no existe o hubo error, devolver diccionario vacío
        return {}
    
    # =========================================================================
    # MÉTODO PRIVADO: _validate_ohlcv (Validar Datos OHLCV)
    # =========================================================================
    
    def _validate_ohlcv(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                      VALIDACIÓN DE DATOS OHLCV                        ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Verifica que los datos descargados tengan sentido lógico.            ║
        ║                                                                       ║
        ║  ¿POR QUÉ ES IMPORTANTE VALIDAR?                                      ║
        ║  ─────────────────────────────────                                    ║
        ║  A veces los datos de Yahoo Finance vienen con errores:               ║
        ║  - Datos faltantes                                                    ║
        ║  - Valores incorrectos (negativos, invertidos)                        ║
        ║  - Problemas de transmisión                                           ║
        ║                                                                       ║
        ║  Si una estrategia usa datos incorrectos, tomará decisiones malas.    ║
        ║  ¡Es como cocinar con ingredientes podridos!                          ║
        ║                                                                       ║
        ║  REGLAS DE VALIDACIÓN:                                                ║
        ║  ───────────────────────                                              ║
        ║                                                                       ║
        ║  REGLA 1: High >= Low                                                 ║
        ║  ────────────────────                                                 ║
        ║  El precio máximo del día SIEMPRE debe ser mayor o igual al mínimo.  ║
        ║  Es imposible que el máximo sea menor que el mínimo.                  ║
        ║                                                                       ║
        ║     CORRECTO:  High=152, Low=149  ✓                                   ║
        ║     INCORRECTO: High=149, Low=152  ✗ (están invertidos)               ║
        ║                                                                       ║
        ║  REGLA 2: High >= Open y High >= Close                                ║
        ║  ─────────────────────────────────────                                ║
        ║  El máximo debe ser >= que la apertura y el cierre.                   ║
        ║                                                                       ║
        ║  REGLA 3: Low <= Open y Low <= Close                                  ║
        ║  ────────────────────────────────────                                 ║
        ║  El mínimo debe ser <= que la apertura y el cierre.                   ║
        ║                                                                       ║
        ║  REGLA 4: Volume >= 0                                                 ║
        ║  ────────────────────                                                 ║
        ║  No puede haber volumen negativo (no tiene sentido).                  ║
        ║                                                                       ║
        ║  REGLA 5: Precios positivos                                           ║
        ║  ────────────────────────────                                         ║
        ║  Ningún precio puede ser negativo.                                    ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # Si el DataFrame está vacío, no hay nada que validar
        if df.empty:
            return False
        
        # Lista para acumular todos los problemas encontrados
        issues = []
        
        # ─────────────────────────────────────────────────────────────────────
        # REGLA 1: Verificar que High >= Low
        # ─────────────────────────────────────────────────────────────────────
        invalid_hl = (df['high'] < df['low']).sum()
        # .sum() cuenta cuántas veces la condición es True
        # Si invalid_hl > 0, hay filas donde High < Low (¡error!)
        
        if invalid_hl > 0:
            issues.append(f"High < Low en {invalid_hl} filas")
        
        # ─────────────────────────────────────────────────────────────────────
        # REGLA 2: Verificar que High >= Open y High >= Close
        # ─────────────────────────────────────────────────────────────────────
        invalid_high = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()
        # | significa "OR" (o una cosa o la otra)
        # Si High es menor que Open O menor que Close, está mal
        
        if invalid_high > 0:
            issues.append(f"High inválido en {invalid_high} filas")
        
        # ─────────────────────────────────────────────────────────────────────
        # REGLA 3: Verificar que Low <= Open y Low <= Close
        # ─────────────────────────────────────────────────────────────────────
        invalid_low = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()
        
        if invalid_low > 0:
            issues.append(f"Low inválido en {invalid_low} filas")
        
        # ─────────────────────────────────────────────────────────────────────
        # REGLA 4: Verificar que Volume >= 0
        # ─────────────────────────────────────────────────────────────────────
        negative_vol = (df['volume'] < 0).sum()
        
        if negative_vol > 0:
            issues.append(f"Volumen negativo en {negative_vol} filas")
        
        # ─────────────────────────────────────────────────────────────────────
        # REGLA 5: Verificar que todos los precios sean positivos
        # ─────────────────────────────────────────────────────────────────────
        negative_prices = (
            (df['open'] < 0) | 
            (df['high'] < 0) | 
            (df['low'] < 0) | 
            (df['close'] < 0)
        ).sum()
        
        if negative_prices > 0:
            issues.append(f"Precios negativos en {negative_prices} filas")
        
        # ─────────────────────────────────────────────────────────────────────
        # RESULTADO FINAL
        # ─────────────────────────────────────────────────────────────────────
        if issues:
            # Hay problemas: reportarlos y retornar False
            logger.warning(f"⚠️ Validación OHLCV para {symbol}: {', '.join(issues)}")
            return False
        
        # Todo bien: retornar True
        return True
    
    # =========================================================================
    # MÉTODO PRIVADO: _rate_limit (Pausar para evitar bloqueo)
    # =========================================================================
    
    def _rate_limit(self):
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                          _RATE_LIMIT                                    │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  Pausa la ejecución por un tiempo configurado.                          │
        │                                                                         │
        │  ¿POR QUÉ NECESITAMOS ESTO?                                             │
        │  ─────────────────────────────                                          │
        │  Yahoo Finance tiene límites de cuántas peticiones puedes hacer.        │
        │  Si haces demasiadas muy rápido, te bloquean temporalmente.             │
        │                                                                         │
        │  Es como en un buffet: si agarras toda la comida de golpe,              │
        │  el encargado te va a echar. Mejor ir despacio.                         │
        │                                                                         │
        │  CONFIGURACIÓN:                                                         │
        │  - self.delay_ms = milisegundos de pausa (por defecto 500ms)            │
        │  - 500ms = 0.5 segundos entre cada petición                             │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        time.sleep(self.delay_ms / 1000.0)
        # time.sleep() recibe segundos, pero self.delay_ms está en milisegundos
        # Por eso dividimos entre 1000 (1000ms = 1 segundo)

    # =========================================================================
    # MÉTODO PÚBLICO: sync_assets_table (Sincronizar Tabla de Activos)
    # =========================================================================
    
    def sync_assets_table(self):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                    PASO 1: SINCRONIZAR MAESTRO DE ACTIVOS             ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Descarga información básica de cada empresa y la guarda en SQLite.   ║
        ║                                                                       ║
        ║  ¿QUÉ INFORMACIÓN DESCARGA?                                           ║
        ║  ─────────────────────────────                                        ║
        ║  • symbol: El ticker de la acción (ej: 'AAPL', 'MSFT')                ║
        ║  • sector: Sector económico (ej: 'Technology', 'Healthcare')          ║
        ║  • industry: Industria específica (ej: 'Consumer Electronics')        ║
        ║  • is_active: Si la acción está activa (1) o no (0)                   ║
        ║                                                                       ║
        ║  ¿PARA QUÉ SIRVE?                                                     ║
        ║  ──────────────────                                                   ║
        ║  Tener esta información nos permite:                                  ║
        ║  • Filtrar acciones por sector ("solo quiero tecnología")             ║
        ║  • Diversificar ("no poner todo en una sola industria")               ║
        ║  • Análisis sectorial ("¿qué sector está más fuerte?")                ║
        ║                                                                       ║
        ║  TABLA RESULTANTE EN SQLite:                                          ║
        ║  ─────────────────────────────                                        ║
        ║  ┌─────────┬────────────────┬────────────────────┬───────────┐        ║
        ║  │ symbol  │    sector      │     industry       │ is_active │        ║
        ║  ├─────────┼────────────────┼────────────────────┼───────────┤        ║
        ║  │ AAPL    │ Technology     │ Consumer Electr.   │     1     │        ║
        ║  │ MSFT    │ Technology     │ Software-Infrastr. │     1     │        ║
        ║  │ JPM     │ Financial Svcs │ Banks-Diversified  │     1     │        ║
        ║  │ SPY     │ ETF            │ Unknown            │     1     │        ║
        ║  └─────────┴────────────────┴────────────────────┴───────────┘        ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        print(f"--- 1. Sincronizando Maestro de Activos ({len(self.tickers)}) ---")
        
        # Lista donde acumularemos toda la información
        asset_data = []
        
        # Iterar sobre cada ticker con barra de progreso
        for ticker in tqdm(self.tickers, desc="Descargando Info"):
            # tqdm() envuelve la lista y muestra una barra de progreso
            # desc = descripción que aparece junto a la barra
            
            try:
                # ─────────────────────────────────────────────────────────────
                # DESCARGAR INFORMACIÓN DE YAHOO FINANCE
                # ─────────────────────────────────────────────────────────────
                
                # Crear objeto Ticker de yfinance
                t = yf.Ticker(ticker)
                # yf.Ticker() crea un objeto que representa una acción
                # Tiene varios atributos: .info, .history, .financials, etc.
                
                # .info es un diccionario con TODA la información de la empresa
                info = t.info
                # Contiene 100+ campos: sector, industry, marketCap, employees, etc.
                
                # ─────────────────────────────────────────────────────────────
                # EXTRAER CAMPOS RELEVANTES
                # ─────────────────────────────────────────────────────────────
                
                asset_data.append({
                    'symbol': ticker,
                    
                    # .get() busca la clave, si no existe devuelve el valor por defecto
                    'sector': info.get('sector', 'ETF'),
                    # Si no tiene sector (como los ETFs), ponemos 'ETF'
                    
                    'industry': info.get('industry', 'Unknown'),
                    # Si no tiene industry, ponemos 'Unknown'
                    
                    'is_active': 1
                    # 1 = activa, 0 = inactiva (útil para filtrar luego)
                })
                
            except Exception as e:
                # Si hay cualquier error (conexión, ticker inválido, etc.)
                print(f"⚠️ Error con {ticker}: {e}")
                # Continúa con el siguiente ticker, no paramos todo
        
        # ─────────────────────────────────────────────────────────────────────
        # GUARDAR EN BASE DE DATOS
        # ─────────────────────────────────────────────────────────────────────
        
        # Convertir la lista de diccionarios a un DataFrame de pandas
        df = pd.DataFrame(asset_data)
        
        # Conectar a SQLite y guardar
        with sqlite3.connect(self.db_path) as conn:
            # 'with' garantiza que la conexión se cierre automáticamente
            
            df.to_sql('assets', conn, if_exists='replace', index=False)
            # .to_sql() convierte el DataFrame a una tabla SQL
            # - 'assets': nombre de la tabla
            # - if_exists='replace': si la tabla existe, la reemplaza
            # - index=False: no guardar el índice del DataFrame como columna
        
        print("✅ Tabla 'assets' actualizada.")

    # =========================================================================
    # MÉTODO PÚBLICO: sync_market_data (Sincronizar Datos de Mercado)
    # =========================================================================
    
    def sync_market_data(self, period="2y"):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                 PASO 2: DESCARGAR HISTÓRICO DE PRECIOS                ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Descarga el historial completo de precios OHLCV y lo guarda.         ║
        ║                                                                       ║
        ║  PARÁMETRO 'period':                                                  ║
        ║  ────────────────────                                                 ║
        ║  • "1d"  = 1 día               • "5d"  = 5 días                       ║
        ║  • "1mo" = 1 mes               • "3mo" = 3 meses                      ║
        ║  • "6mo" = 6 meses             • "1y"  = 1 año                        ║
        ║  • "2y"  = 2 años (default)    • "5y"  = 5 años                       ║
        ║  • "max" = Todo el historial disponible                               ║
        ║                                                                       ║
        ║  PROCESO DE DESCARGA:                                                 ║
        ║  ─────────────────────                                                ║
        ║                                                                       ║
        ║    1. Descargar todos los tickers de una vez (más rápido)             ║
        ║    2. Separar los datos por ticker                                    ║
        ║    3. Transformar formato (normalizar columnas)                       ║
        ║    4. Concatenar y guardar en SQLite                                  ║
        ║                                                                       ║
        ║  ESTRUCTURA DE LA TABLA 'market_data':                                ║
        ║  ────────────────────────────────────────                             ║
        ║  ┌────────┬────────────────────┬────────┬────────┬───────┬────────┬─────────┐
        ║  │ symbol │      datetime      │  open  │  high  │  low  │ close  │ volume  │
        ║  ├────────┼────────────────────┼────────┼────────┼───────┼────────┼─────────┤
        ║  │ AAPL   │ 2024-01-02         │ 185.30 │ 186.50 │ 184.20│ 185.90 │ 45000000│
        ║  │ AAPL   │ 2024-01-03         │ 185.90 │ 187.00 │ 185.00│ 186.80 │ 42000000│
        ║  │ MSFT   │ 2024-01-02         │ 374.50 │ 376.80 │ 373.20│ 375.60 │ 22000000│
        ║  └────────┴────────────────────┴────────┴────────┴───────┴────────┴─────────┘
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        print(f"--- 2. Descargando Market Data (Periodo: {period}) ---")
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 1: DESCARGAR TODOS LOS TICKERS DE UNA VEZ
        # ─────────────────────────────────────────────────────────────────────
        
        data = yf.download(
            self.tickers,           # Lista de símbolos a descargar
            period=period,          # Período de tiempo ("2y" = 2 años)
            group_by='ticker',      # Agrupar datos por ticker
            auto_adjust=True,       # Ajustar precios por splits y dividendos
            progress=True,          # Mostrar barra de progreso
            threads=True            # Usar múltiples hilos (más rápido)
        )
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 2: VALIDAR QUE OBTUVIMOS DATOS
        # ─────────────────────────────────────────────────────────────────────
        
        if data is None or data.empty:
            # Si yfinance falla (sin internet, servidor caído, etc.)
            print("❌ Error crítico: yfinance no devolvió datos. Revisa tu conexión.")
            return  # Salir de la función, no hay nada que hacer
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 3: PROCESAR CADA TICKER INDIVIDUALMENTE
        # ─────────────────────────────────────────────────────────────────────
        
        clean_data = []  # Aquí guardaremos los DataFrames limpios
        
        for ticker in self.tickers:
            try:
                # ---------------------------------------------------------
                # MANEJAR DIFERENTES ESTRUCTURAS DE DATOS
                # ---------------------------------------------------------
                # yfinance puede devolver los datos de diferentes formas
                # dependiendo de cuántos tickers descargamos
                
                # CASO A: Estructura Multi-Index (varios tickers)
                # Las columnas tienen dos niveles: (ticker, campo)
                # Ejemplo: ('AAPL', 'Close'), ('AAPL', 'Volume'), etc.
                if isinstance(data.columns, pd.MultiIndex):
                    # Verificar que el ticker esté en los datos
                    if ticker not in data.columns.levels[0]:
                        print(f"⚠️ {ticker} no se encontró en la descarga (MultiIndex).")
                        continue  # Saltar a siguiente ticker
                    
                    # Extraer solo los datos de este ticker
                    ticker_data = data[ticker].copy()
                
                # CASO B: Estructura plana (un solo ticker)
                # Las columnas son directamente: 'Open', 'High', 'Low', etc.
                elif len(self.tickers) == 1 and ticker == self.tickers[0]:
                    ticker_data = data.copy()
                
                # CASO C: Estructura desconocida
                else:
                    print(f"⚠️ Estructura de datos no coincide para {ticker}")
                    continue
                
                # ---------------------------------------------------------
                # VERIFICAR QUE HAY DATOS
                # ---------------------------------------------------------
                if ticker_data.empty:
                    print(f"⚠️ Datos vacíos para {ticker}")
                    continue
                
                # ---------------------------------------------------------
                # TRANSFORMAR Y LIMPIAR DATOS
                # ---------------------------------------------------------
                
                # Convertir el índice (fechas) a una columna
                df = ticker_data.reset_index()
                # reset_index() convierte el índice en columna 'Date'
                
                # Normalizar nombres de columnas a minúsculas
                df.columns = [c.lower() for c in df.columns]
                # Ejemplo: 'Open' -> 'open', 'Close' -> 'close'
                
                # Añadir columna con el símbolo del ticker
                df['symbol'] = ticker
                
                # Renombrar 'date' a 'datetime' para consistencia
                df = df.rename(columns={'date': 'datetime'})
                
                # ---------------------------------------------------------
                # VERIFICAR COLUMNAS REQUERIDAS
                # ---------------------------------------------------------
                required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                
                if not all(col in df.columns for col in required_cols):
                    # all() verifica que TODAS las columnas estén presentes
                    print(f"⚠️ {ticker} le faltan columnas críticas.")
                    continue
                
                # Seleccionar solo las columnas necesarias en orden correcto
                df = df[['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
                
                # Validar datos OHLCV antes de agregar
                if self._validate_ohlcv(df, ticker):
                    clean_data.append(df)
                else:
                    # Agregar de todas formas pero advertir
                    logger.warning(f"⚠️ {ticker}: datos con problemas de validación, se agregan con advertencia.")
                    clean_data.append(df)
                
            except Exception as e:
                # Si hay cualquier error procesando este ticker
                print(f"⚠️ Error procesando {ticker}: {e}")
                continue  # Continuar con el siguiente ticker
        
        # ─────────────────────────────────────────────────────────────────────
        # PASO 4: COMBINAR Y GUARDAR EN BASE DE DATOS
        # ─────────────────────────────────────────────────────────────────────
        
        if not clean_data:
            # Si ningún ticker se pudo procesar
            print("❌ No se pudo procesar ningún activo.")
            return
        
        # Concatenar todos los DataFrames en uno solo
        final_df = pd.concat(clean_data)
        # pd.concat() une múltiples DataFrames verticalmente
        
        # ─────────────────────────────────────────────────────────────────────
        # UPSERT: Combinar datos nuevos con existentes sin perder data
        # ─────────────────────────────────────────────────────────────────────
        # En lugar de 'replace' (que borra todo), hacemos upsert:
        # 1. Cargar datos existentes
        # 2. Concatenar con nuevos
        # 3. Eliminar duplicados (quedarnos con los más recientes)
        # 4. Guardar todo
        # Esto previene pérdida de datos si la descarga falla a mitad
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                existing = pd.read_sql("SELECT * FROM market_data", conn)
                combined = pd.concat([existing, final_df])
                # Eliminar duplicados por symbol + datetime, quedarnos con el último
                combined = combined.drop_duplicates(
                    subset=['symbol', 'datetime'], keep='last'
                )
                combined.to_sql('market_data', conn, if_exists='replace', index=False)
            except Exception:
                # Si la tabla no existe aún, simplemente guardar
                final_df.to_sql('market_data', conn, if_exists='replace', index=False)
            
            # Crear índice para búsquedas rápidas
            conn.execute("CREATE INDEX IF NOT EXISTS idx_md_sym_date ON market_data(symbol, datetime)")
        
        print(f"✅ Market Data inyectada: {len(final_df)} filas.")

    # =========================================================================
    # MÉTODO PÚBLICO: sync_fundamentals (Sincronizar Datos Fundamentales)
    # =========================================================================
    
    def sync_fundamentals(self):
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                 PASO 3: DESCARGAR DATOS FUNDAMENTALES                 ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║  Obtiene ratios financieros y métricas de valoración de cada empresa. ║
        ║                                                                       ║
        ║  ¿QUÉ SON LOS DATOS FUNDAMENTALES?                                    ║
        ║  ──────────────────────────────────                                   ║
        ║  Son métricas que miden la "salud financiera" de una empresa:         ║
        ║                                                                       ║
        ║  • Market Cap (Capitalización de Mercado):                            ║
        ║    → El valor total de todas las acciones de la empresa               ║
        ║    → Ejemplo: Apple = ~3 trillones USD                                ║
        ║                                                                       ║
        ║  • PE Ratio (Price/Earnings = Precio/Beneficio):                      ║
        ║    → Cuántos años de ganancias pagas por la acción                    ║
        ║    → PE = 15 significa "pagas 15 años de ganancias"                   ║
        ║    → Menor es "más barato", mayor es "más caro"                       ║
        ║                                                                       ║
        ║  • PB Ratio (Price/Book = Precio/Valor en Libros):                    ║
        ║    → Cuánto pagas vs. el valor contable de la empresa                 ║
        ║    → PB < 1 podría indicar empresa "infravalorada"                    ║
        ║                                                                       ║
        ║  • ROE (Return On Equity = Retorno sobre Capital):                    ║
        ║    → Qué tan eficiente es la empresa generando beneficios             ║
        ║    → ROE = 20% significa "genera 20 centavos por cada dólar invertido"║
        ║                                                                       ║
        ║  • Debt to Equity (Deuda/Capital):                                    ║
        ║    → Cuánta deuda tiene la empresa vs. su capital                     ║
        ║    → Alto significa más riesgo financiero                             ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        print("--- 3. Descargando Fundamentales ---")
        
        # Lista para acumular datos fundamentales
        fund_data = []
        
        # Iterar sobre cada ticker
        for ticker in tqdm(self.tickers, desc="Fundamentales"):
            try:
                # Obtener objeto Ticker de yfinance
                t = yf.Ticker(ticker)
                info = t.info
                
                # Extraer métricas fundamentales
                fund_data.append({
                    'symbol': ticker,
                    
                    # Fecha del snapshot (los fundamentales cambian trimestralmente)
                    'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                    # strftime convierte la fecha a texto formato YYYY-MM-DD
                    
                    # Capitalización de mercado (valor total de la empresa)
                    'market_cap': info.get('marketCap', 0),
                    # Ejemplo: 3,000,000,000,000 para Apple (3 trillones)
                    
                    # Ratio Precio/Beneficio (cuántos años de ganancias pagas)
                    'pe_ratio': info.get('trailingPE', 0),
                    # 'trailing' significa "de los últimos 12 meses"
                    # Ejemplo: 28 significa que pagas 28 años de ganancias actuales
                    
                    # Ratio Precio/Valor en Libros
                    'pb_ratio': info.get('priceToBook', 0),
                    # Ejemplo: 40 significa que la acción vale 40x su valor contable
                    
                    # Retorno sobre Capital (eficiencia generando beneficios)
                    'roe': info.get('returnOnEquity', 0),
                    # Ejemplo: 0.25 significa 25% de retorno sobre capital
                    
                    # Ratio Deuda/Capital (apalancamiento financiero)
                    'debt_to_equity': info.get('debtToEquity', 0)
                    # Ejemplo: 1.5 significa que tiene 1.5x más deuda que capital
                })
                
            except:
                # Si falla (empresa sin datos, API caída, etc.), continuar
                pass
        
        # Guardar en base de datos con lógica upsert
        df = pd.DataFrame(fund_data)
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                existing = pd.read_sql("SELECT * FROM fundamentals", conn)
                combined = pd.concat([existing, df])
                # Eliminar duplicados por symbol + date, quedarnos con el último
                combined = combined.drop_duplicates(
                    subset=['symbol', 'date'], keep='last'
                )
                combined.to_sql('fundamentals', conn, if_exists='replace', index=False)
            except Exception:
                # Si la tabla no existe aún, simplemente guardar
                df.to_sql('fundamentals', conn, if_exists='replace', index=False)
        
        print("✅ Fundamentales actualizados.")


# =============================================================================
# EJEMPLO DE USO (Para referencia)
# =============================================================================
#
# if __name__ == "__main__":
#     # Crear el descargador apuntando a nuestra base de datos
#     ingestor = DataIngestor("quant.db")
#     
#     # Paso 1: Actualizar información de empresas
#     ingestor.sync_assets_table()
#     
#     # Paso 2: Descargar 2 años de precios históricos
#     ingestor.sync_market_data("2y")
#     
#     # Paso 3: Actualizar ratios fundamentales
#     ingestor.sync_fundamentals()
#     
#     print("\n🎉 ¡Sincronización completa!")
#
# =============================================================================