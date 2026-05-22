"""Application-wide structured logging."""

import logging
import os
from typing import Any


class AppLogger:
    """Wraps Python logging with consistent contextual formatting."""

    def __init__(self, name: str = 'documents'):
        self._logger = logging.getLogger(name)
        self._level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self._logger.setLevel(getattr(logging, self._level, logging.INFO))

    def _format_message(self, message: str, extra: dict[str, Any] | None = None) -> str:
        if not extra:
            return message
        context = ' | '.join(f'{key}={value}' for key, value in extra.items())
        return f'{message} | {context}'

    def debug(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._logger.debug(self._format_message(message, extra))

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._logger.info(self._format_message(message, extra))

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._logger.warning(self._format_message(message, extra))

    def error(self, message: str, extra: dict[str, Any] | None = None, exc_info: bool = False) -> None:
        self._logger.error(self._format_message(message, extra), exc_info=exc_info)

    def critical(self, message: str, extra: dict[str, Any] | None = None, exc_info: bool = False) -> None:
        self._logger.critical(self._format_message(message, extra), exc_info=exc_info)


def get_logger(name: str = 'documents') -> AppLogger:
    return AppLogger(name)
