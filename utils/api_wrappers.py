import requests
import logging
import time
import hmac
import hashlib
import json
from urllib.parse import urlencode

# ====================== BYBIT API WRAPPER ===========================
class BybitHTTP:
    """
    Упрощённый HTTP-клиент для работы с API Bybit.
    Работает как с мастером, так и с подписчиком.
    """

    def __init__(self, api_key, api_secret, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ---------- Вспомогательные ----------
    def _sign(self, params):
        param_str = urlencode(sorted(params.items()))
        return hmac.new(
            bytes(self.api_secret, "utf-8"),
            bytes(param_str, "utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method, path, params=None, body=None, auth=True):
        url = f"{self.base_url}{path}"
        headers = {}
        if auth:
            timestamp = str(int(time.time() * 1000))
            params = params or {}
            params.update({"api_key": self.api_key, "timestamp": timestamp})
            sign = self._sign(params)
            params["sign"] = sign
        try:
            if method == "GET":
                r = self.session.get(url, params=params, timeout=10)
            else:
                r = self.session.post(url, json=body or params, timeout=10)
            data = r.json()
            if data.get("retCode", 0) != 0:
                logging.warning(f"Bybit API error {path}: {data}")
            return data.get("result", {})
        except Exception as e:
            logging.warning(f"Bybit request failed: {e}")
            return {}

    # ---------- Основные методы ----------
    def get_positions(self):
        """Возвращает список открытых позиций"""
        res = self._request("GET", "/v5/position/list", {"category": "linear"})
        return res.get("list", []) if isinstance(res, dict) else []

    def get_position(self, symbol):
        for pos in self.get_positions():
            if pos["symbol"] == symbol:
                return pos
        return None

    def get_mark_price(self, symbol):
        res = self._request("GET", "/v5/market/tickers", {"category": "linear", "symbol": symbol})
        try:
            return float(res["list"][0]["markPrice"])
        except Exception:
            return 0.0

    def get_volatility(self, symbol):
        """Приближение: волатильность = abs(price24hPcnt)*100"""
        res = self._request("GET", "/v5/market/tickers", {"category": "linear", "symbol": symbol})
        try:
            return abs(float(res["list"][0]["price24hPcnt"])) * 100
        except Exception:
            return 0.0

    def market_order(self, symbol, side, qty, reduce_only=False):
        """Отправка маркет-ордера"""
        body = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(qty),
            "reduceOnly": reduce_only
        }
        res = self._request("POST", "/v5/order/create", body)
        logging.info(f"🟢 Ордер {side} {qty} {symbol} → {res}")
        return res

    def close_position(self, symbol):
        """Закрытие всей позиции"""
        pos = self.get_position(symbol)
        if not pos or float(pos.get("size") or 0) == 0:
            return
        side = "Sell" if pos["side"] == "Buy" else "Buy"
        qty = float(pos["size"])
        self.market_order(symbol, side, qty, reduce_only=True)

    def set_take_profit(self, symbol, price):
        pos = self.get_position(symbol)
        if not pos:
            return
        body = {
            "category": "linear",
            "symbol": symbol,
            "takeProfit": str(price)
        }
        self._request("POST", "/v5/position/trading-stop", body)
        logging.info(f"✅ TP {symbol} = {price}")

    def set_stop_loss(self, symbol, price):
        pos = self.get_position(symbol)
        if not pos:
            return
        body = {
            "category": "linear",
            "symbol": symbol,
            "stopLoss": str(price)
        }
        self._request("POST", "/v5/position/trading-stop", body)
        logging.info(f"✅ SL {symbol} = {price}")

    def get_follower_equity(self):
        """Баланс подписчика"""
        res = self._request("GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        try:
            return float(res["list"][0]["coin"][0]["walletBalance"])
        except Exception:
            return 0.0

    def get_master_equity(self):
        """Баланс мастера (тот же метод, но для отдельного API-ключа)"""
        return self.get_follower_equity()

    # ---------- Telegram уведомления ----------
    def send_telegram_message(self, text):
        try:
            token = self.api_key  # заглушка — реальный токен хранится в cfg, не здесь
            logging.info(f"Telegram: {text}")
        except Exception as e:
            logging.warning(f"Ошибка Telegram уведомления: {e}")
