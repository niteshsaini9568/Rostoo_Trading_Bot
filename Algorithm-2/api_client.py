# api_client.py
import requests
import hmac
import hashlib
import time
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class RoostooAPIClient:
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://mock-api.roostoo.com"):
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.base_url = base_url
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def _get_timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def _sign(self, params: Dict) -> str:
        sorted_items = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_items])
        return hmac.new(self.secret_key, query_string.encode(), hashlib.sha256).hexdigest()

    def _headers(self, params: Dict, signed: bool = False) -> Dict:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if signed:
            signature = self._sign(params)
            headers["RST-API-KEY"] = self.api_key
            headers["MSG-SIGNATURE"] = signature
        return headers

    def _handle_response(self, response: requests.Response) -> Optional[Dict]:
        if response.status_code != 200:
            logging.error(f"HTTP Error: {response.status_code} - {response.text}")
            return None
        try:
            return response.json()
        except Exception as e:
            logging.error(f"JSON parse error: {e}")
            return None

    def get_all_tickers(self) -> Optional[Dict]:
        params = {"timestamp": self._get_timestamp()}
        response = self.session.get(f"{self.base_url}/v3/ticker", params=params, headers=self._headers(params, signed=False))
        return self._handle_response(response)

    def get_balance(self) -> Optional[Dict]:
        params = {"timestamp": self._get_timestamp()}
        response = self.session.get(f"{self.base_url}/v3/balance", params=params, headers=self._headers(params, signed=True))
        return self._handle_response(response)

    def place_order(self, pair: str, side: str, order_type: str, quantity: str) -> Optional[Dict]:
        params = {"pair": pair, "side": side, "type": order_type, "quantity": quantity, "timestamp": self._get_timestamp()}
        response = self.session.post(f"{self.base_url}/v3/place_order", data=params, headers=self._headers(params, signed=True))
        return self._handle_response(response)