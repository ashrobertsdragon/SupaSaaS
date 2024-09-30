import logging
from typing import Any, Callable


class LoggerProxy:
    def __init__(self):
        self._logger = None

    def set_logger(self, logger: Any) -> None:
        self._logger = logger

    def _add_basic_logger(self) -> None:
        logging.basicConfig()
        self._logger = logging.getLogger("supasaas")

    def __getattr__(self, name: str) -> Callable:
        if self._logger is None:
            self._add_basic_logger()
        return getattr(self._logger, name)
