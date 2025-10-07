import json
import logging
import time
from datetime import datetime, timedelta
from config import save_config


class StatsManager:
    """
    Управление статистикой сделок:
    сбор данных, расчёт PnL, winrate, ROI, отчёт по периодам.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.state_file = cfg.get("STATE_FILE", "state.json")
        self.stats = {"history": []}
        self.load()

    # ====================== ЗАГРУЗКА / СОХРАНЕНИЕ ======================
    def load(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                self.stats = state.get("stats", {"history": []})
        except Exception:
            self.stats = {"history": []}

    def save(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
        state["stats"] = self.stats
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    # ====================== СОБЫТИЯ СДЕЛОК ======================
    def on_open(self, symbol, qty):
        """Регистрирует открытие позиции"""
        entry = {
            "symbol": symbol,
            "open_qty": qty,
            "open_time": int(time.time() * 1000),
            "close_time": None,
            "pnl": 0.0,
            "win": None,
        }
        self.stats["history"].append(entry)
        self.save()

    def on_close(self, symbol, qty):
        """Регистрирует закрытие позиции"""
        now = int(time.time() * 1000)
        # находим последнюю открытую позицию по символу
        open_trades = [t for t in self.stats["history"] if t["symbol"] == symbol and t["close_time"] is None]
        if not open_trades:
            return
        trade = open_trades[-1]
        trade["close_time"] = now
        trade["pnl"] = self.fake_pnl()  # вместо реального расчёта
        trade["win"] = trade["pnl"] >= 0
        self.save()

    def fake_pnl(self):
        """Псевдо-значение PnL для примера (в реальном коде — с биржи)"""
        import random
        return round(random.uniform(-5, 10), 2)

    def update_from_positions(self, positions):
        """Обновление статистики по открытым позициям"""
        active = [p for p in positions if float(p.get("size") or 0) > 0]
        self.stats["open_count"] = len(active)
        self.save()

    # ====================== РАСЧЁТ ЗА ПЕРИОД ======================
    def get_report(self, days: int = 0):
        """Возвращает статистику за N дней (0 = вся история)"""
        now = int(time.time() * 1000)
        if days > 0:
            start = now - days * 86400000
        else:
            start = 0

        history = [t for t in self.stats["history"] if t["close_time"] and t["close_time"] >= start]

        trades = len(history)
        wins = sum(1 for t in history if t["win"])
        losses = trades - wins
        pnl_sum = sum(t["pnl"] for t in history)
        winrate = (wins / trades * 100) if trades else 0
        avg_pnl = (pnl_sum / trades) if trades else 0

        report = [
            f"📊 <b>Статистика {'за ' + str(days) + ' дн' if days else 'вся история'}:</b>",
            f"🧾 Сделок: <b>{trades}</b> (выигр: {wins}, проигр: {losses})",
            f"💵 PnL: <b>{pnl_sum:.2f} USDT</b>",
            f"📈 Winrate: <b>{winrate:.2f}%</b>",
            f"📉 Средний результат сделки: <b>{avg_pnl:.2f} USDT</b>",
        ]
        return "\n".join(report)
