"""
Главная точка входа бота копитрейдинга Bybit
--------------------------------------------
Запускает трейдер и Telegram-интерфейс.
Добавлена корректная обработка SIGINT (Ctrl+C) и SIGTERM.
"""

import asyncio
import logging
import signal
from config import load_config
from trader.core import CopyTrader
from telegram.ui import TelegramUI


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Запуск бота копитрейдинга для подписчика...")

    cfg = load_config()
    trader = CopyTrader(cfg)
    tg = TelegramUI(cfg, trader)

    # Создаём задачу
    trader_task = asyncio.create_task(trader.start())
    tg_task = asyncio.create_task(tg.run())

    # Функция завершения
    async def shutdown():
        logger.warning("🟥 Завершение работы по сигналу...")
        trader_task.cancel()
        tg_task.cancel()
        try:
            await trader.master_api.close()
            await trader.follower_api.close()
        except Exception:
            pass
        await asyncio.sleep(0.5)
        logger.info("✅ Завершено корректно.")
        asyncio.get_event_loop().stop()

    # Регистрируем обработчики сигналов
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown()))
        except NotImplementedError:
            # Windows не поддерживает add_signal_handler
            pass

    await asyncio.gather(trader_task, tg_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🟥 Остановлено пользователем (Ctrl+C).")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
