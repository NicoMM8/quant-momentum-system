# =============================================================================
# INTERFACES.PY - CONTRATOS BASE DEL SISTEMA
# =============================================================================
# 
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo define las "interfaces" o "contratos" que deben cumplir
# todas las estrategias y repositorios de datos del sistema.
#
# Piensa en una interfaz como un "contrato de trabajo": establece QUÉ
# funciones debe tener una clase, pero no CÓMO debe implementarlas.
# Es como decir "todo chef debe saber cocinar y lavar platos", pero
# cada chef puede hacerlo a su manera.
#
# ¿POR QUÉ USAMOS INTERFACES?
# ---------------------------
# 1. CONSISTENCIA: Todas las estrategias funcionan igual desde afuera
# 2. INTERCAMBIABILIDAD: Podemos cambiar una estrategia por otra fácilmente
# 3. TESTING: Podemos crear versiones "falsas" para probar el sistema
#
# ANALOGÍA SIMPLE:
# ----------------
# Imagina que tienes varios enchufes en casa. Todos siguen el mismo
# "contrato" (forma de los pines, voltaje, etc.), así que cualquier
# aparato puede conectarse a cualquier enchufe. Las interfaces hacen
# lo mismo con el código.
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------
# Estas son las herramientas que necesitamos de Python

from abc import ABC, abstractmethod
# ABC = "Abstract Base Class" (Clase Base Abstracta)
# Es la forma de Python de crear interfaces/contratos
# 'abstractmethod' marca métodos que DEBEN ser implementados por las clases hijas

from typing import List, Dict, Any
# Estas son "anotaciones de tipo" que ayudan a documentar:
# - List = una lista de elementos (ejemplo: ['AAPL', 'MSFT', 'TSLA'])
# - Dict = un diccionario (ejemplo: {'precio': 100, 'volumen': 5000})
# - Any = cualquier tipo de dato

import pandas as pd
# Pandas es la librería más popular para trabajar con datos tabulares
# Un DataFrame es como una hoja de Excel en Python


# =============================================================================
# INTERFACES DE ESTRATEGIA (Separación de Responsabilidades)
# =============================================================================
#
# El sistema tiene dos tipos de componentes estratégicos:
#
# 1. FILTROS DE UNIVERSO (IUniverseFilter):
#    → Capas 1 y 2 que reducen el universo de acciones
#    → Reciben N candidatos, retornan M mejores (M < N)
#
# 2. GENERADORES DE SEÑAL (ISignalGenerator):
#    → Capa 3 que genera señales de compra/venta
#    → Retorna un valor entre -1.0 (vender) y +1.0 (comprar)
#
# IStrategy combina ambas interfaces para compatibilidad con código existente.
# =============================================================================

class IUniverseFilter(ABC):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    INTERFAZ DE FILTRO DE UNIVERSO                         ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Para estrategias que FILTRAN candidatos (Capas 1 y 2).                   ║
    ║                                                                           ║
    ║  Ejemplo: De 500 acciones → seleccionar las 50 mejores                   ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    @abstractmethod
    def update_universe(self, candidates: List[str], data_context: Any = None) -> List[str]:
        """
        Filtrar una lista de acciones y quedarse solo con las mejores.
        
        PARÁMETROS:
        - candidates: Lista de símbolos a analizar (['AAPL', 'GOOGL', 'TSLA'])
        - data_context: Información adicional opcional
        
        RETORNA:
        - Lista filtrada con los mejores candidatos
        """
        pass


