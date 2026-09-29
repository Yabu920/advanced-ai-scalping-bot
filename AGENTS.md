# Codex Project Instructions

This project is a staged MT5 trading bot project. Stage 1 is foundation and diagnostics only.

- Never add live order execution unless explicitly requested.
- Never hardcode credentials or secrets.
- Never make strategy logic stricter than requested.
- Prefer small, modular files with one clear responsibility.
- Keep backtest and live candle behavior consistent as future stages are added.
- Use closed candles for signal confirmation later.
- Always explain changed files after each task.
- Keep safety first: no real orders, no hidden trading behavior, and no surprise integrations.
