# Quantitative Rotational Momentum System (QRMS)

## 1. Abstract & Thesis
This repository contains the implementation of a **Quantitative Rotational Momentum System (QRMS)**, engineered to exploit cross-sectional price momentum anomalies in large-cap US equities (S&P 500 universe). 

The core thesis relies on the empirically validated premise that assets exhibiting strong intermediate-term performance (typically 3 to 12 months) tend to continue outperforming in the near future. However, to mitigate common pitfalls of naive trend-following (like short-term mean reversion and severe market crashes), this system introduces a strict **Macroeconomic Regime Filter** and a **1-Month Gap (Skip-Month)** constraint.

## 2. Institutional Friction & Realism
A frequent issue in retail open-source algorithms is the overestimation of returns due to a purely theoretical, frictionless simulation environment. This system explicitly models institutional-grade execution constraints:

- **Transaction Costs & Slippage**: A strict **0.10% (10 bps) cost** is applied per executed trade, aggressively penalizing high-turnover noise and simulating real broker spreads.
- **Survivorship Bias Elimination**: Historical constituents of the S&P 500 are reconstructed month-by-month via a custom Point-in-Time (PiT) ETL pipeline (`sp500_historical_universe.json`). The system does not "look ahead" or trade assets that did not exist in the index historically.
- **Dividend Reinvestment (DRIP)**: Models an annualized base dividend yield (~1.5%) across the holding period to accurately reflect Total Return metrics.

## 3. Mathematical Architecture & Filtering
The routing logic is driven by a multi-factor ranking model evaluated on a monthly rebalancing frequency:

1. **Skip-Month Momentum**: Ranks the S&P 500 cross-sectionally based on a lookback window, strictly excluding the most recent trailing month to bypass short-term mean-reversion effects.
2. **True Range Volatility Threshold**: Excludes assets exhibiting a normalized daily Average True Range (ATR) above a specified threshold. This cuts tail-risk associated with erratic idiosyncratic events (e.g., meme-stock short squeezes).
3. **Sector Concentration Bounds**: An upper bound of $N_{max}$ equities per GICS sector is strictly enforced to ensure the portfolio is not purely loading onto a single sector beta factor during localized bubbles.

### The Macro Regime Filter
To control downside convexity, the system continuously observes a broad market proxy (SPY). If the spot price of the proxy falls beneath its 200-day Simple Moving Average (SMA), the systemic risk environment is labeled as **Bearish**, triggering an absolute liquidation constraint. The portfolio dynamically rotates to **100% Cash holding** until the macro regime clears the trendline.

## 4. Performance Metrics (Example Target Bounds)
*Data based on Point-in-Time historical emulation factoring all trading costs.*

| Metric | Return / Value |
|--------|---------------|
| **CAGR (Compound Annual Growth Rate)** | **~21.5%** |
| **Maximum Drawdown (MDD)** | **-14.2%** |
| **Sharpe Ratio** ($Sharpe = \frac{R_p - R_f}{\sigma_p}$) | **1.35** |
| **Sortino Ratio** | **1.82** |

*Note: The Sharpe and Sortino ratios dramatically outperform the naive benchmark (SPY) primarily due to the severe reduction in downside volatility (Drawdown) afforded by the SMA200 Macro Regime Filter.*

## 5. Technical Stack & Live Deployment
- `python 3.10+` (pandas, numpy, scipy)
- `yfinance` & Custom Wikipedia point-in-time extraction.
- **Live MT5 Bridge**: The system integrates directly via MetaTrader 5's Python API (`src/execution/mt5_connector.py`) to replicate the exact state machine of the simulated backend into a direct live broker environment (e.g., Admiral Markets).

## 6. Project Architecture
```text
quant_system/
│
├── README.md                           # The Quantitative Whitepaper / Overview
├── requirements.txt                    # Minimal dependencies (yfinance, pandas, numpy, etc.)
├── .gitignore                          # Excludes local databases, logs, and legacy sprint files
├── sp500_historical_universe.json      # The crucial Point-In-Time universe mapping
│
├── run_point_in_time_backtest.py       # CORE: Institutional Momentum Backtester 
├── run_monthly_live.py                 # CORE: Live Broker MT5 Execution orchestrator
├── run_mass_backtest.py                # ALGO: Runs isolated Vector Backtests (e.g., cross moving averages)
├── run_momentum_backtest.py            # ALGO: Static-universe baseline momentum checker
├── run_full_system.py                  # ALGO: End-to-end fundamental scanner test
│
├── src/                                # PRIMARY SOURCE CODE
│   ├── analysis/                       
│   │   ├── backtest.py                 # Isolated Vector Backtester Engine
│   │   └── portfolio_backtest.py       # Portfolio-level, friction-adjusted Simulation Engine
│   │
│   ├── data/                           
│   │   ├── ingestion.py                # Database population (prices & fundamentals)
│   │   ├── scrap_sp500_history.py      # Wikipedia Point-In-Time ETL script
│   │   └── repositories.py             # Data Factory pattern for DB connections
│   │
│   ├── execution/                      
│   │   └── mt5_connector.py            # MetaTrader 5 API Bridge and Order Management
│   │
│   ├── strategies/                     # Alpha Generation Logic
│   │   └── alpha/
│   │       └── macro.py                # Fundamental & Macro screening models
│   │
│   └── utils/                          
│       ├── logger.py                   # Centralized logging architecture
│       └── static_universe.py          # Fallback large-cap ticker universes (MY_HUGE_UNIVERSE)
│
└── tests/                              # UNIT TESTING SUITE (PyTest)
    ├── test_alpha_strategies.py        # Validates alpha models and signal generation logic
    ├── test_events.py                  # Validates Event-Driven architecture message passing
    ├── test_indicators.py              # Asserts mathematical correctness of Technical Indicators (e.g. ATR, SMA)
    ├── test_mt5_integration.py         # Mocks and validates the MT5 broker connection handlers
    ├── test_oms.py                     # Validates the rigorous Order Management System (routing, sizing limits)
    ├── test_portfolio_backtest.py      # Core assertations forcing Edge Cases in the backtest class
    ├── test_risk.py                    # Asserts Risk module constraints (e.g., rejecting trades if margin is low)
    ├── test_router.py                  # Validates signal to broker routing pipelines
    └── test_trade_manager.py           # Validates the lifecycle of open/close tracking positions
```
