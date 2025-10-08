import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from telegram.messages import (
    get_welcome_text,
    get_settings_text,
    get_positions_text,
    get_stats_loading_text,
    build_stats_text,
    main_menu_kb,
    settings_inline_kb,
    settings_net_kb,
    settings_risk_kb,
    settings_alerts_kb,
)

logger = logging.getLogger(__name__)

class TelegramUI:
    def __init__(self, cfg: dict, trader):
        self.cfg = cfg
        self.trader = trader

        self.bot = Bot(token=self.cfg["TELEGRAM_BOT_TOKEN"], parse_mode="HTML")
        self.dp = Dispatcher(storage=MemoryStorage())

        # Команды
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_stats, Command("stats"))
        self.dp.message.register(self.on_text)

        # Callback-и из инлайн-кнопок
        self.dp.callback_query.register(self.cb_settings_router, F.data.startswith("settings:"))

    # ---------------- Команды / Сообщения ----------------

    async def cmd_start(self, msg: Message):
        await msg.answer(get_welcome_text(), reply_markup=main_menu_kb())

    async def cmd_stats(self, msg: Message):
        # 1) отправляем "загрузка" с reply keyboard (новое сообщение)
        loading = await msg.answer(get_stats_loading_text(), reply_markup=main_menu_kb())

        try:
            # 2) параллельно берём балансы
            master_balance_task = asyncio.create_task(self.trader.master_api.get_balance())
            follower_balance_task = asyncio.create_task(self.trader.follower_api.get_balance())
            summary = self.trader.stats.get_summary()
            master_balance, follower_balance = await asyncio.gather(master_balance_task, follower_balance_task)

            text = build_stats_text(
                master_env=self.trader.master_env,
                follower_env=self.trader.follower_env,
                master_balance=master_balance,
                follower_balance=follower_balance,
                summary=summary,
                currency="USDT",
            )

            # 3) пытаемся заменить текст лоадера
            try:
                await loading.edit_text(text)
            except TelegramBadRequest:
                # если редактировать нельзя — удаляем лоадер и шлём новое сообщение
                try:
                    await loading.delete()
                except Exception:
                    pass
                await msg.answer(text, reply_markup=main_menu_kb())

        except Exception as e:
            logger.warning(f"[TelegramUI] Ошибка формирования статистики: {e}")
            # тоже: если нельзя редактировать — удаляем и шлём новое
            try:
                await loading.edit_text("⚠️ Не удалось получить статистику. Попробуйте позже.")
            except TelegramBadRequest:
                try:
                    await loading.delete()
                except Exception:
                    pass
                await msg.answer("⚠️ Не удалось получить статистику. Попробуйте позже.", reply_markup=main_menu_kb())

    async def on_text(self, msg: Message):
        text = (msg.text or "").strip()

        if text == "⚙️ Настройки":
            await msg.answer(get_settings_text(), reply_markup=settings_inline_kb())
            return

        if text == "📊 Статистика":
            await self.cmd_stats(msg)
            return

        if text == "📂 Открытые позиции":
            await msg.answer(get_positions_text(), reply_markup=main_menu_kb())
            return

        if text == "🔄 Перезапуск":
            await msg.answer("♻️ Перезапуск бота (заглушка).", reply_markup=main_menu_kb())
            # здесь можно повесить безопасный рестарт через systemd или внутренний сигнал
            return

        # по умолчанию просто вернуть главное меню
        await msg.answer("Выберите действие на клавиатуре ниже.", reply_markup=main_menu_kb())

    # ---------------- Callback-и настроек ----------------

    async def cb_settings_router(self, cq: CallbackQuery):
        data = cq.data

        if data == "settings:back":
            await cq.message.edit_text(get_settings_text(), reply_markup=settings_inline_kb())
            await cq.answer()
            return

        if data == "settings:set_net":
            await cq.message.edit_text("🌐 Выберите торговую сеть:", reply_markup=settings_net_kb())
            await cq.answer()
            return

        if data == "settings:set_risk":
            await cq.message.edit_text("🛡️ Параметры риска и режимов:", reply_markup=settings_risk_kb())
            await cq.answer()
            return

        if data == "settings:set_alerts":
            await cq.message.edit_text("🔔 Управление уведомлениями:", reply_markup=settings_alerts_kb())
            await cq.answer()
            return

        # Подсеть выбора
        if data.startswith("settings:net:"):
            net = data.split(":")[-1]
            await cq.answer(f"Сеть выбрана: {net}")
            # здесь можно сохранить выбор в конфиг или state.json и предложить перезапуск
            await cq.message.edit_text(get_settings_text(), reply_markup=settings_inline_kb())
            return

        if data == "settings:risk:max_risk":
            await cq.answer("Пришлите новое значение MAX_RISK_PCT (например, 3.5).")
            await cq.message.answer("✍️ Введите число, % риска на сделку. (пока заглушка)")
            return

        if data == "settings:risk:test_mode":
            await cq.answer("Переключение TEST_MODE (пока заглушка).")
            await cq.message.edit_text("TEST_MODE переключён (заглушка).", reply_markup=settings_inline_kb())
            return

        if data == "settings:alerts:toggle":
            await cq.answer("Оповещения переключены (заглушка).")
            await cq.message.edit_text("🔔 Оповещения переключены (заглушка).", reply_markup=settings_inline_kb())
            return

        await cq.answer("Неизвестное действие.")

    # ---------------- Запуск ----------------

    async def run(self):
        logger.info("🤖 Telegram-бот запущен и слушает команды.")
        await self.dp.start_polling(self.bot)

    async def close(self):
        try:
            await self.bot.session.close()
        except Exception:
            pass
