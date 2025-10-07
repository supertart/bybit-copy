import asyncio
import logging
import time
from trader.master_bridge import MasterBridge
from utils.api_wrappers import BybitHTTP
from trader.risk import RiskManager
from trader.stats import StatsManager


class CopyTrader:
    """
    Основной класс копирования сделок мастера.
    Поддерживает разные сети и режимы мастера.
    """

    def __init__(self, cfg):
        self.cfg = cfg

        # ---- Мастер ----
        self.master = MasterBridge(cfg)

        # ---- Подписчик ----
        follower_net = cfg.get("FOLLOWER_NET", "mainnet").lower()
        follower_testnet = follower_net == "testnet"
        self.follower_api = BybitHTTP(
            cfg["FOLLOWER_API_KEY"],
            cfg["FOLLOWER_API_SECRET"],
            testnet=follower_testnet
        )

        # ---- Сервисы ----
        self.stats = StatsManager(cfg)
        self.risk = RiskManager(cfg, self.follower_api)
        self.last_check = 0

        logging.info(f"📡 Подписчик сеть={follower_net}")

    async def run_forever(self):
        logging.info("🟢 Запуск цикла копирования сделок")
        while True:
            try:
                await self.sync_positions()
                await asyncio.sleep(5)
            except Exception as e:
                logging.warning(f"Ошибка цикла копирования: {e}")
                await asyncio.sleep(5)

    async def sync_positions(self):
        """Синхронизация позиций мастера и подписчика"""
        now = time.time()
        if now - self.last_check < 5:
            return
        self.last_check = now

        master_positions = self.master.get_positions()
        follower_positions = self.follower_api.get_positions()

        for mpos in master_positions:
            symbol = mpos["symbol"]
            side = mpos["side"]
            size = float(mpos.get("size") or 0)
            entry_price = float(mpos.get("avgPrice") or 0)
            tp = float(mpos.get("takeProfit") or 0)
            sl = float(mpos.get("stopLoss") or 0)

            fpos = next((p for p in follower_positions if p["symbol"] == symbol), None)
            fsize = float(fpos["size"]) if fpos else 0.0

            # ---- Закрытие ----
            if size == 0 and fsize != 0:
                await self.close_position(symbol, fpos)
                continue

            # ---- Расчёт нужного размера ----
            qty = self.risk.calculate_scaled_qty(
                master_size=size,
                master_price=entry_price,
                symbol=symbol
            )

            if fsize == 0 and qty > 0:
                await self.open_position(symbol, side, qty)
            elif abs(qty - fsize) / max(qty, 1) > 0.05:
                await self.adjust_position(symbol, side, qty, fsize)

            # ---- TP/SL ----
            if tp > 0 and self.cfg.get("COPY_TP", True):
                self.follower_api.set_take_profit(symbol, tp)
            if sl > 0 and self.cfg.get("COPY_SL", True):
                self.follower_api.set_stop_loss(symbol, sl)

            await self.risk.check_local_stoploss(symbol)
            await self.risk.check_autopause()

        self.stats.update_from_positions(follower_positions)

    async def open_position(self, symbol, side, qty):
        if not self.cfg.get("COPY_ACTIVE", True):
            return
        logging.info(f"📈 Открытие позиции {symbol} {side} {qty}")
        self.follower_api.market_order(symbol, side, qty)
        self.stats.on_open(symbol, qty)

    async def close_position(self, symbol, pos):
        side = "Sell" if pos["side"] == "Buy" else "Buy"
        qty = abs(float(pos["size"]))
        logging.info(f"📉 Закрытие позиции {symbol} {side} {qty}")
        self.follower_api.market_order(symbol, side, qty, reduce_only=True)
        self.stats.on_close(symbol, qty)

    async def adjust_position(self, symbol, side, target_qty, current_qty):
        if not self.cfg.get("COPY_ACTIVE", True):
            return
        delta = target_qty - current_qty
        if abs(delta) < 1e-6:
            return
        adj_side = side if delta > 0 else ("Sell" if side == "Buy" else "Buy")
        adj_qty = abs(delta)
        logging.info(f"⚙️ Корректировка {symbol}: {adj_side} {adj_qty}")
        self.follower_api.market_order(symbol, adj_side, adj_qty, reduce_only=(delta < 0))
