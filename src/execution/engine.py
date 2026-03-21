import pandas as pd
from typing import List, Dict
from src.execution.trade_manager import TradeManager, TradeState, TradeRecord

class ExecutionEngine:
    def __init__(self, data_feed: pd.DataFrame):
        self.data_feed = data_feed
        self.managers: Dict[str, TradeManager] = {}
        self.closed_trades: List[TradeRecord] = []

    def run(self):
        unique_symbols = self.data_feed['symbol'].unique()
        for sym in unique_symbols:
            self.managers[sym] = TradeManager(sym)

        print(f"\n--- Iniciando Motor de Ejecución para {len(unique_symbols)} activos ---")

        time_grouped = self.data_feed.groupby('datetime')

        for timestamp, tick_data in time_grouped:
            for _, row in tick_data.iterrows():
                sym = row['symbol']
                manager = self.managers[sym]

                if manager.state != TradeState.CLOSED:
                    manager.on_tick(row)

        self._collect_results()

    def _collect_results(self):
        print("\n=== RESUMEN DE EJECUCIÓN (INTRA-DÍA) ===")
        total_pnl = 0.0
        wins = 0
        losses = 0

        for sym, mgr in self.managers.items():
            if mgr.state == TradeState.CLOSED:
                trade = mgr.position
                if trade is not None:
                    self.closed_trades.append(trade)
                    total_pnl += trade.pnl_pct
                    if trade.pnl_pct > 0: wins += 1
                    else: losses += 1
            elif mgr.state == TradeState.OPEN:
                print(f"[{sym}] ⚠️ Posición quedó abierta al cierre de mercado (Mark-to-Market).")

        n_trades = len(self.closed_trades)
        if n_trades > 0:
            avg_pnl = total_pnl / n_trades
            print(f"Total Trades: {n_trades}")
            print(f"Win Rate: {wins/n_trades*100:.1f}% ({wins}W / {losses}L)")
            print(f"Global Session Alpha (Sum PnL): {total_pnl*100:.2f}%")
        else:
            print("No se ejecutaron trades (No hubo trigger de entrada).")