class ISignalGenerator(ABC):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    INTERFAZ DE GENERADOR DE SEÑALES                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Para estrategias que GENERAN SEÑALES de trading (Capa 3).                ║
    ║                                                                           ║
    ║  La señal es un número entre -1.0 (vender fuerte) y +1.0 (comprar fuerte)║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    @abstractmethod
    def generate_signal(self, data: Dict[str, pd.DataFrame]) -> float:
        """
        Analizar datos de mercado y decidir si comprar, vender o esperar.
        
        LA SEÑAL:
           -1.0          0.0          +1.0
             │            │             │
             ▼            ▼             ▼
          VENDER       ESPERAR      COMPRAR
          FUERTE       (Neutral)    FUERTE
        
        PARÁMETROS:
        - data: Diccionario {símbolo: DataFrame con históricos}
        
        RETORNA:
        - Un float entre -1.0 y +1.0
        """
        pass


class IStrategy(IUniverseFilter, ISignalGenerator):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    INTERFAZ COMBINADA (Backward Compatible)               ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Combina IUniverseFilter + ISignalGenerator para compatibilidad.          ║
    ║                                                                           ║
    ║  Preferir las interfaces específicas en código nuevo:                     ║
    ║  • Capas 1-2 (filtros) → heredar de IUniverseFilter                      ║
    ║  • Capa 3 (señales)    → heredar de ISignalGenerator                     ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    pass


# =============================================================================
# INTERFAZ: IDataRepository (Interfaz de Repositorio de Datos)
# =============================================================================

class IDataRepository(ABC):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    INTERFAZ DE REPOSITORIO DE DATOS                       ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta interfaz define cómo cualquier fuente de datos debe comportarse.    ║
    ║                                                                           ║
    ║  El sistema puede obtener datos de diferentes fuentes:                    ║
    ║  - Base de datos SQLite (datos históricos guardados)                      ║
    ║  - Archivos Parquet (formato eficiente para big data)                     ║
    ║  - APIs en línea (Yahoo Finance, Bloomberg, etc.)                         ║
    ║                                                                           ║
    ║  Esta interfaz garantiza que todas las fuentes de datos funcionen         ║
    ║  de la misma manera, sin importar de dónde vengan los datos.              ║
    ║                                                                           ║
    ║  ANALOGÍA:                                                                ║
    ║  Es como un "adaptador universal" de viaje. No importa si el enchufe     ║
    ║  es europeo, americano o británico, el adaptador hace que funcione       ║
    ║  de la misma manera para tu dispositivo.                                 ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    @abstractmethod
    def get_data(self, symbols: List[str], **kwargs) -> pd.DataFrame:
        """
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                              GET_DATA                                   │
        ├─────────────────────────────────────────────────────────────────────────┤
        │  PROPÓSITO:                                                             │
        │  Obtener datos de mercado para una lista de símbolos bursátiles.        │
        │                                                                         │
        │  PARÁMETROS:                                                            │
        │  - symbols: Lista de símbolos de acciones                               │
        │    Ejemplo: ['AAPL', 'MSFT', 'GOOGL']                                   │
        │                                                                         │
        │  - **kwargs: Argumentos opcionales adicionales                          │
        │    Ejemplos:                                                            │
        │    - start_date='2024-01-01'                                            │
        │    - end_date='2024-12-31'                                              │
        │    - interval='1d' (diario) o '1h' (por hora)                           │
        │                                                                         │
        │  RETORNA:                                                               │
        │  - Un DataFrame de pandas con los datos solicitados                     │
        │                                                                         │
        │  EJEMPLO DE RETORNO:                                                    │
        │  ┌──────────┬────────┬────────┬────────┬────────┬─────────┐             │
        │  │  symbol  │  open  │  high  │  low   │ close  │ volume  │             │
        │  ├──────────┼────────┼────────┼────────┼────────┼─────────┤             │
        │  │  AAPL    │ 150.00 │ 152.50 │ 149.00 │ 151.25 │ 1000000 │             │
        │  │  MSFT    │ 380.00 │ 385.00 │ 378.00 │ 383.50 │  500000 │             │
        │  └──────────┴────────┴────────┴────────┴────────┴─────────┘             │
        └─────────────────────────────────────────────────────────────────────────┘
        """
        pass