"""Safe MetaTrader 5 connection wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import MetaTrader5 as mt5

from config.settings import Settings
from utils.logger import setup_logger


class MT5Connection:
    """Manage MT5 terminal initialization and optional account login."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = setup_logger(__name__, settings.log_level)
        self._connected = False
        self.last_error: Any | None = None

    def initialize(self) -> bool:
        init_kwargs: dict[str, Any] = {}
        if self.settings.mt5_path:
            mt5_path = Path(self.settings.mt5_path).expanduser()
            self.logger.info("Using MT5_PATH: %s", mt5_path)
            if not mt5_path.exists():
                self.logger.error(
                    "MT5_PATH does not exist: %s. Set MT5_PATH to terminal64.exe, not a shortcut.",
                    mt5_path,
                )
                self._connected = False
                return False
            init_kwargs["path"] = str(mt5_path)
        else:
            self.logger.info("No MT5_PATH provided; using MetaTrader5 default terminal discovery.")

        if not mt5.initialize(**init_kwargs):
            initial_error = mt5.last_error()
            self._log_mt5_error("MT5 initialize failed")
            if self._is_authorization_failed(initial_error) and self._has_login_details():
                self.logger.info(
                    "Retrying MT5 initialize with explicit account credentials for login %s.",
                    self.settings.mt5_login,
                )
                credential_kwargs = {
                    **init_kwargs,
                    "login": self.settings.mt5_login,
                    "password": self.settings.mt5_password,
                    "server": self.settings.mt5_server,
                }
                if not mt5.initialize(**credential_kwargs):
                    self._log_mt5_error("MT5 initialize with credentials failed")
                    self._connected = False
                    return False
            else:
                self._connected = False
                return False

        self._connected = True
        self.logger.info("MT5 terminal initialized.")

        if self._has_login_details():
            login_ok = mt5.login(
                login=self.settings.mt5_login,
                password=self.settings.mt5_password,
                server=self.settings.mt5_server,
            )
            if not login_ok:
                self._log_mt5_error("MT5 login failed")
                self.shutdown()
                return False
            self.logger.info("MT5 login successful for account %s.", self.settings.mt5_login)
        else:
            self.logger.info("No MT5 credentials provided; using current terminal session.")

        return True

    def shutdown(self) -> None:
        if self._connected:
            mt5.shutdown()
            self.logger.info("MT5 terminal shutdown complete.")
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_account_info(self) -> dict[str, Any] | None:
        account_info = mt5.account_info()
        if account_info is None:
            self.logger.warning("MT5 account info unavailable: %s", mt5.last_error())
            return None
        return account_info._asdict()

    def get_terminal_info(self) -> dict[str, Any] | None:
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            self.logger.warning("MT5 terminal info unavailable: %s", mt5.last_error())
            return None
        return terminal_info._asdict()

    def get_last_error(self) -> Any | None:
        return self.last_error

    def _log_mt5_error(self, message: str) -> None:
        error = mt5.last_error()
        self.last_error = error
        self.logger.error("%s: %s", message, error)
        if self._is_ipc_timeout(error):
            self.logger.error(
                "MT5 IPC timeout hint: open MT5 manually first, confirm it is logged in, "
                "set MT5_PATH to terminal64.exe if needed, use the same Windows permission "
                "level for MT5 and Python, close duplicate terminals, then try again."
            )
        elif self._is_authorization_failed(error):
            self.logger.error(
                "MT5 authorization hint: confirm the MT5 terminal is logged in, or provide "
                "MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER in .env. Also confirm Python is "
                "connecting to the same terminal you use manually."
            )

    @staticmethod
    def _is_ipc_timeout(error: Any) -> bool:
        return isinstance(error, tuple) and len(error) > 0 and error[0] == -10005

    @staticmethod
    def _is_authorization_failed(error: Any) -> bool:
        return isinstance(error, tuple) and len(error) > 0 and error[0] == -6

    def _has_login_details(self) -> bool:
        return all([self.settings.mt5_login, self.settings.mt5_password, self.settings.mt5_server])
