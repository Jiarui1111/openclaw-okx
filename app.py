from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import load_config
from exchange import OkxDemoClient
from signals import load_signal


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


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("event=%s %s", event, payload)


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
                "initial_margin_usd": _to_float(position.get("imr")),
                "maintenance_margin_usd": _to_float(position.get("mmr")),
                "upl_usd": _to_float(position.get("upl")),
                "avg_px": _to_float(position.get("avgPx")),
                "liquidation_px": _to_float(position.get("liqPx")),
                "reported_leverage": _to_float(position.get("lever")),
            }
        )

    return summary, total_notional


def summarize_account_config(account_config_rows: list[dict[str, str]]) -> dict[str, str]:
    if not account_config_rows:
        return {}

    config = account_config_rows[0]
    return {
        "account_level": config.get("acctLv", ""),
        "position_mode": config.get("posMode", ""),
        "auto_loan": str(config.get("autoLoan", "")),
        "greeks_type": config.get("greeksType", ""),
        "level": config.get("level", ""),
        "contract_isolated_mode": config.get("ctIsoMode", ""),
        "margin_isolated_mode": config.get("mgnIsoMode", ""),
    }


def infer_trade_mode(account_config: dict[str, str], positions: list[dict[str, str]]) -> str:
    for position in positions:
        trade_mode = position.get("mgnMode")
        if trade_mode:
            return trade_mode
    return "cross"


def summarize_size_rows(rows: list[dict[str, str]]) -> dict[str, float]:
    if not rows:
        return {}

    row = rows[0]
    return {
        "max_buy_contracts": _to_float(row.get("maxBuy")),
        "max_sell_contracts": _to_float(row.get("maxSell")),
        "avail_buy_contracts": _to_float(row.get("availBuy")),
        "avail_sell_contracts": _to_float(row.get("availSell")),
    }


def estimate_margin_used(position: dict[str, float | str]) -> float:
    direct_margin = float(position["margin_usd"])
    if direct_margin > 0:
        return direct_margin

    initial_margin = float(position["initial_margin_usd"])
    if initial_margin > 0:
        return initial_margin

    leverage = float(position["reported_leverage"])
    if leverage > 0:
        return float(position["notional_usd"]) / leverage

    return 0.0


def build_order_plan(
    instrument_id: str,
    trade_mode: str,
    side: str,
    size_contracts: float,
    instrument: dict[str, str],
    ticker: dict[str, str],
) -> dict[str, float | str]:
    contract_value = _to_float(instrument.get("ctVal"))
    contract_multiplier = _to_float(instrument.get("ctMult")) or 1.0
    last_price = _to_float(ticker.get("last"))
    coin_exposure = size_contracts * contract_value * contract_multiplier
    notional_usd = coin_exposure * last_price
    return {
        "instrument_id": instrument_id,
        "trade_mode": trade_mode,
        "side": side,
        "size_contracts": size_contracts,
        "coin_exposure": coin_exposure,
        "notional_usd": notional_usd,
        "reference_price": last_price,
    }


def infer_position_side(side: str, account_config: dict[str, str]) -> str | None:
    if account_config.get("position_mode") != "long_short_mode":
        return None
    return "long" if side == "buy" else "short"


