"""
Форматирование и отправка Telegram-уведомлений о сделках/рисках.
Совместимо с ui.py (функция send_trade_alert(trade_info)).
"""

from datetime import datetime
import logging
import requests


# ============= ВСПОМОГАТЕЛЬНЫЕ ФОРМАТТЕРЫ =============

def _ts_to_str(ms: int) -> str:
    """Печать времени из миллисекунд в локальный читаемый формат."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return "-"

def _fmt_num(x, digits=4):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)

def _fmt_pnl(x):
    try:
        val = float(x)
        sign = "🟢" if val >= 0 else "🔴"
        return f"{sign} {val:.2f} USDT"
    except Exception:
        return str(x)

def _fmt_duration(ms_start: int | None, ms_end: int | None) -> str:
    if not ms_start:
        return "—"
    if not ms_end:
        return "в процессе"
    try:
        sec = (int(ms_end) - int(ms_start)) // 1000
        if sec < 60:
            return f"{sec}s"
        minutes = sec // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"
    except Exception:
        return "—"


# ============= ПУБЛИЧНАЯ ФУНКЦИЯ ДЛЯ ui.py =============

def send_trade_alert(trade: dict) -> str:
    """
    Возвращает готовый HTML-текст для Telegram об открытии/закрытии сделки.

    Ожидаемые ключи trade (не все обязательны):
      symbol, side, qty,
      open_price, close_price,
      net_pnl, leverage, dca_count,
      open_time_ms, close_time_ms,
      event ("open" | "close" | "adjust")
    """
    symbol     = trade.get("symbol", "-")
    side       = trade.get("side", "-")
    qty        = trade.get("qty", 0)
    open_p     = trade.get("open_price")
    close_p    = trade.get("close_price")
    pnl        = trade.get("net_pnl")
    lev        = trade.get("leverage")
    dca        = trade.get("dca_count")
    t_open_ms  = trade.get("open_time_ms")
    t_close_ms = trade.get("close_time_ms")
    event      = (trade.get("event") or "").lower()

    # Заголовок по типу события
    if event == "open":
        title = "📈 <b>Открыта позиция</b>"
    elif event == "close":
        title = "📉 <b>Закрыта позиция</b>"
    elif event == "adjust":
        title = "⚙️ <b>Корректировка позиции</b>"
    else:
        title = "ℹ️ <b>Событие по позиции</b>"

    rows = [
        f"{title}",
        f"{symbol} | {side} | кол-во: <b>{_fmt_num(qty, 3)}</b>",
    ]

    if open_p is not None:
        rows.append(f"Цена входа: <b>{_fmt_num(open_p, 4)}</b>")
    if close_p is not None:
        rows.append(f"Цена выхода: <b>{_fmt_num(close_p, 4)}</b>")

    if pnl is not None and event in ("close",):
        rows.append(f"Результат: <b>{_fmt_pnl(pnl)}</b>")

    if lev is not None:
        rows.append(f"Плечо: <b>{lev}x</b>")
    if dca is not None:
        rows.append(f"Усреднений: <b>{dca}</b>")

    if t_open_ms:
        rows.append(f"Время открытия: <b>{_ts_to_str(t_open_ms)}</b>")
    if t_close_ms:
        rows.append(f"Время закрытия: <b>{_ts_to_str(t_close_ms)}</b>")
        rows.append(f"Длительность: <b>{_fmt_duration(t_open_ms, t_close_ms)}</b>")

    return "\n".join(rows)


# ============= НЕОБЯЗАТЕЛЬНЫЙ КЛАСС-ОТПРАВЩИК =============

class TelegramAlerts:
    """
    Простой отправщик сообщений в Telegram по токену и chat_id.
    Можно использовать из других модулей при необходимости.
    """
    def __init__(self, token: str, chat_ids: str | list[str]):
        self.token = token
        if isinstance(chat_ids, str):
            self.chat_ids = [cid.strip() for cid in chat_ids.split(",") if cid.strip()]
        else:
            self.chat_ids = chat_ids or []

    def send(self, text: str, parse_mode: str = "HTML", disable_preview: bool = True):
        if not self.token or not self.chat_ids:
            logging.warning("TelegramAlerts: не заданы token/chat_id")
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for cid in self.chat_ids:
            try:
                r = requests.post(
                    url,
                    json={
                        "chat_id": cid,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_preview,
                    },
                    timeout=10,
                )
                if r.status_code != 200:
                    logging.warning(f"Telegram API error: {r.text}")
            except Exception as e:
                logging.warning(f"Telegram send error: {e}")
