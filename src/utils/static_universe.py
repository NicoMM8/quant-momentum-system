# =============================================================================
# STATIC_UNIVERSE.PY - UNIVERSO ESTÁTICO DE ACTIVOS
# =============================================================================
#
# ¿QUÉ ES ESTE ARCHIVO?
# ---------------------
# Contiene una lista MASIVA y CURADA de símbolos bursátiles (tickers).
# Es el "catálogo" de activos que el sistema puede analizar.
#
# ¿POR QUÉ UNA LISTA ESTÁTICA?
# ────────────────────────────
# En lugar de descubrir activos dinámicamente (ej: API de símbolos del S&P 500),
# mantenemos una lista fija por varias razones:
#
# 1. CONTROL: Sabemos exactamente qué estamos analizando
# 2. CALIDAD: Activos curados manualmente (evitamos penny stocks, ADRs raros)
# 3. VELOCIDAD: No necesitamos llamadas API para obtener la lista
# 4. REPRODUCIBILIDAD: Los backtests siempre usan el mismo universo
#
# ESTRUCTURA DEL UNIVERSO:
# ─────────────────────────
# La lista incluye ~700+ activos organizados conceptualmente en:
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ MEGA CAPS (Top 10 por capitalización)                                  │
# │ AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, BRK-B, LLY, AVGO            │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ SECTORES S&P 500                                                        │
# │ • Tecnología: AMD, CRM, ADBE, ORCL, INTC, CSCO...                       │
# │ • Financiero: JPM, BAC, WFC, GS, MS, C, AXP...                          │
# │ • Salud: UNH, JNJ, PFE, MRK, ABBV, TMO...                               │
# │ • Consumo: WMT, COST, HD, MCD, SBUX, NKE...                             │
# │ • Energía: XOM, CVX, COP, SLB, EOG...                                   │
# │ • Industriales: CAT, DE, HON, UPS, BA...                                │
# │ • Materiales: LIN, APD, FCX, NEM...                                     │
# │ • REITs: AMT, PLD, SPG, O, EQIX...                                      │
# │ • Utilities: NEE, DUK, SO, AEP...                                       │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ GROWTH/MOMENTUM (Alta volatilidad, alto potencial)                      │
# │ CRWD, SNOW, DDOG, SHOP, ROKU, COIN, MSTR, PLTR...                       │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ INTERNACIONALES (ADRs)                                                  │
# │ TSM, ASML, BABA, NVO, TM, SONY, SAP, ARM...                             │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ ETFs (Para benchmark y diversificación)                                  │
# │ • Índices: SPY, QQQ, IWM, DIA, VOO                                      │
# │ • Sectores: XLF, XLK, XLE, XLV, XLY...                                  │
# │ • Commodities: GLD, SLV                                                 │
# │ • Bonos: TLT, LQD, HYG                                                  │
# │ • Apalancados: TQQQ, SQQQ, SOXL (¡cuidado!)                             │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ ESPECULATIVOS (Meme stocks, crypto-adyacentes, etc.)                    │
# │ GME, AMC, MARA, RIOT, COIN, HOOD...                                     │
# └─────────────────────────────────────────────────────────────────────────┘
#
# ¿POR QUÉ CONVERTIMOS "." A "-"?
# ─────────────────────────────────
# Yahoo Finance usa "-" en lugar de "." para clases de acciones:
# • BRK.B → BRK-B (Berkshire Hathaway Clase B)
# • BF.B → BF-B (Brown-Forman Clase B)
# • PBR.A → PBR-A (Petrobras Clase A)
#
# =============================================================================

# src/utils/static_universe.py

# -----------------------------------------------------------------------------
# UNIVERSO MASIVO CURADO MANUALMENTE
# -----------------------------------------------------------------------------
# Esta lista contiene ~700 tickers organizados por categoría.
# Incluye: Mega caps, S&P 500 completo, Growth stocks, ADRs, ETFs.

