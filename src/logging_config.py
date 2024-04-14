import logging
import os
from logging import Logger, FileHandler, Formatter

class TypeLogger():
    """
    TypeLogger class

    This class creates a logger for a specific level, and saves logger output
    in a log file in a log director using a simplified format based on the
    idea that log levels are stored as different files. The initialized
    instance calls the log method by default.

    Attributes:
        name (str): The name of the logger.
        logger (Logger): The logger object.
        file_handler (FileHandler): The file handler object.
        formatter (Formatter): The formatter object.
    
    Methods:
        __init__(self, name: str) -> None: Initializes the TypeLogger object.
        __call__(self, message: str) -> None: Calls the log method.
        _get_logger(self, name: str) -> Logger: Returns a logger object.
        _get_log_level(self) -> int: Returns the log level.
        _get_file_handler(self, name: str) -> FileHandler: Returns a file
            handler object.
        _get_formatter(self) -> Formatter: Returns a formatter object.
        _setup_logger(self) -> None: Sets up the logger.
        log(self, message) -> None: Logs a message using the logger.

    Example:
        >>>info_logger = TypeLogger("info")
        >>>info_logger("Info logger initialized")

        >cat info.log

        Output:
        2024-04-13 23:33:39,228 - Info logger initialized
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = self._get_logger(name)
        self.file_handler = self._get_file_handler(name)
        self.formatter = self._get_formatter()
        self._setup_logger()
    
    def __call__(self, message: str) -> None:
        self.log(message)

    def _get_logger(self, name: str) -> Logger:
        logger_name: str = f"{name}_logger"
        logger: Logger = logging.getLogger(logger_name)
        log_level: int = self._get_log_level(name)
        logger.setLevel(log_level)
        return logger
    
    def _get_log_level(self) -> int:

        name: str = self.name.upper()
        try:
            log_level = getattr(logging, name)
        except AttributeError:
            raise ValueError(f"Invalid log level name: {name}")
        return log_level
        
    def _get_file_handler(self, name: str) -> FileHandler:
        filename: str = f"{name}.log"
        file_path = os.path.join("logs", filename)
        return logging.FileHandler(file_path)

    def _get_formatter(self) -> Formatter:
        return logging.Formatter(
            "%(asctime)s - %(message)s"
        )

    def _setup_logger(self) -> None:
        self.logger.addHandler(self.file_handler)
        self.file_handler.setFormatter(self.formatter)

    def log(self, message) -> None:
        """
        Log a message using the logger.

        Args:
            message (str): The message to be logged.

        Returns:
            None

        Example:
            logger = Logger("my_logger")
            logger.log("This is a log message")
        """
        self.logger.log(self.logger.level, message)


def start_loggers():
    error_logger = Logger("error")
    info_logger = Logger("info")
    
    return error_logger, info_logger