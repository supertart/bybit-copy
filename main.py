import asyncio
import logging
from trader.core import CopyTrader
from telegram.ui import TelegramUI
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

async def main():
    cfg = load_config()

    logging.info("🚀 Запуск бота копитрейдинга для подписчика...")

    trader = CopyTrader(cfg)
    tg = TelegramUI(cfg, trader)

    # Запуск торгового цикла и Telegram бота параллельно
    await asyncio.gather(
        trader.run_forever(),
        tg.run()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("🛑 Остановка по Ctrl+C")
