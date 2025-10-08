import os
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def _as_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def load_config() -> dict:
    # Загружаем .env (молчаливо)
    load_dotenv(_ENV_PATH, override=False)

    # Новые ключи окружения (предпочтительны)
    master_env = os.getenv("MASTER_ENV", "").strip().lower()
    follower_env = os.getenv("FOLLOWER_ENV", "").strip().lower()

    # Обратная совместимость: если MASTER_ENV/FOLLOWER_ENV не заданы — читаем старые MASTER_NET/FOLLOWER_NET
    if master_env not in ("demo", "testnet", "mainnet"):
        master_env = os.getenv("MASTER_NET", "mainnet").strip().lower()
    if follower_env not in ("demo", "testnet", "mainnet"):
        follower_env = os.getenv("FOLLOWER_NET", "mainnet").strip().lower()

    cfg = {
        # мастер: может быть обычный trade-аккаунт или "copy" (копитрейдер Bybit). Логика у тебя уже есть.
        "MASTER_MODE": os.getenv("MASTER_MODE", "trade").strip(),  # trade | copy

        # сети/окружения
        "MASTER_ENV": master_env,       # demo | testnet | mainnet
        "FOLLOWER_ENV": follower_env,   # demo | testnet | mainnet

        # API ключи
        "MASTER_API_KEY": os.getenv("MASTER_API_KEY", "").strip(),
        "MASTER_API_SECRET": os.getenv("MASTER_API_SECRET", "").strip(),
        "FOLLOWER_API_KEY": os.getenv("FOLLOWER_API_KEY", "").strip(),
        "FOLLOWER_API_SECRET": os.getenv("FOLLOWER_API_SECRET", "").strip(),

        # Telegram
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        "TELEGRAM_USER_ID": int(os.getenv("TELEGRAM_USER_ID", "0") or "0"),

        # Риск и поведение
        "TEST_MODE": _as_bool(os.getenv("TEST_MODE", "true")),  # вкл/выкл торговлю у подписчика
        "MAX_RISK_PCT": float(os.getenv("MAX_RISK_PCT", "5.0") or "5.0"),

        # Интервалы опроса
        "POLL_INTERVAL_SEC": float(os.getenv("POLL_INTERVAL_SEC", "5") or "5"),

        # Файл состояния
        "STATE_FILE": os.getenv("STATE_FILE", "state.json").strip(),
    }
    return cfg
