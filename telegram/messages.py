from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

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

def _fmt_money(x: float) -> str:
    try:
        return f"{x:,.2f}"
    except Exception:
        return str(x)

def build_stats_text_extended(
    master_env: str,
    follower_env: str,
    master_balance: float,
    follower_balance: float,
    follower_open_count: int,
    follower_positions_value_total: float,
    follower_unrealized_total: float,
    summary_updated_at: str | None,
    pnl_windows: dict[int, float],
    currency: str = "USDT",
) -> str:
    lines = []
    lines.append("📊 <b>Статистика бота</b>")
    lines.append("")
    lines.append(f"👤 <b>Мастер</b> [{master_env}] — баланс: <code>{_fmt_money(master_balance)} {currency}</code>")
    lines.append(f"🤖 <b>Подписчик</b> [{follower_env}] — баланс: <code>{_fmt_money(follower_balance)} {currency}</code>")
    lines.append("")
    lines.append(f"📌 Открытых позиций: <b>{follower_open_count}</b>")
    lines.append(f"💰 Стоимость открытых позиций: <code>{_fmt_money(follower_positions_value_total)} {currency}</code>")
    lines.append(f"📈 Нереализ. PnL (UPnL): <code>{_fmt_money(follower_unrealized_total)} {currency}</code>")
    lines.append("")
    if pnl_windows:
        lines.append("🧾 <b>PNL подписчика</b>:")
        for days in [1, 7, 14, 30, 45, 60, 90]:
            val = pnl_windows.get(days, 0.0)
            lines.append(f" • {days:>2} дн: <code>{_fmt_money(val)} {currency}</code>")
        lines.append("")
    lines.append(f"🕒 Обновлено: <i>{_fmt_dt(summary_updated_at)}</i>")
    return "\n".join(lines)

# ---------- Главная клавиатура ----------

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

# ---------- Настройки ----------

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
