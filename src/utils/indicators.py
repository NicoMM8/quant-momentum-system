# =============================================================================
# INDICATORS.PY - INDICADORES TÉCNICOS PARA ANÁLISIS DE MERCADO
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Este archivo contiene las fórmulas matemáticas para calcular indicadores
# técnicos que los traders usan para analizar gráficos y predecir movimientos.
#
# ¿QUÉ ES EL ANÁLISIS TÉCNICO?
# ----------------------------
# Es el estudio de gráficos de precios para predecir movimientos futuros.
# Se basa en la idea de que "el precio lo descuenta todo" y que los patrones
# del pasado tienden a repetirse.
#
# ANALOGÍA SIMPLE:
# ----------------
# Es como un médico que mide tu temperatura, presión y pulso.
# Los "signos vitales" del mercado son los indicadores técnicos:
# - RSI = ¿El mercado está "febril" (sobrecomprado)?
# - EMA = ¿Cuál es la tendencia general (subiendo/bajando)?
# - ATR = ¿Qué tan "nervioso" está el mercado (volatilidad)?
# - RVOL = ¿Hay más "presión" de lo normal (volumen)?
#
# ¿QUÉ SIGNIFICA "VECTORIZADO"?
# -----------------------------
# "Vectorizado" significa que calculamos TODO de una vez, no fila por fila.
# 
# Ejemplo NO vectorizado (LENTO):
#   for i in range(len(datos)):
#       resultado[i] = datos[i] * 2
#
# Ejemplo vectorizado (RÁPIDO):
#   resultado = datos * 2
#
# NumPy y Pandas están optimizados para operaciones vectorizadas.
# Pueden ser 100x más rápidos que usar bucles for.
#
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTACIONES
# -----------------------------------------------------------------------------

import pandas as pd
# Pandas es la librería principal para análisis de datos en Python
# pd.Series = una columna de datos (como una lista con índice)

import numpy as np
# NumPy es la librería de cálculo numérico
# np.nan = "Not a Number" (valor especial para datos faltantes)


# =============================================================================
# CLASE: TechnicalMath (Matemáticas Técnicas)
# =============================================================================

