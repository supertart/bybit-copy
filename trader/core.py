"""
Модуль ядра бота CopyTrader
---------------------------
Отвечает за синхронизацию сделок мастера и подписчика.
"""

import asyncio
import logging
from trader.risk import RiskManager
from trader.stats import StatsManager
from utils.api_wrappers import BybitAPI

logger = logging.getLogger(__name__)

class CopyTrader:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.master_mode = cfg.get("MASTER_MODE", "trade")
        self.master_env = cfg.get("MASTER_ENV", "mainnet")
        self.follower_env = cfg.get("FOLLOWER_ENV", "mainnet")

        logger.info(f"🧩 Инициализация мастера ({self.master_mode}, env={self.master_env})")

        self.master_api = BybitAPI(
            api_key=cfg.get("MASTER_API_KEY"),
            api_secret=cfg.get("MASTER_API_SECRET"),
            role="MASTER",
            env=self.master_env,
        )
        self.follower_api = BybitAPI(
            api_key=cfg.get("FOLLOWER_API_KEY"),
            api_secret=cfg.get("FOLLOWER_API_SECRET"),
            role="FOLLOWER",
            env=self.follower_env,
        )

        self.stats = StatsManager(cfg)
        self.risk = RiskManager(cfg, self.follower_api)
        logger.info(f"📡 Подписчик env={self.follower_env}")

        self.ignored_symbols = set()

    async def fetch_master_positions(self):
        try:
            return await self.master_api.get_open_positions() or []
        except Exception as e:
            logger.warning(f"[MASTER] fetch_master_positions failed: {e}")
            return []

    async def fetch_follower_positions(self):
        try:
            return await self.follower_api.get_open_positions() or []
        except Exception as e:
            logger.warning(f"[FOLLOWER] fetch_follower_positions failed: {e}")
            return []

    async def run_copy_loop(self):
        logger.info("🟢 Запуск цикла копирования сделок")

        master_positions = await self.fetch_master_positions()
        self.ignored_symbols = {pos["symbol"] for pos in master_positions}
        if self.ignored_symbols:
            logger.info(
                f"🔸 Найдено {len(self.ignored_symbols)} активных позиций мастера. "
                f"Они будут проигнорированы при старте: {', '.join(self.ignored_symbols)}"
            )
        else:
            logger.info("✅ У мастера нет активных позиций при старте — копирование начнётся немедленно.")

        try:
            while True:
                master_positions = await self.fetch_master_positions()
                follower_positions = await self.fetch_follower_positions()

                master_symbols = {p["symbol"] for p in master_positions}
                follower_symbols = {p["symbol"] for p in follower_positions}

                for pos in master_positions:
                    symbol = pos["symbol"].upper()
                    side = pos["side"]
                    qty = float(pos.get("contracts") or pos.get("size") or 0)
                    price = float(pos.get("entryPrice") or 0)
                    leverage = int(pos.get("leverage") or 10)

                    if symbol in self.ignored_symbols:
                        continue

                    if symbol not in follower_symbols and qty > 0:
                        logger.info(f"🆕 Новая позиция мастера: {symbol} ({side}, qty={qty})")
                        balance = await self.follower_api.get_balance()
                        risk_check = self.risk.apply_risk_rules(symbol, side, price, balance, leverage)
                        if not risk_check["allowed"]:
                            logger.warning(f"🚫 Сделка {symbol} отклонена: {risk_check['reason']}")
                            continue

                        await self.follower_api.open_position(symbol, side, qty, leverage)
                        self.stats.record_open_trade(symbol, side, qty, price, leverage)
                        logger.info(f"✅ Сделка {symbol} открыта у подписчика.")
                        self.ignored_symbols.add(symbol)

                for sym in list(self.ignored_symbols):
                    if sym not in master_symbols:
                        logger.info(f"🔻 Мастер закрыл {sym}. Закрываем и у подписчика.")
                        await self.follower_api.close_position(sym)
                        self.stats.record_close_trade(sym, price=0.0, pnl=0.0)
                        self.ignored_symbols.remove(sym)

                self.stats.update_from_positions(follower_positions)
                await asyncio.sleep(self.cfg.get("POLL_INTERVAL_SEC", 5))

        except asyncio.CancelledError:
            logger.warning("🟥 Цикл копирования остановлен (SIGINT/SIGTERM).")
            raise
        except Exception as e:
            logger.warning(f"Ошибка цикла копирования: {e}")
            await asyncio.sleep(5)

    async def start(self):
        await self.run_copy_loop()
