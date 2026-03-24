from __future__ import annotations

from dataclasses import dataclass

from config import OkxConfig


@dataclass(frozen=True)
class TradingSignal:
    source: str
    action: str
    size_contracts: float
    reason: str
    confidence: float


def load_signal(config: OkxConfig) -> TradingSignal:
    return TradingSignal(
        source="env_manual",
        action=config.order_side,
        size_contracts=config.order_size_contracts,
        reason="manual_env_input",
        confidence=1.0,
    )
