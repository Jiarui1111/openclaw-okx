# openclaw-okx

# OpenClaw OKX Demo MVP

Step 1 of the workflow is exchange connectivity.

This project starts with a minimal OKX demo trading connectivity check:

- load API credentials from `.env`
- connect to OKX demo trading
- fetch account balance
- fetch a ticker for `BTC-USDT-SWAP`
- optionally load a trading signal from `lobster_signal.json`

## Setup

1. Create an OKX demo trading API key.
2. Copy `.env.example` to `.env`.
3. Fill in your credentials.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run:

```bash
python app.py
```

## Notes

- This script uses the OKX official Python SDK.
- Demo trading is enabled with `flag = "1"`.
- No orders are placed in this step.
- Signal priority is `lobster_signal.json` first, then `.env` fallback.