class TechnicalMath:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                    MOTOR DE CÁLCULO TÉCNICO VECTORIZADO                   ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Esta clase contiene las fórmulas para calcular indicadores técnicos.     ║
    ║                                                                           ║
    ║  Todos los métodos son ESTÁTICOS (no necesitan crear un objeto).          ║
    ║  Simplemente llamas: TechnicalMath.rsi(precios)                           ║
    ║                                                                           ║
    ║  INDICADORES DISPONIBLES:                                                 ║
    ║  ─────────────────────────                                                ║
    ║  • RSI: Mide si algo está sobrecomprado/sobrevendido                      ║
    ║  • EMA: Media móvil que da más peso a datos recientes                     ║
    ║  • ATR: Mide la volatilidad (qué tan bruscos son los movimientos)         ║
    ║  • RVOL: Compara el volumen actual con el promedio                        ║
    ║                                                                           ║
    ║  GRÁFICO DE INDICADORES:                                                  ║
    ║  ────────────────────────                                                 ║
    ║                                                                           ║
    ║  PRECIO (con EMA 200)         │  RSI (0-100)                              ║
    ║  ──────────────────────       │  ─────────────                            ║
    ║  150 ┤     ╭────╮             │  70 ┤----SOBRECOMPRADO----                ║
    ║      │   ╭╯    ╰╮            │     │      ╭─╮                            ║
    ║  140 ┤ ╭╯       │  ←Precio   │  50 ┤─────╯  ╰────                        ║
    ║      │╱ ────────── ←EMA      │     │                                     ║
    ║  130 ┤                       │  30 ┤----SOBREVENDIDO----                 ║
    ║      ╰──────────────→ Tiempo │     ╰──────────────→ Tiempo               ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    
    # =========================================================================
    # INDICADOR 1: RSI (Relative Strength Index)
    # =========================================================================
    
    @staticmethod  # @staticmethod indica que no necesita 'self' ni crear objeto
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                 RSI - RELATIVE STRENGTH INDEX                         ║
        ║                 (Índice de Fuerza Relativa)                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║                                                                       ║
        ║  ¿QUÉ MIDE?                                                           ║
        ║  ──────────                                                           ║
        ║  El RSI mide la VELOCIDAD y MAGNITUD de los cambios de precio.        ║
        ║  Indica si una acción ha subido "demasiado rápido" (sobrecomprada)    ║
        ║  o ha bajado "demasiado rápido" (sobrevendida).                       ║
        ║                                                                       ║
        ║  ESCALA: 0 a 100                                                      ║
        ║  ───────────────                                                      ║
        ║                                                                       ║
        ║     100 ┤ ══════════════ MÁXIMO SOBRECOMPRADO                         ║
        ║         │                                                             ║
        ║      70 ┤ -------------- ZONA DE SOBRECOMPRA (vender?)                ║
        ║         │  ↑ Considerar VENDER cuando RSI > 70                        ║
        ║         │                                                             ║
        ║      50 ┤ ============== NEUTRAL                                      ║
        ║         │                                                             ║
        ║      30 ┤ -------------- ZONA DE SOBREVENTA (comprar?)                ║
        ║         │  ↓ Considerar COMPRAR cuando RSI < 30                       ║
        ║       0 ┤ ══════════════ MÁXIMO SOBREVENDIDO                          ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • RSI > 70: "Sobrecomprado" - El precio subió mucho, puede bajar     ║
        ║  • RSI < 30: "Sobrevendido" - El precio bajó mucho, puede subir       ║
        ║  • RSI ≈ 50: Neutral, sin señal clara                                 ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  RSI = 100 - (100 / (1 + RS))                                         ║
        ║                                                                       ║
        ║  Donde RS = Promedio de Ganancias / Promedio de Pérdidas              ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Si en los últimos 14 días, las ganancias promediaron 2%              ║
        ║  y las pérdidas promediaron 1%, entonces:                             ║
        ║  RS = 2 / 1 = 2                                                       ║
        ║  RSI = 100 - (100 / (1 + 2)) = 100 - 33.33 = 66.67                    ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  ─────────────                                                        ║
        ║  • series: Serie de precios de cierre                                 ║
        ║  • period: Número de períodos (por defecto 14, estándar de Wilder)    ║
        ║                                                                       ║
        ║  RETORNA:                                                             ║
        ║  ──────────                                                           ║
        ║  Serie de valores RSI (0-100) para cada fecha                         ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # PASO 1: Calcular el cambio diario de precios
        delta = series.diff()
        # .diff() calcula la diferencia entre cada valor y el anterior
        # Ejemplo: [100, 102, 101, 103] -> [NaN, +2, -1, +2]
        
        # PASO 2: Separar ganancias y pérdidas
        # ─────────────────────────────────────
        
        # Ganancias: solo los cambios positivos (los negativos se vuelven 0)
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        # .where(condición, valor_si_falso) mantiene los positivos, pone 0 en negativos
        # .ewm() = Exponential Weighted Mean (Media Ponderada Exponencial)
        # alpha=1/period es la fórmula de Wilder para el suavizado
        
        # Pérdidas: solo los cambios negativos, convertidos a positivos
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        # El signo negativo convierte las pérdidas en números positivos
        # Ejemplo: -2 se convierte en +2
        
        # PASO 3: Calcular RS (Relative Strength)
        # ─────────────────────────────────────────
        
        # IMPORTANTE: Protección contra división por cero
        # Si no hay pérdidas (loss = 0), la división daría infinito
        rs = gain / loss.replace(0, np.nan)
        # .replace(0, np.nan) cambia los ceros por NaN para evitar división por cero
        
        # PASO 4: Calcular RSI final
        # ─────────────────────────────
        rsi = 100 - (100 / (1 + rs))
        
        # PASO 5: Manejar casos especiales
        # ─────────────────────────────────
        # Si loss = 0, rs = NaN, y rsi = NaN
        # En este caso, RSI debería ser 100 (solo hubo ganancias)
        return rsi.fillna(100)
        # .fillna(100) reemplaza los NaN por 100

    # =========================================================================
    # INDICADOR 2: EMA (Exponential Moving Average)
    # =========================================================================
    
    @staticmethod
    def ema(series: pd.Series, period: int = 200) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                 EMA - EXPONENTIAL MOVING AVERAGE                      ║
        ║                 (Media Móvil Exponencial)                             ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║                                                                       ║
        ║  ¿QUÉ ES UNA MEDIA MÓVIL?                                             ║
        ║  ──────────────────────────                                           ║
        ║  Es el promedio de los últimos N precios. Se llama "móvil" porque     ║
        ║  se va moviendo con el tiempo (siempre usa los últimos N días).       ║
        ║                                                                       ║
        ║  ¿POR QUÉ "EXPONENCIAL"?                                              ║
        ║  ─────────────────────────                                            ║
        ║  La EMA da MÁS PESO a los datos recientes y MENOS a los antiguos.     ║
        ║  Reacciona más rápido a cambios que una media simple (SMA).           ║
        ║                                                                       ║
        ║  COMPARACIÓN SMA vs EMA:                                              ║
        ║  ─────────────────────────                                            ║
        ║                                                                       ║
        ║  Datos: [10, 12, 15, 20, 25]                                          ║
        ║                                                                       ║
        ║  SMA (Simple): (10 + 12 + 15 + 20 + 25) / 5 = 16.4                    ║
        ║    → Todos los valores pesan igual (20%)                              ║
        ║                                                                       ║
        ║  EMA (Exponencial): Más peso al 25, menos al 10                       ║
        ║    → [10×5%, 12×10%, 15×15%, 20×25%, 25×45%] ≈ 20.3                   ║
        ║    → Reacciona más rápido al cambio reciente                          ║
        ║                                                                       ║
        ║  USO EN TRADING:                                                      ║
        ║  ─────────────────                                                    ║
        ║  • EMA 200: Tendencia de largo plazo (muy popular)                    ║
        ║  • EMA 50: Tendencia de mediano plazo                                 ║
        ║  • EMA 20: Tendencia de corto plazo                                   ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • Precio > EMA → Tendencia ALCISTA (el precio está arriba del prom.)║
        ║  • Precio < EMA → Tendencia BAJISTA (el precio está abajo del prom.) ║
        ║                                                                       ║
        ║  GRÁFICO:                                                             ║
        ║  ──────────                                                           ║
        ║                                                                       ║
        ║      │    ╭───── Precio (más volátil)                                 ║
        ║      │  ╭╯  ╲                                                         ║
        ║      │╭╯     ╲╭─                                                      ║
        ║      ├────────────── EMA 200 (suave, tendencia)                       ║
        ║      │                                                                ║
        ║      └─────────────────→ Tiempo                                       ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  ─────────────                                                        ║
        ║  • series: Serie de precios                                           ║
        ║  • period: Número de períodos (200 = largo plazo)                     ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        return series.ewm(span=period, adjust=False).mean()
        # .ewm() = Exponential Weighted functions
        # span=period indica el número de períodos para el cálculo
        # adjust=False usa el método recursivo (más eficiente)
        # .mean() calcula la media ponderada

    # =========================================================================
    # INDICADOR 3: ATR (Average True Range)
    # =========================================================================
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                  ATR - AVERAGE TRUE RANGE                             ║
        ║                  (Rango Verdadero Promedio)                           ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║                                                                       ║
        ║  ¿QUÉ MIDE?                                                           ║
        ║  ──────────                                                           ║
        ║  El ATR mide la VOLATILIDAD del mercado, es decir, qué tan grandes    ║
        ║  son los movimientos de precio típicamente.                           ║
        ║                                                                       ║
        ║  No indica dirección (arriba/abajo), solo MAGNITUD del movimiento.    ║
        ║                                                                       ║
        ║  ANALOGÍA:                                                            ║
        ║  ──────────                                                           ║
        ║  Es como medir el "temperamento" del mercado:                         ║
        ║  • ATR alto: Mercado "nervioso", movimientos grandes                  ║
        ║  • ATR bajo: Mercado "calmado", movimientos pequeños                  ║
        ║                                                                       ║
        ║  ¿QUÉ ES EL "TRUE RANGE"?                                             ║
        ║  ──────────────────────────                                           ║
        ║  Es el mayor de estos tres valores:                                   ║
        ║                                                                       ║
        ║  1. High - Low (rango del día actual)                                 ║
        ║     │ High ─────┬─────                                                ║
        ║     │           │ Rango                                               ║
        ║     │ Low  ─────┴─────                                                ║
        ║                                                                       ║
        ║  2. |High - Close ayer| (gap hacia arriba)                            ║
        ║     │ High HOY ───┐                                                   ║
        ║     │             │ Gap                                               ║
        ║     │ Close AYER ─┘                                                   ║
        ║                                                                       ║
        ║  3. |Low - Close ayer| (gap hacia abajo)                              ║
        ║     │ Close AYER ─┐                                                   ║
        ║     │             │ Gap                                               ║
        ║     │ Low HOY ────┘                                                   ║
        ║                                                                       ║
        ║  USO EN TRADING:                                                      ║
        ║  ─────────────────                                                    ║
        ║  • Calcular Stop Loss: SL = Precio - (2 × ATR)                        ║
        ║  • Medir riesgo: Mayor ATR = mayor riesgo                             ║
        ║  • Detectar cambios de régimen: ATR creciente = volatilidad sube      ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  Si AAPL tiene ATR(14) = $3.50                                        ║
        ║  Significa que en promedio, AAPL se mueve $3.50 por día               ║
        ║  Un stop loss de 2×ATR = $7 sería "2 días de movimiento normal"       ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  ─────────────                                                        ║
        ║  • high: Serie de precios máximos                                     ║
        ║  • low: Serie de precios mínimos                                      ║
        ║  • close: Serie de precios de cierre                                  ║
        ║  • period: Número de períodos para el promedio (14 es estándar)       ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # PASO 1: Calcular los tres componentes del True Range
        # ─────────────────────────────────────────────────────
        
        # Componente 1: High - Low (rango del día)
        h_l = high - low
        
        # Componente 2: |High - Close de ayer| (gap alcista)
        h_pc = (high - close.shift(1)).abs()
        # .shift(1) desplaza la serie una posición (obtiene el valor de ayer)
        # .abs() convierte a valor absoluto (siempre positivo)
        
        # Componente 3: |Low - Close de ayer| (gap bajista)
        l_pc = (low - close.shift(1)).abs()
        
        # PASO 2: True Range = máximo de los tres
        # ─────────────────────────────────────────
        tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
        # pd.concat() une las tres series en un DataFrame
        # .max(axis=1) encuentra el máximo de cada fila
        
        # PASO 3: ATR = media móvil exponencial del True Range
        # ─────────────────────────────────────────────────────
        return tr.ewm(alpha=1/period, adjust=False).mean()
        # Usamos EWM con alpha de Wilder para suavizar

    # =========================================================================
    # INDICADOR 4: RVOL (Relative Volume)
    # =========================================================================
    
    @staticmethod
    def relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        ╔═══════════════════════════════════════════════════════════════════════╗
        ║                  RVOL - RELATIVE VOLUME                               ║
        ║                  (Volumen Relativo)                                   ║
        ╠═══════════════════════════════════════════════════════════════════════╣
        ║                                                                       ║
        ║  ¿QUÉ MIDE?                                                           ║
        ║  ──────────                                                           ║
        ║  Compara el volumen actual con el volumen promedio reciente.          ║
        ║  Indica si hay MÁS o MENOS actividad de lo normal.                    ║
        ║                                                                       ║
        ║  ¿QUÉ ES EL VOLUMEN?                                                  ║
        ║  ─────────────────────                                                ║
        ║  El volumen es la cantidad de acciones que se compraron/vendieron     ║
        ║  en un período. Alto volumen = mucha actividad de trading.            ║
        ║                                                                       ║
        ║  FÓRMULA:                                                             ║
        ║  ──────────                                                           ║
        ║  RVOL = Volumen Actual / Promedio de Volumen (últimos N días)         ║
        ║                                                                       ║
        ║  INTERPRETACIÓN:                                                      ║
        ║  ────────────────                                                     ║
        ║  • RVOL = 1.0: Volumen normal (igual al promedio)                     ║
        ║  • RVOL = 2.0: El doble de volumen de lo normal                       ║
        ║  • RVOL = 0.5: La mitad de volumen de lo normal                       ║
        ║                                                                       ║
        ║  ¿POR QUÉ ES IMPORTANTE?                                              ║
        ║  ──────────────────────────                                           ║
        ║  El volumen confirma movimientos de precio:                           ║
        ║                                                                       ║
        ║  • Precio sube + RVOL alto → Movimiento FUERTE (muchos comprando)     ║
        ║  • Precio sube + RVOL bajo → Movimiento DÉBIL (pocos comprando)       ║
        ║  • Precio baja + RVOL alto → Venta FUERTE (muchos vendiendo)          ║
        ║                                                                       ║
        ║  Es como la diferencia entre:                                         ║
        ║  • Una manifestación con 10 personas (poco volumen)                   ║
        ║  • Una manifestación con 10,000 personas (alto volumen)               ║
        ║  ¡La segunda tiene más "peso" y probabilidad de éxito!                ║
        ║                                                                       ║
        ║  EJEMPLO:                                                             ║
        ║  ──────────                                                           ║
        ║  AAPL promedia 50 millones de acciones/día                            ║
        ║  Hoy se negociaron 100 millones                                       ║
        ║  RVOL = 100M / 50M = 2.0 (el doble de lo normal)                      ║
        ║  → ¡Algo importante está pasando!                                     ║
        ║                                                                       ║
        ║  PARÁMETROS:                                                          ║
        ║  ─────────────                                                        ║
        ║  • volume: Serie de volúmenes diarios                                 ║
        ║  • period: Días para calcular el promedio (20 = 1 mes bursátil)       ║
        ╚═══════════════════════════════════════════════════════════════════════╝
        """
        # PASO 1: Calcular el promedio de volumen de los últimos N días
        # ─────────────────────────────────────────────────────────────
        avg_vol = volume.rolling(window=period).mean()
        # .rolling(window=N) crea una "ventana deslizante" de N elementos
        # .mean() calcula el promedio de esa ventana
        
        # PASO 2: Dividir volumen actual entre promedio
        # ─────────────────────────────────────────────
        # IMPORTANTE: Protección contra división por cero
        return volume / avg_vol.replace(0, 1)
        # .replace(0, 1) cambia ceros por unos para evitar división por cero
        # Si avg_vol = 0, resultaría volume/1 = volume (no infinito)


# =============================================================================
# EJEMPLO DE USO (Para referencia)
# =============================================================================
#
# import pandas as pd
# 
# # Supongamos que tenemos datos de AAPL
# datos_aapl = pd.DataFrame({
#     'close': [150, 152, 151, 153, 155, 154, 156, 158, 157, 159],
#     'high':  [151, 153, 152, 154, 156, 155, 157, 159, 158, 160],
#     'low':   [149, 151, 150, 152, 154, 153, 155, 157, 156, 158],
#     'volume': [50e6, 45e6, 55e6, 60e6, 70e6, 40e6, 65e6, 80e6, 50e6, 75e6]
# })
# 
# # Calcular indicadores
# rsi = TechnicalMath.rsi(datos_aapl['close'])
# ema_200 = TechnicalMath.ema(datos_aapl['close'], period=200)
# atr = TechnicalMath.atr(datos_aapl['high'], datos_aapl['low'], datos_aapl['close'])
# rvol = TechnicalMath.relative_volume(datos_aapl['volume'])
# 
# print(f"RSI actual: {rsi.iloc[-1]:.1f}")  # Ejemplo: RSI actual: 65.3
# print(f"ATR actual: ${atr.iloc[-1]:.2f}")  # Ejemplo: ATR actual: $2.15
# print(f"RVOL actual: {rvol.iloc[-1]:.2f}x")  # Ejemplo: RVOL actual: 1.50x
#
# =============================================================================