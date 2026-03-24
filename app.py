from __future__ import annotations

import logging
from pathlib import Path

from config import load_config
from exchange import OkxDemoClient


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "openclaw.log"


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
        force=True,
    )
    return logging.getLogger("openclaw")


def _to_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def summarize_balance(balance_rows: list[dict[str, str]]) -> dict[str, float]:
    if not balance_rows:
        return {}

    account = balance_rows[0]
    return {
        "total_equity_usd": _to_float(account.get("totalEq")),
        "available_equity_usd": _to_float(account.get("availEq")),
        "isolated_margin_used_usd": _to_float(account.get("isoEq")),
        "initial_margin_required_usd": _to_float(account.get("imr")),
        "maintenance_margin_required_usd": _to_float(account.get("mmr")),
        "unrealized_pnl_usd": _to_float(account.get("upl")),
    }


def summarize_positions(positions: list[dict[str, str]]) -> tuple[list[dict[str, float | str]], float]:
    summary: list[dict[str, float | str]] = []
    total_notional = 0.0

    for position in positions:
        size = _to_float(position.get("pos"))
        if size == 0:
            continue

        mark_price = _to_float(position.get("markPx"))
        notional = _to_float(position.get("notionalUsd"))
        total_notional += notional
        summary.append(
            {
                "instId": position.get("instId", ""),
                "side": position.get("posSide") or position.get("side") or "net",
                "contracts": size,
                "mark_price": mark_price,
                "notional_usd": notional,
                "margin_usd": _to_float(position.get("margin")),
                "upl_usd": _to_float(position.get("upl")),
                "avg_px": _to_float(position.get("avgPx")),
                "liquidation_px": _to_float(position.get("liqPx")),
                "reported_leverage": _to_float(position.get("lever")),
            }
        )

    return summary, total_notional


def main() -> None:
    logger = configure_logging()
    config = load_config()
    client = OkxDemoClient(config)

    balance_rows = client.fetch_balance()
    positions = client.fetch_positions("SWAP")
    ticker = client.fetch_ticker("BTC-USDT-SWAP")
    instrument = client.fetch_instrument("BTC-USDT-SWAP", "SWAP")
    balance_summary = summarize_balance(balance_rows)
    position_summary, total_position_notional = summarize_positions(positions)
    contract_value = _to_float(instrument.get("ctVal"))
    contract_multiplier = _to_float(instrument.get("ctMult")) or 1.0

    logger.info("OKX connectivity check succeeded.")
    logger.info("Simulated trading: %s", config.simulated_trading)
    logger.info("Balance rows returned: %s", len(balance_rows))
    logger.info(
        "BTC-USDT-SWAP ticker:"
        " last=%s, bidPx=%s, askPx=%s",
        ticker.get("last"),
        ticker.get("bidPx"),
        ticker.get("askPx"),
    )
    logger.info(
        "Account funds:"
        " total_equity_usd=%.2f available_equity_usd=%.2f"
        " initial_margin_required_usd=%.2f maintenance_margin_required_usd=%.2f"
        " unrealized_pnl_usd=%.2f isolated_margin_used_usd=%.2f",
        balance_summary.get("total_equity_usd", 0.0),
        balance_summary.get("available_equity_usd", 0.0),
        balance_summary.get("initial_margin_required_usd", 0.0),
        balance_summary.get("maintenance_margin_required_usd", 0.0),
        balance_summary.get("unrealized_pnl_usd", 0.0),
        balance_summary.get("isolated_margin_used_usd", 0.0),
    )
    logger.info(
        "Instrument BTC-USDT-SWAP:"
        " ctVal=%s ctValCcy=%s ctMult=%s lotSz=%s minSz=%s lever=%s",
        instrument.get("ctVal"),
        instrument.get("ctValCcy"),
        instrument.get("ctMult"),
        instrument.get("lotSz"),
        instrument.get("minSz"),
        instrument.get("lever"),
    )
    logger.info(
        "Open swap positions: count=%s total_notional_usd=%.2f",
        len(position_summary),
        total_position_notional,
    )

    if not position_summary:
        logger.info("No open swap positions found.")
        return

    for position in position_summary:
        estimated_leverage = (
            position["notional_usd"] / position["margin_usd"]
            if position["margin_usd"]
            else 0.0
        )
        coin_exposure = position["contracts"] * contract_value * contract_multiplier
        logger.info(
            "Position %s side=%s contracts=%s avg_px=%.2f mark_price=%.2f"
            " notional_usd=%.2f margin_usd=%.2f upl_usd=%.2f"
            " coin_exposure=%s estimated_leverage=%.2f reported_leverage=%.2f liquidation_px=%.2f",
            position["instId"],
            position["side"],
            position["contracts"],
            position["avg_px"],
            position["mark_price"],
            position["notional_usd"],
            position["margin_usd"],
            position["upl_usd"],
            coin_exposure,
            estimated_leverage,
            position["reported_leverage"],
            position["liquidation_px"],
        )


if __name__ == "__main__":
    main()