MY_HUGE_UNIVERSE = [
    # ═══════════════════════════════════════════════════════════════════════
    # TOP 10 POR CAPITALIZACIÓN DE MERCADO
    # ═══════════════════════════════════════════════════════════════════════
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'LLY', 'AVGO', 
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR FINANCIERO
    # ═══════════════════════════════════════════════════════════════════════
    'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'SCHW',
    'BLK', 'SPGI', 'MCO', 'ICE', 'CME', 'NDAQ', 'CBOE',
    'USB', 'PNC', 'TFC', 'COF', 'AIG', 'TRV', 'ALL', 'MET', 'PRU', 'HIG',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR TECNOLOGÍA
    # ═══════════════════════════════════════════════════════════════════════
    'ORCL', 'AMD', 'CRM', 'ADBE', 'CSCO', 'ACN', 'INTU', 'IBM', 'TXN', 'QCOM',
    'AMAT', 'NOW', 'LRCX', 'ADI', 'MU', 'KLAC', 'CDNS', 'SNPS', 'MCHP', 'ON',
    'FTNT', 'PANW', 'CRWD', 'ZS', 'NET', 'DDOG', 'SNOW', 'MDB', 'OKTA', 'TWLO',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR SALUD
    # ═══════════════════════════════════════════════════════════════════════
    'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'PFE', 'ABT', 'DHR', 'BMY', 'AMGN',
    'GILD', 'VRTX', 'REGN', 'ISRG', 'SYK', 'MDT', 'ELV', 'CI', 'CVS', 'HCA',
    'ZTS', 'BDX', 'BSX', 'BIIB', 'MRNA', 'DXCM', 'ALGN',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR CONSUMO
    # ═══════════════════════════════════════════════════════════════════════
    'WMT', 'HD', 'COST', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX', 'TJX',
    'LOW', 'TGT', 'CL', 'EL', 'KMB', 'MDLZ', 'KHC', 'GIS', 'K', 'HSY',
    'DG', 'DLTR', 'ROST', 'ORLY', 'AZO', 'ULTA', 'LULU', 'CMG',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR ENERGÍA
    # ═══════════════════════════════════════════════════════════════════════
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'HAL', 'BKR', 'DVN', 'FANG',
    'MRO', 'HES', 'PSX', 'VLO', 'MPC',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR INDUSTRIAL
    # ═══════════════════════════════════════════════════════════════════════
    'CAT', 'DE', 'HON', 'UPS', 'BA', 'RTX', 'LMT', 'GD', 'NOC', 'GE',
    'UNP', 'CSX', 'FDX', 'WM', 'ETN', 'ITW', 'EMR', 'CTAS', 'ODFL',
    
    # ═══════════════════════════════════════════════════════════════════════
    # REITs (REAL ESTATE)
    # ═══════════════════════════════════════════════════════════════════════
    'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'DLR', 'WELL', 'SBAC',
    'EQR', 'AVB', 'VICI', 'VNQ',
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════
    'NEE', 'DUK', 'SO', 'AEP', 'D', 'SRE', 'XEL', 'ED', 'PCG', 'EXC',
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMUNICACIONES & MEDIA
    # ═══════════════════════════════════════════════════════════════════════
    'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'NFLX', 'CHTR', 'WBD', 'PARA',
    
    # ═══════════════════════════════════════════════════════════════════════
    # AUTOS & TRANSPORTE
    # ═══════════════════════════════════════════════════════════════════════
    'F', 'GM', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV',
    'DAL', 'UAL', 'AAL', 'LUV', 'UBER', 'LYFT', 'ABNB',
    
    # ═══════════════════════════════════════════════════════════════════════
    # GROWTH / MOMENTUM (Alto riesgo, alta recompensa)
    # ═══════════════════════════════════════════════════════════════════════
    'SHOP', 'ROKU', 'DKNG', 'COIN', 'HOOD', 'MSTR', 'PLTR', 'RBLX',
    'SQ', 'PYPL', 'AFRM', 'SOFI', 'NU', 'PATH', 'HUBS', 'TTD', 'TEAM',
    
    # ═══════════════════════════════════════════════════════════════════════
    # SEMICONDUCTORES (Ciclo de IA)
    # ═══════════════════════════════════════════════════════════════════════
    'ARM', 'SMCI', 'ANET', 'STM', 'SWKS', 'QRVO', 'CRUS', 'MRVL',
    
    # ═══════════════════════════════════════════════════════════════════════
    # ADRs INTERNACIONALES
    # ═══════════════════════════════════════════════════════════════════════
    'TSM', 'ASML', 'BABA', 'PDD', 'JD', 'BIDU', 'NVO', 'AZN', 'NVS',
    'TM', 'SONY', 'SAP', 'SHEL', 'BP', 'RIO', 'BHP', 'VALE', 'MELI',
    
    # ═══════════════════════════════════════════════════════════════════════
    # ETFs PRINCIPALES
    # ═══════════════════════════════════════════════════════════════════════
    # Índices
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'IVV', 'VTI',
    # Sectores
    'XLE', 'XLF', 'XLK', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB', 'XLC',
    # Temáticos
    'SMH', 'SOXX', 'ARKK', 'ICLN', 'TAN', 'XBI', 'IBB', 'GDX',
    # Commodities
    'GLD', 'SLV', 'USO', 'UNG',
    # Bonos
    'TLT', 'LQD', 'HYG', 'JNK', 'SHY', 'BND', 'AGG',
    # Apalancados (CUIDADO: Decay temporal)
    'TQQQ', 'SQQQ', 'SOXL', 'UPRO', 'SPXU',
    # Volatilidad
    'VIXY', 'UVXY',
    # Internacionales
    'EEM', 'VWO', 'VEA', 'EWZ', 'EWJ', 'FXI', 'MCHI', 'KWEB',
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESPECULATIVOS / MEME STOCKS
    # ═══════════════════════════════════════════════════════════════════════
    'GME', 'AMC', 'BB', 'NOK', 'MARA', 'RIOT', 'CLSK',
    
    # ═══════════════════════════════════════════════════════════════════════
    # ENERGÍAS RENOVABLES
    # ═══════════════════════════════════════════════════════════════════════
    'FSLR', 'ENPH', 'SEDG', 'RUN', 'PLUG', 'FCEL', 'BE',
    
    # ═══════════════════════════════════════════════════════════════════════
    # MATERIALES & MINERÍA
    # ═══════════════════════════════════════════════════════════════════════
    'NEM', 'FCX', 'SCCO', 'AA', 'NUE', 'STLD', 'CLF',
    'ALB', 'SQM', 'LAC', 'MP', 'CCJ', 'UEC',
    
    # ... (y muchos más en la lista completa)
]

