from __future__ import annotations

from typing import Any

from okx import Account
from okx import MarketData

from config import OkxConfig


class OkxDemoClient:
    def __init__(self, config: OkxConfig) -> None:
        self._account_api = Account.AccountAPI(
            api_key=config.api_key,
            api_secret_key=config.secret_key,
            passphrase=config.passphrase,
            use_server_time=config.use_server_time,
            flag=config.flag,
            debug=False,
        )
        self._market_api = MarketData.MarketAPI(flag=config.flag)

    def fetch_balance(self) -> list[dict[str, Any]]:
        response = self._account_api.get_account_balance()
        self._raise_if_error(response, "fetch account balance")
        return response.get("data", [])

    def fetch_positions(self, instrument_type: str = "SWAP") -> list[dict[str, Any]]:
        response = self._account_api.get_positions(instType=instrument_type)
        self._raise_if_error(response, f"fetch positions for {instrument_type}")
        return response.get("data", [])

    def fetch_ticker(self, instrument_id: str) -> dict[str, Any]:
        response = self._market_api.get_ticker(instId=instrument_id)
        self._raise_if_error(response, f"fetch ticker for {instrument_id}")
        data = response.get("data", [])
        if not data:
            raise RuntimeError(f"No ticker data returned for {instrument_id}")
        return data[0]

    @staticmethod
    def _raise_if_error(response: dict[str, Any], action: str) -> None:
        code = response.get("code")
        if code not in (None, "0", 0):
            message = response.get("msg", "unknown error")
            raise RuntimeError(f"Failed to {action}: code={code}, msg={message}")
