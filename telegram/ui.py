import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from trader.stats import StatsManager
from config import save_config
from telegram.messages import get_param_description

# ============================================================
#  Telegram UI — меню, кнопки, категории
# ============================================================

class TelegramUI:
    def __init__(self, cfg, trader):
        self.cfg = cfg
        self.trader = trader
        self.stats = trader.stats
        self.bot = Bot(token=cfg["TELEGRAM_BOT_TOKEN"])
        self.dp = Dispatcher(self.bot)

        self._register_handlers()

    # ====================== ЗАПУСК ======================
    async def run(self):
        logging.info("🤖 Telegram-бот запущен")
        await self.dp.start_polling()

    # ====================== ОБРАБОТЧИКИ ======================
    def _register_handlers(self):
        self.dp.register_message_handler(self.cmd_start, commands=["start"])
        self.dp.register_callback_query_handler(self.on_callback)

    async def cmd_start(self, message: types.Message):
        text = "⚙️ Главное меню бота копитрейдинга"
        await message.answer(text, reply_markup=self.main_menu())

    # ====================== КЛАВИАТУРЫ ======================
    def main_menu(self):
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("📈 Основные", callback_data="cat_main"),
            InlineKeyboardButton("📊 Масштабирование", callback_data="cat_scale"),
            InlineKeyboardButton("🧮 Риск", callback_data="cat_risk"),
            InlineKeyboardButton("⏸ Пауза и уведомления", callback_data="cat_pause"),
            InlineKeyboardButton("📈 Статистика", callback_data="stats_menu"),
        )
        return kb

    def back_menu(self):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
        return kb

    def stats_menu(self):
        kb = InlineKeyboardMarkup(row_width=3)
        kb.add(
            InlineKeyboardButton("🕐 1д", callback_data="stat_1"),
            InlineKeyboardButton("🗓 7д", callback_data="stat_7"),
            InlineKeyboardButton("📅 30д", callback_data="stat_30"),
            InlineKeyboardButton("🧭 90д", callback_data="stat_90"),
            InlineKeyboardButton("📊 Вся история", callback_data="stat_all"),
            InlineKeyboardButton("🔄 Обновить", callback_data="stat_refresh"),
            InlineKeyboardButton("⬅️ Назад", callback_data="back_main")
        )
        return kb

    # ====================== КАТЕГОРИИ ======================
    def category_menu(self, category):
        """Создаёт меню параметров для категории"""
        cat_map = {
            "cat_main": [
                "COPY_ACTIVE", "COPY_TP", "COPY_SL", "DRY_RUN", "POSITION_IDX"
            ],
            "cat_scale": [
                "SIZE_SCALE", "DYNAMIC_SCALE", "DYN_SCALE_FACTOR",
                "VOLATILITY_SCALE"
            ],
            "cat_risk": [
                "MAX_EQUITY_RISK_PCT", "MIN_LIQ_BUFFER_PCT",
                "MAX_DCA_PER_TRADE", "LOCAL_SL_PCT",
                "LIQ_BUFFER_EMERGENCY", "CUT_PERCENT"
            ],
            "cat_pause": [
                "EQUITY_DRAWDOWN_PCT", "AUTO_CLOSE_ON_DRAWDOWN",
                "RISK_ALERTS"
            ]
        }

        kb = InlineKeyboardMarkup(row_width=1)
        for p in cat_map.get(category, []):
            val = self.cfg.get(p)
            text = f"{p}: {val}"
            kb.add(InlineKeyboardButton(text, callback_data=f"param_{p}"))
        kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
        return kb

    # ====================== ОБРАБОТКА CALLBACK ======================
    async def on_callback(self, query: types.CallbackQuery):
        data = query.data
        if data == "back_main":
            await query.message.edit_text("⚙️ Главное меню", reply_markup=self.main_menu())

        elif data.startswith("cat_"):
            await query.message.edit_text(
                "Выберите параметр:",
                reply_markup=self.category_menu(data)
            )

        elif data.startswith("param_"):
            param = data.replace("param_", "")
            desc = get_param_description(param)
            value = self.cfg.get(param)
            msg = f"🔧 <b>{param}</b>\n\n{desc}\n\nТекущее значение: <b>{value}</b>"
            await query.message.edit_text(msg, reply_markup=self.param_menu(param))

        elif data.startswith("stat_"):
            days = {
                "stat_1": 1,
                "stat_7": 7,
                "stat_30": 30,
                "stat_90": 90,
                "stat_all": 0,
                "stat_refresh": -1
            }[data]
            if days == -1:
                await query.message.edit_text("🔄 Обновление статистики...", reply_markup=self.stats_menu())
            else:
                report = self.stats.get_report(days)
                await query.message.edit_text(report, reply_markup=self.stats_menu())

        await query.answer()

    def param_menu(self, param):
        """Меню для отдельного параметра (изменение значения)"""
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_{param}"))
        kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
        return kb
