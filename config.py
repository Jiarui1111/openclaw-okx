import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OkxConfig:
    api_key: str
    secret_key: str
    passphrase: str
    use_server_time: bool
    simulated_trading: bool

    @property
    def flag(self) -> str:
        return "1" if self.simulated_trading else "0"


def load_config() -> OkxConfig:
    config = OkxConfig(
        api_key=os.getenv("OKX_API_KEY", "").strip(),
        secret_key=os.getenv("OKX_SECRET_KEY", "").strip(),
        passphrase=os.getenv("OKX_PASSPHRASE", "").strip(),
        use_server_time=_to_bool(os.getenv("OKX_USE_SERVER_TIME"), default=False),
        simulated_trading=_to_bool(os.getenv("OKX_SIMULATED_TRADING"), default=True),
    )

    missing = [
        name
        for name, value in (
            ("OKX_API_KEY", config.api_key),
            ("OKX_SECRET_KEY", config.secret_key),
            ("OKX_PASSPHRASE", config.passphrase),
        )
        if not value
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_list}")

    return config
