"""Beginner-friendly MT5 connection troubleshooting script."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import MetaTrader5 as mt5

from config.settings import Settings
from config.symbols import normalize_symbol
from mt5.connection import MT5Connection
from utils.logger import setup_logger


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    return str(value)


def print_terminal_info(info: dict[str, Any] | None) -> None:
    print_section("Terminal Info")
    if not info:
        print("Terminal info is unavailable.")
        print(f"MT5 last error: {mt5.last_error()}")
        return

    print(f"Name: {format_value(info.get('name'))}")
    print(f"Path: {format_value(info.get('path'))}")
    print(f"Connected: {format_value(info.get('connected'))}")
    print(f"Trade allowed: {format_value(info.get('trade_allowed'))}")
    print(f"Community account: {format_value(info.get('community_account'))}")


def print_account_info(info: dict[str, Any] | None) -> None:
    print_section("Account Info")
    if not info:
        print("Account info is unavailable.")
        print("If you did not provide credentials, make sure MT5 is already logged in.")
        print(f"MT5 last error: {mt5.last_error()}")
        return

    print(f"Login: {format_value(info.get('login'))}")
    print(f"Server: {format_value(info.get('server'))}")
    print(f"Balance: {format_value(info.get('balance'))}")
    print(f"Equity: {format_value(info.get('equity'))}")
    print(f"Currency: {format_value(info.get('currency'))}")


def print_symbol_test(symbol: str) -> None:
    print_section("Symbol Visibility Test")
    normalized = normalize_symbol(symbol)
    print(f"Symbol: {normalized}")

    info = mt5.symbol_info(normalized)
    if info is None:
        print("Result: symbol was not found in this MT5 terminal.")
        print("Tip: check the broker symbol name. Some brokers use suffixes like XAUUSDm.")
        print(f"MT5 last error: {mt5.last_error()}")
        return

    if info.visible:
        print("Result: symbol is visible in Market Watch.")
    elif mt5.symbol_select(normalized, True):
        print("Result: symbol was found and selected in Market Watch.")
    else:
        print("Result: symbol exists but could not be selected.")
        print(f"MT5 last error: {mt5.last_error()}")

    tick = mt5.symbol_info_tick(normalized)
    if tick is None:
        print("Latest tick: unavailable.")
    else:
        print(f"Latest bid: {format_value(tick.bid)}")
        print(f"Latest ask: {format_value(tick.ask)}")


def print_path_check(settings: Settings) -> None:
    print_section("Configured MT5 Path")
    print(f"MT5_PATH: {settings.mt5_path or 'not set'}")

    if not settings.mt5_path:
        print("Path check: skipped. The MetaTrader5 package will try default terminal discovery.")
        return

    mt5_path = Path(settings.mt5_path).expanduser()
    if mt5_path.exists():
        print("Path check: exists.")
    else:
        print("Path check: does not exist.")
        print("Tip: MT5_PATH should point to terminal64.exe, not a desktop shortcut.")


def print_ipc_hints() -> None:
    print_section("IPC Timeout Hints")
    print("If you see (-10005, 'IPC timeout'):")
    print("1. Open MT5 manually first.")
    print("2. Confirm the account is logged in.")
    print("3. Confirm Market Watch prices are moving.")
    print("4. Set MT5_PATH to terminal64.exe, not a shortcut.")
    print("5. Use the same Windows permission level for MT5 and Python.")
    print("6. Close duplicate MT5 terminals.")
    print("7. Restart MT5 and try again.")


def print_authorization_hints() -> None:
    print_section("Authorization Failed Hints")
    print("If you see (-6, 'Terminal: Authorization failed'):")
    print("1. Open MT5 manually and log into the trading account.")
    print("2. Confirm the bottom-right connection status is active.")
    print("3. Confirm Market Watch prices are moving.")
    print("4. If manual login is not enough, fill MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER in .env.")
    print("5. Make sure MT5_SERVER exactly matches the broker server name shown in MT5.")
    print("6. If multiple terminals are installed, set MT5_PATH to the correct terminal64.exe.")
    print("7. Restart MT5, then run this script again.")


def print_error_hints(error: Any) -> None:
    if isinstance(error, tuple) and len(error) > 0 and error[0] == -10005:
        print_ipc_hints()
    elif isinstance(error, tuple) and len(error) > 0 and error[0] == -6:
        print_authorization_hints()
    else:
        print_section("General MT5 Hints")
        print("1. Open MT5 manually first.")
        print("2. Confirm the account is logged in and prices are moving.")
        print("3. Set MT5_PATH if Python may be finding the wrong terminal.")
        print("4. Restart MT5 and try again.")


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("MT5 Connection Check")
    print("====================")
    print("This script only checks MT5 connectivity. It does not place trades.")

    print_path_check(settings)

    connection = MT5Connection(settings)
    logger.info("Running standalone MT5 connection check.")
    if not connection.initialize():
        error = connection.get_last_error() or mt5.last_error()
        print_section("Connection Result")
        print("Result: MT5 initialization or login failed.")
        print(f"MT5 last error: {error}")
        print_error_hints(error)
        return 1

    try:
        print_section("Connection Result")
        print("Result: MT5 initialized successfully.")
        print_terminal_info(connection.get_terminal_info())
        print_account_info(connection.get_account_info())
        print_symbol_test(settings.default_symbol)
        return 0
    finally:
        connection.shutdown()
        print_section("Shutdown")
        print("MT5 connection shutdown complete.")


if __name__ == "__main__":
    raise SystemExit(main())
