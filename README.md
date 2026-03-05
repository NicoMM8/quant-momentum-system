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

## 4. Performance Metrics & Stress Testing
*Data based on Point-in-Time historical emulation factoring all trading costs.*

**The Golden Rule:** Returns are meaningless without context. The system generated a **CAGR of 21.88%** while maintaining a strict **Maximum Drawdown (MDD) of only -14.2%**.

### Visual Performance Analysis & Research Notebook
This repository includes an interactive **Jupyter Notebook** that renders the mathematical research process, the log-scale Equity Curve, and the Underwater Drawdown charts directly in your Github browser viewer.

👉 **[View the Visual Research Notebook (`research/portfolio_simulation.ipynb`)](research/portfolio_simulation.ipynb)**

### Scenario A: The 10-Year Bull Market (2014-2024)
* **Conditions:** High liquidity, low interest rates, tech boom.
* **Performance:** **CAGR: 29.95%** | **MDD: -11.5%**
* **Insights:** The system perfectly captures late-cycle momentum, but this profitability is not representative of a full macroeconomic cycle.

### Scenario B: Full Economic Cycle & Stress Test (2004-2024)
* **Conditions:** Includes the Great Financial Crisis (2008), the sovereign debt crisis (2011), and the COVID shock (2020).
* **Performance:** **CAGR: 21.88%** | **MDD: -14.2%**
* **Insights:** This is where the Macro Regime Filter (SPY SMA200) shines. By sacrificing operations during bear markets, the system survives the worst crises, drastically reducing transaction costs and protecting base capital.

| Metric | Full Cycle Value (2004-2024) |
|--------|---------------|
| **CAGR** | **21.88%** |
| **Max Drawdown (MDD)** | **-14.2%** |
| **Sharpe Ratio** ($Sharpe = \frac{R_p - R_f}{\sigma_p}$) | **1.35** |
| **Sortino Ratio** | **1.82** |

> **Note: All displayed returns are Net.** They explicitly include dividend reinvestment (DRIP) and a strict 0.10% penalty per trade to account for broker commissions and execution slippage.

*Note: The Sharpe and Sortino ratios dramatically outperform the naive benchmark (SPY) primarily due to the severe reduction in downside volatility (Drawdown) afforded by the SMA200 Macro Regime Filter.*

## 5. Quick Start / Installation
To deploy the system locally and execute the full integration test:

```bash
# 1. Clone the repository
git clone https://github.com/NicoMM8/quant-momentum-system.git
cd quant-momentum-system

# 2. Install minimal dependencies
pip install -r requirements.txt

# 3. Formulate local database and execute basic backtest routing
# (Note: Upon first execution, the system will automatically fetch historical data via yfinance and build the local SQLite database).
python run_full_system.py
```

## 6. Technical Stack & Live Deployment
- `python 3.10+` (pandas, numpy, scipy)
- `yfinance` & Custom Wikipedia point-in-time extraction.
- **Live MT5 Bridge**: The system integrates directly via MetaTrader 5's Python API (`src/execution/mt5_connector.py`) to replicate the exact state machine of the simulated backend into a direct live broker environment (e.g., Admiral Markets).

## 7. Project Architecture
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

## 8. Future Work & Known Limitations
This project serves as a foundational architecture, but professional environments require continuous iteration. Current engineering limitations include:

1. **Intraday Scalability**: The system currently utilizes SQLite for daily resolution data. A migration to a time-series database (e.g., InfluxDB or KDB+) would be required to scale towards high-frequency or tick-level intraday execution.
2. **Fractional Position Sizing**: The `MT5Connector` currently rounds down to the nearest whole `volume_step`. Integrating native fractional share logic would drastically improve portfolio tracking error on smaller capital allocations.
3. **Advanced Volatility Modeling**: The current implementation relies on a static Average True Range (ATR) threshold limit. A transition to a robust statistical model, such as GARCH(1,1), would allow for superior dynamic volatility clustering estimation.
4. **Interactive Dashboarding**: While the current visual analysis is handled via Jupyter Notebooks (`research/portfolio_simulation.ipynb`), an interactive web frontend utilizing **Streamlit** is planned for future sprints. This will provide a no-code interface for backtest parameter tuning and live result rendering.
