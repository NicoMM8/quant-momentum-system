-- Habilitar Write-Ahead Logging para mejor concurrencia y velocidad
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS assets (
    symbol TEXT PRIMARY KEY,
    sector TEXT,
    industry TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    date TEXT, -- ISO8601 YYYY-MM-DD
    market_cap REAL,
    pe_ratio REAL,   -- Price to Earnings
    pb_ratio REAL,   -- Price to Book
    roe REAL,        -- Return on Equity
    debt_to_equity REAL,
    FOREIGN KEY(symbol) REFERENCES assets(symbol),
    UNIQUE(symbol, date) ON CONFLICT REPLACE
);

-- Índices críticos para la velocidad de lectura de Pandas
CREATE INDEX IF NOT EXISTS idx_fund_date ON fundamentals(date);
CREATE INDEX IF NOT EXISTS idx_fund_symbol ON fundamentals(symbol);