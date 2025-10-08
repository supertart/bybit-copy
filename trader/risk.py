"""
Модуль управления рисками (Risk Manager)
---------------------------------------
Анализирует параметры позиции, проверяет доступный баланс,
расчёт максимально допустимого лота и оценку риска ликвидации.
"""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Менеджер рисков подписчика.
    Проверяет, можно ли открыть сделку и с каким объёмом.
    """

    def __init__(self, cfg: dict, api=None):
        """
        cfg — конфигурация (.env)
        api — объект подключения к Bybit API (может быть None)
        """
        self.cfg = cfg
        self.api = api
        self.max_leverage = 50           # макс. разрешённое плечо
        self.max_risk_per_trade = 0.05   # доля риска на сделку (5%)
        self.min_balance_threshold = 10  # минимум для работы (USDT)
        self.test_mode = self.cfg.get("FOLLOWER_NET", "mainnet") == "testnet"

        logger.info(
            f"🔒 Инициализация RiskManager (test_mode={self.test_mode}, "
            f"max_risk={self.max_risk_per_trade * 100:.1f}%)"
        )

    # ================================================================
    # 🔹 Проверка достаточности баланса
    # ================================================================

    def check_balance(self, balance: float) -> bool:
        """Проверяет, достаточно ли средств для открытия сделки"""
        if balance < self.min_balance_threshold:
            logger.warning(
                f"⚠️ Недостаточный баланс ({balance:.2f} USDT) "
                f"— минимум {self.min_balance_threshold:.2f} USDT."
            )
            return False
        return True

    # ================================================================
    # 🔹 Расчёт максимально допустимого размера позиции
    # ================================================================

    def calculate_position_size(self, balance: float, price: float, leverage: float = 10) -> float:
        """
        Расчёт объёма позиции исходя из допустимого риска.
        """
        if balance <= 0 or price <= 0:
            logger.error("❌ Неверные входные данные для расчёта позиции.")
            return 0.0

        risk_amount = balance * self.max_risk_per_trade
        allowed_margin = risk_amount * leverage
        position_size = allowed_margin / price

        logger.debug(
            f"💰 Расчёт размера позиции: баланс={balance:.2f}, риск={risk_amount:.2f}, "
            f"цена={price:.2f}, плечо={leverage}, объём={position_size:.6f}"
        )
        return round(position_size, 6)

    # ================================================================
    # 🔹 Проверка на возможную ликвидацию
    # ================================================================

    def check_liquidation_risk(self, side: str, entry_price: float, balance: float, leverage: float = 10) -> bool:
        """
        Оценивает риск ликвидации при неблагоприятном движении.
        """
        if not all([entry_price, balance]):
            logger.warning("⚠️ Недостаточно данных для оценки риска ликвидации.")
            return False

        liquidation_distance = (1 / leverage) * 100
        logger.debug(
            f"📉 Риск ликвидации для {side.upper()}: плечо={leverage} → "
            f"допустимое движение ±{liquidation_distance:.2f}%"
        )

        if leverage > self.max_leverage:
            logger.warning(f"🚫 Превышено макс. плечо: {leverage}x (лимит {self.max_leverage}x)")
            return False

        return True

    # ================================================================
    # 🔹 Применение параметров риска к сделке
    # ================================================================

    def apply_risk_rules(self, symbol: str, side: str, price: float, balance: float, leverage: float = 10) -> dict:
        """
        Основная точка входа: применяет риск-правила перед открытием сделки.
        Возвращает dict с рекомендациями.
        """
        if not self.check_balance(balance):
            return {"allowed": False, "reason": "Недостаточно средств"}

        if not self.check_liquidation_risk(side, price, balance, leverage):
            return {"allowed": False, "reason": "Риск ликвидации слишком высок"}

        qty = self.calculate_position_size(balance, price, leverage)
        allowed = qty > 0

        result = {
            "allowed": allowed,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "leverage": leverage,
            "price": price,
            "test_mode": self.test_mode,
        }

        logger.info(
            f"✅ Риск-проверка для {symbol}: "
            f"{'разрешено' if allowed else 'запрещено'}, объём={qty}, плечо={leverage}x"
        )
        return result

    # ================================================================
    # 🔹 Обновление конфигурации (без записи в .env)
    # ================================================================

    def update_settings(self, **kwargs):
        """
        Обновляет параметры риска (в памяти, без сохранения в .env).
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"⚙️ Обновлено значение параметра {key} = {value}")
        logger.info("✅ Конфигурация риска обновлена (без сохранения в .env)")
