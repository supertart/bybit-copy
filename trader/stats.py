import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class StatsManager:
    def __init__(self, cfg: dict):
        self.state_file = cfg.get("STATE_FILE", "state.json")
        self.state: Dict[str, Any] = {
            "history": [],          # список завершённых сделок: [{symbol, pnl, opened_at, closed_at, ...}]
            "open": {},             # symbol -> инфо открытой: {symbol, side, qty, entry_price, opened_at, leverage, averages}
            "updated_at": None,
        }
        self._load()
        logger.info(f"📊 Инициализация StatsManager (файл: {self.state_file})")

    def _load(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("history", [])
                    data.setdefault("open", {})
                    data.setdefault("updated_at", None)
                    self.state = data
            logger.info(f"✅ Загружено состояние статистики ({len(self.state['history'])} сделок).")
        except Exception as e:
            logger.warning(f"Не удалось загрузить {self.state_file}: {e}")

    def _save(self):
        try:
            self.state["updated_at"] = datetime.utcnow().isoformat()
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить {self.state_file}: {e}")

    # ----- записи о сделках -----

    def record_open_trade(self, symbol: str, side: str, qty: float, price: float, leverage: int):
        self.state["open"][symbol] = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry_price": price,
            "leverage": leverage,
            "opened_at": datetime.utcnow().isoformat(),
            "averages": 0,
        }
        self._save()

    def record_close_trade(self, symbol: str, price: float, pnl: float):
        info = self.state["open"].pop(symbol, None)
        if not info:
            return
        info["exit_price"] = price
        info["pnl"] = pnl
        info["closed_at"] = datetime.utcnow().isoformat()

        try:
            opened = datetime.fromisoformat(info["opened_at"])
            closed = datetime.fromisoformat(info["closed_at"])
            info["duration_sec"] = int((closed - opened).total_seconds())
        except Exception:
            info["duration_sec"] = None

        self.state["history"].append(info)
        self._save()

    def update_from_positions(self, follower_positions: List[Dict[str, Any]]):
        # можно расширить обновлением плавающего PnL и т.п.
        self._save()

    # ----- агрегаты -----

    def get_summary(self) -> Dict[str, Any]:
        return {
            "open_count": len(self.state.get("open", {})),
            "closed_count": len(self.state.get("history", [])),
            "updated_at": self.state.get("updated_at"),
        }

    def pnl_last_days(self, days: int) -> float:
        """Сумма PnL по закрытым сделкам за последние N дней (UTC)."""
        if days <= 0:
            return 0.0
        cutoff = datetime.utcnow() - timedelta(days=days)
        total = 0.0
        for t in self.state.get("history", []):
            try:
                closed = datetime.fromisoformat(str(t.get("closed_at")))
            except Exception:
                continue
            if closed >= cutoff:
                try:
                    total += float(t.get("pnl", 0.0))
                except Exception:
                    pass
        return float(total)

    def pnl_by_windows(self, windows: List[int]) -> Dict[int, float]:
        res: Dict[int, float] = {}
        for d in windows:
            res[d] = self.pnl_last_days(d)
        return res
