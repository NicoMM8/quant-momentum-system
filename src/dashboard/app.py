"""
═══════════════════════════════════════════════════════════════════════════════
  Quant System Pro — Dashboard v2.0
  
  Ejecutar: streamlit run src/dashboard/app.py
  
  Mejoras sobre v1:
  - Carga datos directamente desde SQLite (sin depender de CSV)
  - Vista de portafolio con curva de equity
  - Panel de métricas de riesgo (Sharpe, Sortino, Max Drawdown)
  - Navegación por pestañas (Overview, Asset, Risk)
  - KPIs dinámicos
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Quant System Pro",
    page_icon="⚡",
)

# Rutas
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "data", "market_data.db")
EXPORT_DIR = os.path.join(BASE_DIR, "data_export")


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_from_db(db_path: str):
    """Carga datos directamente desde SQLite."""
    if not os.path.exists(db_path):
        return None, None
    
    try:
        conn = sqlite3.connect(db_path)
        market_df = pd.read_sql("SELECT * FROM market_data ORDER BY datetime", conn)
        market_df['datetime'] = pd.to_datetime(market_df['datetime'])
        
        # Intentar cargar trades si existen
        try:
            trades_df = pd.read_sql("SELECT * FROM trades", conn)
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        except Exception:
            trades_df = pd.DataFrame()
        
        conn.close()
        return market_df, trades_df
    except Exception:
        return None, None


def load_from_csv(export_dir: str):
    """Fallback: cargar desde CSV exports."""
    try:
        market_df = pd.read_csv(os.path.join(export_dir, "market_data.csv"))
        market_df['datetime'] = pd.to_datetime(market_df['datetime'])
        
        trades_path = os.path.join(export_dir, "trades_log.csv")
        if os.path.exists(trades_path):
            trades_df = pd.read_csv(trades_path)
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        else:
            trades_df = pd.DataFrame()
        
        return market_df, trades_df
    except FileNotFoundError:
        return None, None


def load_data():
    """Carga datos: primero intenta DB, luego CSV como fallback."""
    market_data, trade_data = load_from_db(DB_PATH)
    if market_data is None:
        market_data, trade_data = load_from_csv(EXPORT_DIR)
    return market_data, trade_data


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULOS DE RIESGO
# ─────────────────────────────────────────────────────────────────────────────

def calculate_risk_metrics(returns: pd.Series):
    """Calcula métricas de riesgo a partir de retornos diarios."""
    if returns.empty or len(returns) < 2:
        return {}
    
    ann_factor = 252
    mean_ret = returns.mean() * ann_factor
    std_ret = returns.std() * np.sqrt(ann_factor)
    
    # Sharpe
    sharpe = mean_ret / std_ret if std_ret > 0 else 0.0
    
    # Sortino (solo downside deviation)
    downside = returns[returns < 0]
    down_std = downside.std() * np.sqrt(ann_factor)
    sortino = mean_ret / down_std if down_std > 0 else 0.0
    
    # Max Drawdown
    cum = (1 + returns).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    # Calmar
    calmar = mean_ret / abs(max_dd) if max_dd != 0 else 0.0
    
    return {
        'Retorno Anualizado': f"{mean_ret:.2%}",
        'Volatilidad Anual': f"{std_ret:.2%}",
        'Sharpe Ratio': f"{sharpe:.2f}",
        'Sortino Ratio': f"{sortino:.2f}",
        'Max Drawdown': f"{max_dd:.2%}",
        'Calmar Ratio': f"{calmar:.2f}",
    }


def calculate_trade_metrics(trades_df: pd.DataFrame):
    """Calcula métricas de trading."""
    if trades_df.empty or 'pnl_pct' not in trades_df.columns:
        return {}
    
    total = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    
    win_rate = len(winners) / total * 100 if total > 0 else 0
    avg_win = winners['pnl_pct'].mean() * 100 if not winners.empty else 0
    avg_loss = losers['pnl_pct'].mean() * 100 if not losers.empty else 0
    profit_factor = abs(winners['pnl_pct'].sum() / losers['pnl_pct'].sum()) if not losers.empty and losers['pnl_pct'].sum() != 0 else float('inf')
    
    return {
        'Total Trades': total,
        'Win Rate': f"{win_rate:.1f}%",
        'Avg Win': f"{avg_win:.2f}%",
        'Avg Loss': f"{avg_loss:.2f}%",
        'Profit Factor': f"{profit_factor:.2f}",
        'Best Trade': f"{trades_df['pnl_pct'].max() * 100:.2f}%",
        'Worst Trade': f"{trades_df['pnl_pct'].min() * 100:.2f}%",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .stMetric { 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 0.75rem;
        border: 1px solid rgba(100, 149, 237, 0.2);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UI PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

st.title("⚡ Quant System Pro — Dashboard v2.0")

market_data, trade_data = load_data()

if market_data is None:
    st.error("❌ No se encontraron datos.")
    st.info("Opciones:\n1. Coloca `market_data.db` en `data/`\n2. Ejecuta `python run_simulation_export.py` para CSV")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Configuración")
symbols = sorted(market_data['symbol'].unique())
selected_symbol = st.sidebar.selectbox("Activo", symbols)

# Fuente de datos indicator
source = "🗄️ SQLite" if os.path.exists(DB_PATH) else "📁 CSV Export"
st.sidebar.caption(f"Fuente: {source}")
st.sidebar.caption(f"Activos disponibles: {len(symbols)}")

date_range = market_data['datetime'].agg(['min', 'max'])
st.sidebar.caption(f"Rango: {date_range['min'].strftime('%Y-%m-%d')} → {date_range['max'].strftime('%Y-%m-%d')}")

if st.sidebar.button("🔄 Recargar datos"):
    st.cache_data.clear()
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab_overview, tab_asset, tab_risk = st.tabs(["📊 Overview", f"📈 {selected_symbol}", "🛡️ Risk Metrics"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW — Portfolio-level view
# ═══════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.subheader("📊 Vista de Portafolio")
    
    # Portfolio equity curve (equal-weight all symbols)
    pivot = market_data.pivot_table(
        index='datetime', columns='symbol', values='close', aggfunc='last'
    ).ffill()
    
    # Normalize each asset to 100 at start
    normalized = pivot / pivot.iloc[0] * 100
    
    # Equal-weight portfolio
    portfolio_eq = normalized.mean(axis=1)
    portfolio_returns = portfolio_eq.pct_change().dropna()
    
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    total_return = (portfolio_eq.iloc[-1] / portfolio_eq.iloc[0] - 1) * 100
    
    cum_ret = (1 + portfolio_returns).cumprod()
    max_dd = ((cum_ret - cum_ret.cummax()) / cum_ret.cummax()).min() * 100
    
    ann_vol = portfolio_returns.std() * np.sqrt(252) * 100
    sharpe = (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252) if portfolio_returns.std() > 0 else 0
    
    c1.metric("Retorno Total", f"{total_return:.1f}%")
    c2.metric("Max Drawdown", f"{max_dd:.1f}%")
    c3.metric("Volatilidad Anual", f"{ann_vol:.1f}%")
    c4.metric("Sharpe Ratio", f"{sharpe:.2f}")
    
    # Equity curve chart
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=portfolio_eq.index, y=portfolio_eq.values,
        mode='lines', name='Portfolio (Equal Weight)',
        line=dict(color='#4fc3f7', width=2.5),
        fill='tozeroy', fillcolor='rgba(79,195,247,0.1)'
    ))
    
    # Add SPY benchmark if available
    if 'SPY' in pivot.columns:
        spy_norm = pivot['SPY'] / pivot['SPY'].iloc[0] * 100
        fig_eq.add_trace(go.Scatter(
            x=spy_norm.index, y=spy_norm.values,
            mode='lines', name='SPY (Benchmark)',
            line=dict(color='rgba(255,193,7,0.7)', width=1.5, dash='dot')
        ))
    
    fig_eq.update_layout(
        template='plotly_dark',
        height=450,
        title="Equity Curve — Portfolio vs Benchmark",
        yaxis_title="Valor (Base 100)",
        hovermode='x unified',
        legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig_eq, use_container_width=True)
    
    # Performance grid: by symbol
    st.subheader("Rendimiento por Activo")
    perf_data = []
    for sym in symbols[:20]:  # top 20 for readability
        sym_data = pivot[sym].dropna()
        if len(sym_data) < 2:
            continue
        ret = (sym_data.iloc[-1] / sym_data.iloc[0] - 1) * 100
        daily_ret = sym_data.pct_change().dropna()
        vol = daily_ret.std() * np.sqrt(252) * 100
        perf_data.append({
            'Symbol': sym,
            'Return (%)': round(ret, 2),
            'Volatility (%)': round(vol, 2),
            'Sharpe': round((daily_ret.mean() / daily_ret.std()) * np.sqrt(252), 2) if daily_ret.std() > 0 else 0,
            'Current Price': round(sym_data.iloc[-1], 2),
        })
    
    if perf_data:
        perf_df = pd.DataFrame(perf_data).sort_values('Return (%)', ascending=False)
        st.dataframe(perf_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: ASSET — Per-symbol candlestick + OBI
# ═══════════════════════════════════════════════════════════════════════════

with tab_asset:
    st.subheader(f"📈 {selected_symbol} — Price Action & Order Flow")
    
    df_asset = market_data[market_data['symbol'] == selected_symbol].copy()
    
    if trade_data is not None and not trade_data.empty:
        asset_trades = trade_data[trade_data['symbol'] == selected_symbol].copy()
    else:
        asset_trades = pd.DataFrame()
    
    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    current_price = df_asset.iloc[-1]['close']
    price_change = (df_asset.iloc[-1]['close'] / df_asset.iloc[0]['close'] - 1) * 100
    c1.metric("Precio Cierre", f"${current_price:.2f}", f"{price_change:+.1f}%")
    
    avg_vol = df_asset['volume'].mean()
    last_vol = df_asset.iloc[-1]['volume']
    vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0
    c2.metric("Volumen Relativo", f"{vol_ratio:.2f}x")
    
    if not asset_trades.empty:
        win_trades = asset_trades[asset_trades['pnl_pct'] > 0]
        total_pnl = asset_trades['pnl_pct'].sum() * 100
        win_rate = len(win_trades) / len(asset_trades) * 100
        c3.metric("Win Rate", f"{win_rate:.0f}%")
        c4.metric("Net PnL", f"{total_pnl:+.2f}%")
    else:
        c3.metric("Trades", "0")
        c4.metric("Net PnL", "N/A")

    # Chart: candlestick + OBI
    has_obi = 'obi' in df_asset.columns
    n_rows = 2 if has_obi else 1
    row_heights = [0.7, 0.3] if has_obi else [1.0]
    subtitles = (f"Price: {selected_symbol}", "OBI") if has_obi else (f"Price: {selected_symbol}",)
    
    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=row_heights,
        subplot_titles=subtitles
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_asset['datetime'],
        open=df_asset['open'], high=df_asset['high'],
        low=df_asset['low'], close=df_asset['close'],
        name='OHLC'
    ), row=1, col=1)

    # Trade markers
    if not asset_trades.empty:
        fig.add_trace(go.Scatter(
            x=asset_trades['entry_time'],
            y=asset_trades['entry_price'],
            mode='markers',
            marker=dict(symbol='triangle-up', size=12, color='lime'),
            name='Entry'
        ), row=1, col=1)

        for _, t in asset_trades.iterrows():
            color = '#00e676' if t['pnl_pct'] > 0 else '#ff1744'
            sym = 'triangle-down' if t['pnl_pct'] > 0 else 'x'
            fig.add_trace(go.Scatter(
                x=[t['exit_time']], y=[t['exit_price']],
                mode='markers',
                marker=dict(symbol=sym, size=12, color=color),
                showlegend=False
            ), row=1, col=1)

    # OBI panel
    if has_obi:
        obi_vals = df_asset['obi']
        colors = ['#00e676' if v > 0.4 else '#ff1744' if v < -0.4 else '#78909c' for v in obi_vals]
        fig.add_trace(go.Bar(
            x=df_asset['datetime'], y=obi_vals,
            marker_color=colors, name='OBI'
        ), row=2, col=1)
        fig.add_hline(y=0.4, line_dash="dot", line_color="green", row=2, col=1)  # type: ignore
        fig.add_hline(y=-0.4, line_dash="dot", line_color="red", row=2, col=1)  # type: ignore

    fig.update_layout(
        height=700, xaxis_rangeslider_visible=False,
        template='plotly_dark', hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Trade log
    if not asset_trades.empty:
        st.subheader("📋 Bitácora de Operaciones")
        display_cols = [c for c in ['entry_time', 'entry_price', 'exit_time', 'exit_price', 'status', 'pnl_pct'] 
                       if c in asset_trades.columns]
        st.dataframe(
            asset_trades[display_cols].style.format({
                'entry_price': '{:.2f}',
                'exit_price': '{:.2f}',
                'pnl_pct': '{:.2%}'
            }),
            use_container_width=True
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: RISK METRICS
# ═══════════════════════════════════════════════════════════════════════════

with tab_risk:
    st.subheader("🛡️ Métricas de Riesgo")
    
    # Portfolio returns for metrics
    pivot_risk = market_data.pivot_table(
        index='datetime', columns='symbol', values='close', aggfunc='last'
    ).ffill()
    
    port_norm = pivot_risk / pivot_risk.iloc[0] * 100
    port_eq = port_norm.mean(axis=1)
    port_rets = port_eq.pct_change().dropna()
    
    # Risk metrics cards
    metrics = calculate_risk_metrics(port_rets)
    
    if metrics:
        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics.items()):
            col.metric(label, value)
    
    st.divider()
    
    # Drawdown chart
    cum = (1 + port_rets).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        mode='lines', name='Drawdown',
        line=dict(color='#ff1744', width=1.5),
        fill='tozeroy', fillcolor='rgba(255,23,68,0.15)'
    ))
    fig_dd.update_layout(
        template='plotly_dark', height=300,
        title="Drawdown del Portafolio",
        yaxis_title="Drawdown (%)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_dd, use_container_width=True)
    
    # Rolling metrics
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Volatilidad Rolling (21d)")
        roll_vol = port_rets.rolling(21).std() * np.sqrt(252) * 100
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=roll_vol.index, y=roll_vol.values,
            mode='lines', name='Vol 21d',
            line=dict(color='#ffa726', width=1.5)
        ))
        fig_vol.update_layout(template='plotly_dark', height=280, yaxis_title="%")
        st.plotly_chart(fig_vol, use_container_width=True)
    
    with col_b:
        st.subheader("Sharpe Rolling (63d)")
        roll_sharpe = (port_rets.rolling(63).mean() / port_rets.rolling(63).std()) * np.sqrt(252)
        fig_sh = go.Figure()
        fig_sh.add_trace(go.Scatter(
            x=roll_sharpe.index, y=roll_sharpe.values,
            mode='lines', name='Sharpe 63d',
            line=dict(color='#4fc3f7', width=1.5)
        ))
        fig_sh.add_hline(y=0, line_dash="dot", line_color="gray")  # type: ignore
        fig_sh.update_layout(template='plotly_dark', height=280, yaxis_title="Ratio")
        st.plotly_chart(fig_sh, use_container_width=True)
    
    # Trade metrics
    if trade_data is not None and not trade_data.empty:
        st.divider()
        st.subheader("📊 Métricas de Trading")
        
        trade_metrics = calculate_trade_metrics(trade_data)
        if trade_metrics:
            t_cols = st.columns(len(trade_metrics))
            for tc, (label, value) in zip(t_cols, trade_metrics.items()):
                tc.metric(label, str(value))
    
    # Returns distribution
    st.divider()
    st.subheader("Distribución de Retornos Diarios")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=port_rets.values * 100,
        nbinsx=50,
        marker_color='#4fc3f7',
        opacity=0.75,
        name='Retornos (%)'
    ))
    fig_hist.add_vline(x=0, line_dash="dot", line_color="white")  # type: ignore
    fig_hist.update_layout(
        template='plotly_dark', height=300,
        xaxis_title="Retorno Diario (%)",
        yaxis_title="Frecuencia",
        bargap=0.05
    )
    st.plotly_chart(fig_hist, use_container_width=True)