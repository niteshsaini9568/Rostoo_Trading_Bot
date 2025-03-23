# api_client.py
import time
import hmac
import hashlib
import requests
import asyncio

class RoostooAPIClient:
    def __init__(self, api_key, secret_key, base_url="https://mock-api.roostoo.com"):
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.base_url = base_url

    def _get_timestamp(self):
        return str(int(time.time() * 1000))

    def _sign(self, params: dict):
        sorted_items = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_items])
        return hmac.new(self.secret_key, query_string.encode(), hashlib.sha256).hexdigest()

    def _headers(self, params: dict, is_signed=False):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if is_signed:
            signature = self._sign(params)
            headers["RST-API-KEY"] = self.api_key
            headers["MSG-SIGNATURE"] = signature
        return headers

    async def get_market_data(self, pair: str):
        params = {"pair": pair, "timestamp": self._get_timestamp()}
        return await self._make_signed_request("GET", "/v3/ticker", params)

    async def get_balance(self):
        return await self._make_signed_request("GET", "/v3/balance", {})

    async def place_order(self, pair: str, side: str, quantity: float):
        params = {"pair": pair, "side": side, "type": "MARKET", "quantity": str(quantity), "timestamp": self._get_timestamp()}
        return await self._make_signed_request("POST", "/v3/place_order", params)

    async def _make_signed_request(self, method: str, endpoint: str, params: dict):
        params["timestamp"] = self._get_timestamp()
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = self._sign(params)
        headers = self._headers(params, is_signed=True)
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
            else:
                response = await asyncio.to_thread(requests.post, url, headers=headers, data=params)
            return response.json() if response.text else {"Success": False, "Error": "Empty response"}
        except Exception as e:
            return {"Success": False, "Error": str(e)}