# -----------------------------------------------------------------------------
# CORRECCIÓN DE SÍMBOLOS PARA YAHOO FINANCE
# -----------------------------------------------------------------------------
# Yahoo Finance usa "-" en lugar de "." para clases de acciones.
# Esta línea convierte automáticamente los símbolos problemáticos.

MY_HUGE_UNIVERSE = [
    t.replace('.', '-') if t in ['BRK.B', 'BF.B', 'PBR.A'] else t 
    for t in MY_HUGE_UNIVERSE
]


# =============================================================================
# EJEMPLO DE USO
# =============================================================================
#
# from src.utils.static_universe import MY_HUGE_UNIVERSE
#
# # Ver cuántos activos tenemos
# print(f"Total de activos: {len(MY_HUGE_UNIVERSE)}")
#
# # Filtrar solo ETFs (empiezan con patrones conocidos)
# etfs = [t for t in MY_HUGE_UNIVERSE if t in ['SPY', 'QQQ', 'IWM', 'XLF'...]]
#
# # Usar en el backtester
# from src.analysis.portfolio_backtest import PortfolioMomentumBacktester
# bt = PortfolioMomentumBacktester("quant.db", MY_HUGE_UNIVERSE)
# bt.run_backtest(top_n=10)
#
# =============================================================================