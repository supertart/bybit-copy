import logging
import time
from utils.api_wrappers import BybitHTTP
from config import save_config


class RiskManager:
    """
    Управление рисками: динамическое масштабирование, стоп-лоссы, ликвидационный буфер, авто-пауза.
    """

    def __init__(self, cfg, follower_api: BybitHTTP):
        self.cfg = cfg
        self.api = follower_api
        self.last_equity = 0
        self.max_equity = 0
        self.last_check = 0

    # ====================== РАСЧЁТ РАЗМЕРА ===========================
    def calculate_scaled_qty(self, master_size, master_price, symbol):
        """
        Возвращает масштабированное количество для подписчика.
        Учитывает SIZE_SCALE, DYNAMIC_SCALE, DYN_SCALE_FACTOR и Smart-Scaling по волатильности.
        """
        if master_size == 0:
            return 0.0

        size_scale = self.cfg.get("SIZE_SCALE", 1.0)
        dyn_scale = self.cfg.get("DYN_SCALE_FACTOR", 0.9)
        qty = master_size * size_scale

        # ===== Smart-Scaling по волатильности =====
        if self.cfg.get("VOLATILITY_SCALE", True):
            vol = self.api.get_volatility(symbol)
            if vol > 25:
                qty *= 0.5
                logging.info(f"⚠️ {symbol}: высокая волатильность {vol:.1f}% → размер ×0.5")
            elif vol > 15:
                qty *= 0.7
                logging.info(f"⚠️ {symbol}: средняя волатильность {vol:.1f}% → размер ×0.7")

        # ===== Динамический масштаб по equity =====
        if self.cfg.get("DYNAMIC_SCALE", True):
            master_eq = self.api.get_master_equity()
            follower_eq = self.api.get_follower_equity()
            if master_eq > 0:
                ratio = (follower_eq / master_eq) * dyn_scale
                qty *= min(size_scale, ratio)
                logging.info(f"🔹 Динамическое масштабирование: {ratio:.2f}")

        # ===== Ограничение по equity-риск % =====
        follower_eq = self.api.get_follower_equity()
        max_risk = self.cfg.get("MAX_EQUITY_RISK_PCT", 2.0)
        if follower_eq > 0:
            max_notional = follower_eq * (max_risk / 100)
            qty_value = master_price * qty
            if qty_value > max_notional:
                qty = max_notional / master_price
                logging.info(f"⚠️ {symbol}: ограничено по риску {max_risk}% → {qty}")

        return round(qty, 3)

    # ====================== ЛОКАЛЬНЫЙ STOP LOSS ======================
    async def check_local_stoploss(self, symbol):
        """Закрывает позицию, если цена ушла против больше LOCAL_SL_PCT%"""
        local_sl = self.cfg.get("LOCAL_SL_PCT", 25)
        if local_sl <= 0:
            return

        pos = self.api.get_position(symbol)
        if not pos or float(pos["size"]) == 0:
            return

        entry = float(pos.get("avgPrice") or 0)
        mark = self.api.get_mark_price(symbol)
        if entry == 0 or mark == 0:
            return

        change = (mark - entry) / entry * (1 if pos["side"] == "Buy" else -1) * 100
        if change <= -local_sl:
            logging.warning(f"🟥 {symbol}: цена ушла против на {abs(change):.2f}% > {local_sl}% → закрытие позиции")
            self.api.close_position(symbol)
            return True
        return False

    # ====================== АВТО-ПАУЗА ======================
    async def check_autopause(self):
        """
        Проверка просадки equity → если > EQUITY_DRAWDOWN_PCT → COPY_ACTIVE=False
        """
        now = time.time()
        if now - self.last_check < 10:
            return
        self.last_check = now

        follower_eq = self.api.get_follower_equity()
        self.max_equity = max(self.max_equity, follower_eq)
        drawdown_pct = 0
        if self.max_equity > 0:
            drawdown_pct = (1 - follower_eq / self.max_equity) * 100

        limit = self.cfg.get("EQUITY_DRAWDOWN_PCT", 15)
        if drawdown_pct >= limit and self.cfg.get("COPY_ACTIVE", True):
            logging.warning(f"🛑 Просадка {drawdown_pct:.1f}% ≥ {limit}% → пауза копирования")
            self.cfg["COPY_ACTIVE"] = False
            save_config(self.cfg)

            # Закрытие всех позиций, если включено AUTO_CLOSE_ON_DRAWDOWN
            if self.cfg.get("AUTO_CLOSE_ON_DRAWDOWN", False):
                positions = self.api.get_positions()
                for pos in positions:
                    if float(pos["size"]) != 0:
                        self.api.close_position(pos["symbol"])

            # Отправить уведомление
            self.api.send_telegram_message("⚠️ Копирование приостановлено из-за просадки депозита")

    # ====================== ПРОЧИЕ ПРОВЕРКИ ======================
    def check_liq_buffer(self, symbol):
        """Проверка минимального буфера до ликвидации"""
        buf_min = self.cfg.get("MIN_LIQ_BUFFER_PCT", 20)
        pos = self.api.get_position(symbol)
        if not pos or float(pos["size"]) == 0:
            return
        mark = self.api.get_mark_price(symbol)
        liq = float(pos.get("liqPrice") or 0)
        if mark and liq:
            buffer = abs(mark - liq) / mark * 100
            if buffer < buf_min:
                logging.warning(f"⚠️ {symbol}: буфер ликвидации {buffer:.2f}% < {buf_min}%")
