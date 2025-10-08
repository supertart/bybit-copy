"""
Bybit Unified v5 (demo/testnet/mainnet) — асинхронная обёртка на aiohttp
------------------------------------------------------------------------
Домены:
- demo:    https://api-demo.bybit.com
- testnet: https://api-testnet.bybit.com
- mainnet: https://api.bybit.com

Работаем с UNIFIED + линейные перпетуалы (USDT).
Подпись v5: HMAC_SHA256(secret, ts + apiKey + recvWindow + queryString + body)
timestamp берём с /v5/market/time (timeNano -> ms).

POST: category="linear" кладём в BODY (не в query), чтобы строка подписи совпадала с Bybit.
"""

import aiohttp
import hashlib
import hmac
import json
import logging
import math
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


def _base_url(env: str) -> str:
    env = (env or "mainnet").lower()
    if env == "demo":
        return "https://api-demo.bybit.com"
    if env == "testnet":
        return "https://api-testnet.bybit.com"
    return "https://api.bybit.com"


class BybitAPI:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        is_testnet: bool = False,   # обратная совместимость
        role: str = "UNKNOWN",
        env: Optional[str] = None   # demo | testnet | mainnet
    ):
        self.role = (role or "UNKNOWN").upper()
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.env = (env or ("testnet" if is_testnet else "mainnet")).lower()
        self.base = _base_url(self.env)

        self._session: Optional[aiohttp.ClientSession] = None
        self._recv_window = "20000"

        logger.info(f"🔗 [{self.role}] Bybit v5 Unified init: env={self.env} base={self.base}")

    # ---------------------- низкоуровневые ----------------------

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def _get_server_ts_ms(self) -> str:
        await self._ensure_session()
        url = f"{self.base}/v5/market/time"
        async with self._session.get(url) as r:
            j = await r.json()
        ts_ms = int(math.floor(int(j["result"]["timeNano"]) / 1e6))
        return str(ts_ms)

    def _sign(self, ts: str, query: str, body: str = "") -> str:
        pre_sign = ts + self.api_key + self._recv_window + (query or "") + (body or "")
        return hmac.new(self.api_secret.encode(), pre_sign.encode(), hashlib.sha256).hexdigest()

    async def _request(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None
    ):
        await self._ensure_session()
        params = params or {}
        body = body or {}

        # query string (детерминированный порядок)
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())]) if params else ""
        body_str = json.dumps(body, separators=(",", ":")) if body else ""

        ts = await self._get_server_ts_ms()
        sign = self._sign(ts, query, body_str)

        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": sign,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": self._recv_window,
            "Content-Type": "application/json",
        }

        url = f"{self.base}{path}"
        if query:
            url = f"{url}?{query}"

        try:
            async with self._session.request(method.upper(), url, headers=headers, data=body_str if body else None) as r:
                text = await r.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.role}] Non-JSON response {r.status}: {text[:200]}")
                    r.raise_for_status()
                    return None
                if r.status != 200 or str(data.get("retCode")) != "0":
                    logger.warning(f"[{self.role}] Bybit v5 error: HTTP={r.status} resp={text[:400]}")
                return data
        except Exception as e:
            logger.warning(f"[{self.role}] HTTP error: {e}")
            return None

    # ---------------------- публичные методы ----------------------

    async def check_auth(self) -> bool:
        data = await self._request(
            "GET",
            "/v5/account/wallet-balance",
            params={"accountType": "UNIFIED"},
        )
        ok = bool(data and str(data.get("retCode")) == "0")
        if ok:
            try:
                total = data["result"]["list"][0]["totalEquity"]
                logger.info(f"[{self.role}] ✅ Auth OK — totalEquity={total}")
            except Exception:
                logger.info(f"[{self.role}] ✅ Auth OK")
        else:
            logger.warning(f"[{self.role}] ❌ Auth failed")
        return ok

    async def get_balance(self) -> float:
        data = await self._request(
            "GET",
            "/v5/account/wallet-balance",
            params={"accountType": "UNIFIED"},
        )
        if not data or str(data.get("retCode")) != "0":
            return 0.0
        try:
            coins = data["result"]["list"][0]["coin"]
            for c in coins:
                if c.get("coin") == "USDT":
                    return float(c.get("availableToWithdraw") or c.get("walletBalance") or 0.0)
        except Exception:
            pass
        return 0.0

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Короткая форма (для логики копирования)."""
        data = await self._request(
            "GET",
            "/v5/position/list",
            params={"category": "linear", "accountType": "UNIFIED", "settleCoin": "USDT"},
        )
        result: List[Dict[str, Any]] = []
        if not data or str(data.get("retCode")) != "0":
            return result

        for item in (data.get("result", {}).get("list") or []):
            try:
                size = float(item.get("size") or 0.0)
            except Exception:
                size = 0.0
            if size <= 0:
                continue
            result.append({
                "symbol": (item.get("symbol") or "").upper(),
                "side": (item.get("side") or "").lower(),
                "contracts": size,
                "entryPrice": float(item.get("avgPrice") or 0.0),
                "leverage": int(float(item.get("leverage") or 10)),
            })
        return result

    async def get_open_positions_detailed(self) -> List[Dict[str, Any]]:
        """
        Детальная форма для статистики:
        symbol, side, size, entryPrice, markPrice, positionValue, unrealisedPnl, leverage
        """
        data = await self._request(
            "GET",
            "/v5/position/list",
            params={"category": "linear", "accountType": "UNIFIED", "settleCoin": "USDT"},
        )
        detailed: List[Dict[str, Any]] = []
        if not data or str(data.get("retCode")) != "0":
            return detailed

        for it in (data.get("result", {}).get("list") or []):
            try:
                size = float(it.get("size") or 0.0)
            except Exception:
                size = 0.0
            if size <= 0:
                continue
            entry = float(it.get("avgPrice") or 0.0)
            mark = float(it.get("markPrice") or 0.0)
            pos_val = float(it.get("positionValue") or 0.0)
            upl = float(it.get("unrealisedPnl") or 0.0)
            lev = int(float(it.get("leverage") or 10))
            detailed.append({
                "symbol": (it.get("symbol") or "").upper(),
                "side": (it.get("side") or "").lower(),
                "size": size,
                "entryPrice": entry,
                "markPrice": mark,
                "positionValue": pos_val,     # USDT
                "unrealisedPnl": upl,         # USDT
                "leverage": lev,
            })
        return detailed

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        data = await self._request(
            "POST",
            "/v5/position/set-leverage",
            params={},
            body={"category": "linear", "symbol": symbol.upper(), "buyLeverage": str(leverage), "sellLeverage": str(leverage)},
        )
        return bool(data and str(data.get("retCode")) == "0")

    async def open_position(self, symbol: str, side: str, qty: float, leverage: int = 10):
        side_v5 = "Buy" if side.lower() in ("buy", "long") else "Sell"
        await self.set_leverage(symbol, leverage)
        data = await self._request(
            "POST",
            "/v5/order/create",
            params={},
            body={
                "category": "linear",
                "symbol": symbol.upper(),
                "side": side_v5,
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "IOC",
            },
        )
        if data and str(data.get("retCode")) == "0":
            logger.info(f"[{self.role}] ✅ Opened {symbol} {side_v5} qty={qty}")
            return data
        logger.warning(f"[{self.role}] Failed to open {symbol} {side_v5} qty={qty}")
        return None

    async def close_position(self, symbol: str) -> bool:
        positions = await self.get_open_positions()
        pos = next((p for p in positions if p["symbol"] == symbol.upper()), None)
        if not pos:
            logger.info(f"[{self.role}] Нет открытой позиции по {symbol} — закрывать нечего.")
            return True

        qty = float(pos["contracts"])
        if qty <= 0:
            logger.info(f"[{self.role}] Позиция по {symbol} уже нулевая.")
            return True

        opposite = "Sell" if pos["side"].lower() == "buy" else "Buy"
        data = await self._request(
            "POST",
            "/v5/order/create",
            params={},
            body={
                "category": "linear",
                "symbol": symbol.upper(),
                "side": opposite,
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "IOC",
                "reduceOnly": True,
            },
        )
        ok = bool(data and str(data.get("retCode")) == "0")
        if ok:
            logger.info(f"[{self.role}] 💤 Closed {symbol} with {opposite} qty={qty}")
        else:
            logger.warning(f"[{self.role}] Не удалось закрыть {symbol} ({opposite} {qty})")
        return ok

    async def close(self):
        try:
            if self._session and not self._session.closed:
                await self._session.close()
        except Exception:
            pass
