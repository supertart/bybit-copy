import logging
import requests


class TelegramAlerts:
    """
    Отправка уведомлений пользователю в Telegram
    (о рисках, авто-паузе, SL, TP, открытии/закрытии сделок).
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.token = cfg.get("TELEGRAM_BOT_TOKEN")
        self.chat_ids = str(cfg.get("TELEGRAM_CHAT_ID", "")).split(",")

    # ====================== ОТПРАВКА СООБЩЕНИЙ ======================
    def send(self, text: str, disable_preview=True):
        """Отправка сообщения во все указанные Telegram-чаты"""
        if not self.token or not self.chat_ids:
            logging.warning("❗ Telegram: не заданы токен или chat_id")
            return

        for chat_id in self.chat_ids:
            try:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                payload = {
                    "chat_id": chat_id.strip(),
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": disable_preview,
                }
                r = requests.post(url, json=payload, timeout=10)
                if r.status_code != 200:
                    logging.warning(f"Telegram API error: {r.text}")
            except Exception as e:
                logging.warning(f"Ошибка Telegram отправки: {e}")

    # ====================== УВЕДОМЛЕНИЯ О СОБЫТИЯХ ======================
    def notify_position_open(self, symbol, side, qty, price):
        self.send(f"📈 <b>Открыта позиция</b>\n"
                  f"{symbol} | {side} {qty}\n"
                  f"Цена входа: <b>{price}</b>")

    def notify_position_close(self, symbol, side, pnl):
        emoji = "✅" if pnl >= 0 else "❌"
        self.send(f"{emoji} <b>Закрыта позиция</b>\n"
                  f"{symbol} | PnL: <b>{pnl:.2f} USDT</b>")

    def notify_stoploss(self, symbol, change):
        self.send(f"🟥 <b>Сработал локальный стоп-лосс</b>\n"
                  f"{symbol}\n"
                  f"Цена ушла против на {abs(change):.2f}%")

    def notify_autopause(self, drawdown):
        self.send(f"⚠️ <b>Копирование приостановлено</b>\n"
                  f"Просадка депозита: {drawdown:.1f}%\n"
                  f"Копирование временно отключено.")

    def notify_liq_buffer(self, symbol, buffer):
        self.send(f"⚠️ <b>Малый буфер ликвидации</b>\n"
                  f"{symbol}\n"
                  f"Буфер: {buffer:.1f}%")

    def notify_volatility(self, symbol, vol, factor):
        self.send(f"🌪 <b>Высокая волатильность</b>\n"
                  f"{symbol}: {vol:.1f}% за 24ч\n"
                  f"Размер позиции уменьшен ×{factor}")
