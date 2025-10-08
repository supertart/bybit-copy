from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

# ---------- Текстовые шаблоны ----------

def get_welcome_text() -> str:
    return (
        "👋 Привет! Я бот копитрейдинга.\n\n"
        "Используй кнопки ниже, чтобы управлять ботом:\n"
        "• 🔄 Перезапуск\n"
        "• ⚙️ Настройки\n"
        "• 📂 Открытые позиции\n"
        "• 📊 Статистика\n"
    )

def get_settings_text() -> str:
    return (
        "⚙️ Настройки бота:\n\n"
        "• Изменить торговую сеть (mainnet/testnet/demo)\n"
        "• Настроить параметры риска и лотности\n"
        "• Управлять Telegram-уведомлениями\n\n"
        "Используйте кнопки ниже для выбора."
    )

def get_positions_text() -> str:
    return "📂 Открытые позиции будут показаны здесь (пока заглушка)."

def _fmt_dt(dt_iso: str | None) -> str:
    if not dt_iso:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return dt_iso

def build_stats_text(
    master_env: str,
    follower_env: str,
    master_balance: float,
    follower_balance: float,
    summary: dict,
    currency: str = "USDT",
) -> str:
    """
    Формирует красивый блок статистики, включая балансы мастера/подписчика.
    """
    open_cnt = summary.get("open_count", 0)
    closed_cnt = summary.get("closed_count", 0)
    updated_at = _fmt_dt(summary.get("updated_at"))

    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 <b>Мастер</b> [{master_env}] — баланс: <code>{master_balance:,.2f} {currency}</code>\n"
        f"🤖 <b>Подписчик</b> [{follower_env}] — баланс: <code>{follower_balance:,.2f} {currency}</code>\n"
        "\n"
        f"📌 Открытых сделок: <b>{open_cnt}</b>\n"
        f"📦 Закрытых сделок: <b>{closed_cnt}</b>\n"
        f"🕒 Обновлено: <i>{updated_at}</i>\n"
    )

def get_stats_loading_text() -> str:
    return "⏳ Собираю статистику и балансы…"

# ---------- Главная клавиатура (ReplyKeyboard) ----------

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Перезапуск"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
            [
                KeyboardButton(text="📂 Открытые позиции"),
                KeyboardButton(text="📊 Статистика"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие…",
    )

# ---------- Клавиатура настроек (InlineKeyboard) ----------

def settings_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Торговая сеть", callback_data="settings:set_net")],
        [InlineKeyboardButton(text="🛡️ Риск и лотность", callback_data="settings:set_risk")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:set_alerts")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
    ])

def settings_net_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="demo (бумажная)", callback_data="settings:net:demo")],
        [InlineKeyboardButton(text="testnet", callback_data="settings:net:testnet")],
        [InlineKeyboardButton(text="mainnet", callback_data="settings:net:mainnet")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
    ])

def settings_risk_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить MAX_RISK_PCT", callback_data="settings:risk:max_risk")],
        [InlineKeyboardButton(text="Изменить TEST_MODE", callback_data="settings:risk:test_mode")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
    ])

def settings_alerts_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вкл/Выкл оповещения", callback_data="settings:alerts:toggle")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
    ])
