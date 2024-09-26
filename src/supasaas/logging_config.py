import sys

from loguru import logger

from . import set_logger

set_logger(logger)


def stdout_logger() -> None:
    "Set up loguru logger with stdout"
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time}</green> <level>{message}</level>",
    )


def gcloud_logger() -> None:
    "Set up loguru logger with Google Cloud Logging"
    _GCP_LOG_FORMAT = (
        "{level:<.1}{time:MM/DD HH:mm:ss.SSSSSS}"
        "{process} {name}:{line}] {message} | {extra}"
    )

    logger.remove()
    logger.add(
        sys.stdout,
        format=_GCP_LOG_FORMAT,
        colorize=True,
    )
