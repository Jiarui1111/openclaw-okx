from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config import OkxConfig


SIGNAL_FILE = Path("lobster_signal.json")


@dataclass(frozen=True)
class TradingSignal:
    source: str
    action: str
    size_contracts: float
    reason: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float


def load_signal_from_file(path: Path = SIGNAL_FILE) -> TradingSignal | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    return TradingSignal(
        source=str(payload.get("source", "lobster_file")),
        action=str(payload.get("action", "buy")).lower(),
        size_contracts=float(payload.get("size_contracts", 0.01)),
        reason=str(payload.get("reason", "file_signal")),
        confidence=float(payload.get("confidence", 0.5)),
        entry_price=float(payload.get("entry_price", 0)),
        stop_loss=float(payload.get("stop_loss", 0)),
        take_profit=float(payload.get("take_profit", 0)),
    )


def load_signal(config: OkxConfig) -> TradingSignal:
    file_signal = load_signal_from_file()
    if file_signal is not None:
        return file_signal

    return TradingSignal(
        source="env_manual",
        action=config.order_side,
        size_contracts=config.order_size_contracts,
        reason="manual_env_input",
        confidence=1.0,
        entry_price=0.0,
        stop_loss=0.0,
        take_profit=0.0,
    )
