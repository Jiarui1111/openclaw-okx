from __future__ import annotations

from typing import Any

from okx import Account
from okx import MarketData
from okx import PublicData
from okx import Trade

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
        self._public_api = PublicData.PublicAPI(flag=config.flag)
        self._trade_api = Trade.TradeAPI(
            api_key=config.api_key,
            api_secret_key=config.secret_key,
            passphrase=config.passphrase,
            use_server_time=config.use_server_time,
            flag=config.flag,
            debug=False,
        )

    def fetch_balance(self) -> list[dict[str, Any]]:
        response = self._account_api.get_account_balance()
        self._raise_if_error(response, "fetch account balance")
        return response.get("data", [])

    def fetch_positions(self, instrument_type: str = "SWAP") -> list[dict[str, Any]]:
        response = self._account_api.get_positions(instType=instrument_type)
        self._raise_if_error(response, f"fetch positions for {instrument_type}")
        return response.get("data", [])

    def fetch_account_config(self) -> list[dict[str, Any]]:
        response = self._account_api.get_account_config()
        self._raise_if_error(response, "fetch account config")
        return response.get("data", [])

    def fetch_max_order_size(
        self,
        instrument_id: str,
        trade_mode: str,
        leverage: str | None = None,
    ) -> list[dict[str, Any]]:
        response = None
        if leverage:
            try:
                response = self._account_api.get_max_order_size(
                    instId=instrument_id,
                    tdMode=trade_mode,
                    lever=leverage,
                )
            except TypeError:
                response = self._account_api.get_max_order_size(
                    instId=instrument_id,
                    tdMode=trade_mode,
                )
        else:
            response = self._account_api.get_max_order_size(
                instId=instrument_id,
                tdMode=trade_mode,
            )
        self._raise_if_error(response, f"fetch max order size for {instrument_id}")
        return response.get("data", [])

    def fetch_max_available_size(
        self,
        instrument_id: str,
        trade_mode: str,
    ) -> list[dict[str, Any]]:
        response = self._account_api.get_max_avail_size(instId=instrument_id, tdMode=trade_mode)
        self._raise_if_error(response, f"fetch max available size for {instrument_id}")
        return response.get("data", [])

    def fetch_pending_orders(self, instrument_type: str = "SWAP") -> list[dict[str, Any]]:
        response = self._trade_api.get_order_list(instType=instrument_type)
        self._raise_if_error(response, f"fetch pending orders for {instrument_type}")
        return response.get("data", [])

    def fetch_ticker(self, instrument_id: str) -> dict[str, Any]:
        response = self._market_api.get_ticker(instId=instrument_id)
        self._raise_if_error(response, f"fetch ticker for {instrument_id}")
        data = response.get("data", [])
        if not data:
            raise RuntimeError(f"No ticker data returned for {instrument_id}")
        return data[0]

    def fetch_instrument(self, instrument_id: str, instrument_type: str = "SWAP") -> dict[str, Any]:
        response = self._public_api.get_instruments(instType=instrument_type, instId=instrument_id)
        self._raise_if_error(response, f"fetch instrument details for {instrument_id}")
        data = response.get("data", [])
        if not data:
            raise RuntimeError(f"No instrument details returned for {instrument_id}")
        return data[0]

    def place_limit_order(
        self,
        instrument_id: str,
        trade_mode: str,
        side: str,
        size_contracts: float,
        price: float,
        position_side: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "instId": instrument_id,
            "tdMode": trade_mode,
            "side": side,
            "ordType": "limit",
            "px": f"{price}",
            "sz": f"{size_contracts}",
        }
        if position_side:
            kwargs["posSide"] = position_side
        response = self._trade_api.place_order(**kwargs)
        self._raise_if_error(response, f"place limit order for {instrument_id}")
        data = response.get("data", [])
        if not data:
            raise RuntimeError(f"No order response returned for {instrument_id}")
        return data[0]

    @staticmethod
    def _raise_if_error(response: dict[str, Any], action: str) -> None:
        code = response.get("code")
        if code not in (None, "0", 0):
            message = response.get("msg", "unknown error")
            raise RuntimeError(f"Failed to {action}: code={code}, msg={message}")
