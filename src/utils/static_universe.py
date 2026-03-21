MY_HUGE_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'LLY', 'AVGO',

    'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'SCHW',
    'BLK', 'SPGI', 'MCO', 'ICE', 'CME', 'NDAQ', 'CBOE',
    'USB', 'PNC', 'TFC', 'COF', 'AIG', 'TRV', 'ALL', 'MET', 'PRU', 'HIG',

    'ORCL', 'AMD', 'CRM', 'ADBE', 'CSCO', 'ACN', 'INTU', 'IBM', 'TXN', 'QCOM',
    'AMAT', 'NOW', 'LRCX', 'ADI', 'MU', 'KLAC', 'CDNS', 'SNPS', 'MCHP', 'ON',
    'FTNT', 'PANW', 'CRWD', 'ZS', 'NET', 'DDOG', 'SNOW', 'MDB', 'OKTA', 'TWLO',

    'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'PFE', 'ABT', 'DHR', 'BMY', 'AMGN',
    'GILD', 'VRTX', 'REGN', 'ISRG', 'SYK', 'MDT', 'ELV', 'CI', 'CVS', 'HCA',
    'ZTS', 'BDX', 'BSX', 'BIIB', 'MRNA', 'DXCM', 'ALGN',

    'WMT', 'HD', 'COST', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX', 'TJX',
    'LOW', 'TGT', 'CL', 'EL', 'KMB', 'MDLZ', 'KHC', 'GIS', 'K', 'HSY',
    'DG', 'DLTR', 'ROST', 'ORLY', 'AZO', 'ULTA', 'LULU', 'CMG',

    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'HAL', 'BKR', 'DVN', 'FANG',
    'MRO', 'HES', 'PSX', 'VLO', 'MPC',

    'CAT', 'DE', 'HON', 'UPS', 'BA', 'RTX', 'LMT', 'GD', 'NOC', 'GE',
    'UNP', 'CSX', 'FDX', 'WM', 'ETN', 'ITW', 'EMR', 'CTAS', 'ODFL',

    'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'DLR', 'WELL', 'SBAC',
    'EQR', 'AVB', 'VICI', 'VNQ',

    'NEE', 'DUK', 'SO', 'AEP', 'D', 'SRE', 'XEL', 'ED', 'PCG', 'EXC',

    'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'NFLX', 'CHTR', 'WBD', 'PARA',

    'F', 'GM', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV',
    'DAL', 'UAL', 'AAL', 'LUV', 'UBER', 'LYFT', 'ABNB',

    'SHOP', 'ROKU', 'DKNG', 'COIN', 'HOOD', 'MSTR', 'PLTR', 'RBLX',
    'SQ', 'PYPL', 'AFRM', 'SOFI', 'NU', 'PATH', 'HUBS', 'TTD', 'TEAM',

    'ARM', 'SMCI', 'ANET', 'STM', 'SWKS', 'QRVO', 'CRUS', 'MRVL',

    'TSM', 'ASML', 'BABA', 'PDD', 'JD', 'BIDU', 'NVO', 'AZN', 'NVS',
    'TM', 'SONY', 'SAP', 'SHEL', 'BP', 'RIO', 'BHP', 'VALE', 'MELI',

    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'IVV', 'VTI',
    'XLE', 'XLF', 'XLK', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB', 'XLC',
    'SMH', 'SOXX', 'ARKK', 'ICLN', 'TAN', 'XBI', 'IBB', 'GDX',
    'GLD', 'SLV', 'USO', 'UNG',
    'TLT', 'LQD', 'HYG', 'JNK', 'SHY', 'BND', 'AGG',
    'TQQQ', 'SQQQ', 'SOXL', 'UPRO', 'SPXU',
    'VIXY', 'UVXY',
    'EEM', 'VWO', 'VEA', 'EWZ', 'EWJ', 'FXI', 'MCHI', 'KWEB',

    'GME', 'AMC', 'BB', 'NOK', 'MARA', 'RIOT', 'CLSK',

    'FSLR', 'ENPH', 'SEDG', 'RUN', 'PLUG', 'FCEL', 'BE',

    'NEM', 'FCX', 'SCCO', 'AA', 'NUE', 'STLD', 'CLF',
    'ALB', 'SQM', 'LAC', 'MP', 'CCJ', 'UEC',

]


MY_HUGE_UNIVERSE = [
    t.replace('.', '-') if t in ['BRK.B', 'BF.B', 'PBR.A'] else t
    for t in MY_HUGE_UNIVERSE
]


