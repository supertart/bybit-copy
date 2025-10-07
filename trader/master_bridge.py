import logging
from utils.api_wrappers import BybitHTTP


class MasterBridge:
    """
    Источник данных о позициях мастера.
    Поддерживает:
    - обычный аккаунт (trade)
    - мастер копитрейдинга (copy)
    """

    def __init__(self, cfg):
        mode = cfg.get("MASTER_MODE", "trade").lower()
        net = cfg.get("MASTER_NET", "mainnet").lower()
        testnet = net == "testnet"

        self.mode = mode
        self.api = BybitHTTP(
            cfg["MASTER_API_KEY"],
            cfg["MASTER_API_SECRET"],
            testnet=testnet
        )

        logging.info(f"🧩 Инициализация мастера ({mode}, сеть={net})")

    def get_positions(self):
        """Получение позиций мастера"""
        if self.mode == "copy":
            return self.get_copy_positions()
        else:
            return self.get_trade_positions()

    def get_trade_positions(self):
        """Позиции обычного торгового аккаунта"""
        return self.api.get_positions()

    def get_copy_positions(self):
        """Позиции мастера копитрейдинга Bybit"""
        try:
            res = self.api._request("GET", "/v5/copytrading/master/positions")
            if not res:
                return []
            return res.get("list", [])
        except Exception as e:
            logging.warning(f"Ошибка запроса позиций копитрейд-мастера: {e}")
            return []
