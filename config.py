import os
import json
from dotenv import load_dotenv

CONFIG_FILE = "state.json"

def load_config():
    load_dotenv()

    config = {
        # API
        "MASTER_API_KEY": os.getenv("MASTER_API_KEY", ""),
        "MASTER_API_SECRET": os.getenv("MASTER_API_SECRET", ""),
        "FOLLOWER_API_KEY": os.getenv("FOLLOWER_API_KEY", ""),
        "FOLLOWER_API_SECRET": os.getenv("FOLLOWER_API_SECRET", ""),
        # Telegram
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
        # State
        "STATE_FILE": os.getenv("STATE_FILE", CONFIG_FILE),
        # Flags
        "TESTNET": os.getenv("TESTNET", "False").lower() == "true"
    }

    # Загружаем пользовательские настройки, если есть
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            config.update(state)

    return config


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
