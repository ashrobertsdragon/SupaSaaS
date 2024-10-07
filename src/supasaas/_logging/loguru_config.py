"""Optional loguru configuration for SupaSaaS including predefined handlers"""

import sys

from loguru import logger

from .. import set_logger

set_logger(logger)


def stdout_logger() -> None:
    "Set up loguru logger with stdout"

    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<c><i>{time}</i></c <level>{message}</level>",
        diagnose=True,
    )


def file_logger() -> None:
    "Set up loguru logger with file"

    logger.remove()
    logger.add(
        "supasaas.log",
        rotation="1 KB",
        colorize=False,
        format="{time:MM/DD HH:mm:ss.ss} - {level} - {message}",
        diagnose=True,
    )


def gcloud_logger() -> None:
    "Set up loguru logger with Google Cloud Logging"
    _GCP_LOG_FORMAT = (
        "{level:<.1}{time:MM/DD HH:mm:ss.SSSSSS}"
        "{process} {name}:{line}] {message} | {extra}"
    )

    logger.remove()
    logger.add(
        sys.stdout, format=_GCP_LOG_FORMAT, colorize=True, diagnose=False
    )