def main() -> None:
    logger = configure_logging()
    config = load_config()
    client = OkxDemoClient(config)
    signal = load_signal(config)

    balance_rows = client.fetch_balance()
    positions = client.fetch_positions("SWAP")
    account_config_rows = client.fetch_account_config()
    ticker = client.fetch_ticker("BTC-USDT-SWAP")
    instrument = client.fetch_instrument(config.instrument_id, "SWAP")
    balance_summary = summarize_balance(balance_rows)
    position_summary, total_position_notional = summarize_positions(positions)
    account_config = summarize_account_config(account_config_rows)
    trade_mode = infer_trade_mode(account_config, positions)
    max_order_size = summarize_size_rows(
        client.fetch_max_order_size(
            config.instrument_id,
            trade_mode,
            leverage=instrument.get("lever"),
        )
    )
    max_available_size = summarize_size_rows(
        client.fetch_max_available_size(config.instrument_id, trade_mode)
    )
    contract_value = _to_float(instrument.get("ctVal"))
    contract_multiplier = _to_float(instrument.get("ctMult")) or 1.0
    order_plan = build_order_plan(
        instrument_id=config.instrument_id,
        trade_mode=config.trade_mode,
        side=signal.action,
        size_contracts=signal.size_contracts,
        instrument=instrument,
        ticker=ticker,
    )
    position_side = infer_position_side(signal.action, account_config)

    logger.info("OKX connectivity check succeeded.")
    log_event(
        logger,
        "startup",
        simulated_trading=config.simulated_trading,
        instrument_id=config.instrument_id,
        trade_mode=config.trade_mode,
        dry_run=config.dry_run,
    )
    log_event(
        logger,
        "signal_loaded",
        source=signal.source,
        action=signal.action,
        size_contracts=f"{signal.size_contracts:.2f}",
        confidence=f"{signal.confidence:.2f}",
        reason=signal.reason,
    )
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
        "Account config:"
        " account_level=%s position_mode=%s contract_isolated_mode=%s margin_isolated_mode=%s auto_loan=%s",
        account_config.get("account_level", ""),
        account_config.get("position_mode", ""),
        account_config.get("contract_isolated_mode", ""),
        account_config.get("margin_isolated_mode", ""),
        account_config.get("auto_loan", ""),
    )
    logger.info(
        "Order sizing:"
        " trade_mode=%s max_buy_contracts=%.2f max_sell_contracts=%.2f"
        " avail_buy_contracts=%.2f avail_sell_contracts=%.2f",
        trade_mode,
        max_order_size.get("max_buy_contracts", 0.0),
        max_order_size.get("max_sell_contracts", 0.0),
        max_available_size.get("avail_buy_contracts", 0.0),
        max_available_size.get("avail_sell_contracts", 0.0),
    )
    logger.info(
        "Order sizing notionals:"
        " max_buy_coin=%.4f max_sell_coin=%.4f avail_buy_coin=%.4f avail_sell_coin=%.4f"
        " max_buy_notional_usd=%.2f max_sell_notional_usd=%.2f"
        " avail_buy_notional_usd=%.2f avail_sell_notional_usd=%.2f",
        max_order_size.get("max_buy_contracts", 0.0) * contract_value * contract_multiplier,
        max_order_size.get("max_sell_contracts", 0.0) * contract_value * contract_multiplier,
        max_available_size.get("avail_buy_contracts", 0.0) * contract_value * contract_multiplier,
        max_available_size.get("avail_sell_contracts", 0.0) * contract_value * contract_multiplier,
        max_order_size.get("max_buy_contracts", 0.0) * contract_value * contract_multiplier * _to_float(ticker.get("last")),
        max_order_size.get("max_sell_contracts", 0.0) * contract_value * contract_multiplier * _to_float(ticker.get("last")),
        max_available_size.get("avail_buy_contracts", 0.0) * contract_value * contract_multiplier * _to_float(ticker.get("last")),
        max_available_size.get("avail_sell_contracts", 0.0) * contract_value * contract_multiplier * _to_float(ticker.get("last")),
    )
    log_event(
        logger,
        "order_plan",
        side=order_plan["side"],
        size_contracts=order_plan["size_contracts"],
        coin_exposure=f"{order_plan['coin_exposure']:.4f}",
        notional_usd=f"{order_plan['notional_usd']:.2f}",
        reference_price=f"{order_plan['reference_price']:.2f}",
        mode="dry_run" if config.dry_run else "live",
        signal_source=signal.source,
    )

    max_contracts_for_side = (
        max_order_size.get("max_buy_contracts", 0.0)
        if signal.action == "buy"
        else max_order_size.get("max_sell_contracts", 0.0)
    )
    if max_contracts_for_side and signal.size_contracts > max_contracts_for_side:
        logger.warning(
            "Configured order size %.2f exceeds current max size %.2f for side=%s",
            signal.size_contracts,
            max_contracts_for_side,
            signal.action,
        )
        log_event(
            logger,
            "order_plan_rejected",
            reason="size_exceeds_max",
            configured_size=f"{signal.size_contracts:.2f}",
            max_size=f"{max_contracts_for_side:.2f}",
            side=signal.action,
        )
    elif config.dry_run:
        logger.info(
            "Dry-run order plan ready: side=%s size_contracts=%.2f estimated_notional_usd=%.2f",
            signal.action,
            signal.size_contracts,
            order_plan["notional_usd"],
        )
    elif not config.simulated_trading:
        logger.warning("Live order blocked because simulated trading is disabled.")
        log_event(
            logger,
            "order_execution_blocked",
            reason="not_in_demo_mode",
            side=signal.action,
            size_contracts=f"{signal.size_contracts:.2f}",
        )
    elif not config.allow_live_demo_orders:
        logger.warning("Live demo order blocked because OPENCLAW_ALLOW_LIVE_DEMO_ORDERS is false.")
        log_event(
            logger,
            "order_execution_blocked",
            reason="live_demo_orders_disabled",
            side=signal.action,
            size_contracts=f"{signal.size_contracts:.2f}",
        )
    else:
        order_result = client.place_market_order(
            instrument_id=config.instrument_id,
            trade_mode=config.trade_mode,
            side=signal.action,
            size_contracts=signal.size_contracts,
            position_side=position_side,
        )
        logger.info(
            "Live demo order placed: ordId=%s clOrdId=%s side=%s size_contracts=%.2f",
            order_result.get("ordId"),
            order_result.get("clOrdId"),
            signal.action,
            signal.size_contracts,
        )
        log_event(
            logger,
            "order_submitted",
            ord_id=order_result.get("ordId", ""),
            cl_ord_id=order_result.get("clOrdId", ""),
            side=signal.action,
            size_contracts=f"{signal.size_contracts:.2f}",
            position_side=position_side or "net",
            signal_source=signal.source,
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
        effective_margin = estimate_margin_used(position)
        estimated_leverage = position["notional_usd"] / effective_margin if effective_margin else 0.0
        coin_exposure = position["contracts"] * contract_value * contract_multiplier
        logger.info(
            "Position %s side=%s contracts=%s avg_px=%.2f mark_price=%.2f"
            " notional_usd=%.2f margin_usd=%.2f initial_margin_usd=%.2f maintenance_margin_usd=%.2f upl_usd=%.2f"
            " coin_exposure=%s estimated_leverage=%.2f reported_leverage=%.2f liquidation_px=%.2f",
            position["instId"],
            position["side"],
            position["contracts"],
            position["avg_px"],
            position["mark_price"],
            position["notional_usd"],
            effective_margin,
            position["initial_margin_usd"],
            position["maintenance_margin_usd"],
            position["upl_usd"],
            coin_exposure,
            estimated_leverage,
            position["reported_leverage"],
            position["liquidation_px"],
        )


if __name__ == "__main__":
    main()
