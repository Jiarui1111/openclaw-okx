from __future__ import annotations

from config import load_config
from exchange import OkxDemoClient


def main() -> None:
    config = load_config()
    client = OkxDemoClient(config)

    balance_rows = client.fetch_balance()
    ticker = client.fetch_ticker("BTC-USDT-SWAP")

    print("OKX connectivity check succeeded.")
    print(f"Simulated trading: {config.simulated_trading}")
    print(f"Balance rows returned: {len(balance_rows)}")
    print(
        "BTC-USDT-SWAP ticker:"
        f" last={ticker.get('last')}, bidPx={ticker.get('bidPx')}, askPx={ticker.get('askPx')}"
    )


if __name__ == "__main__":
    main()
