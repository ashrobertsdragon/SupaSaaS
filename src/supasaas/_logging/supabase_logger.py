"""Default logging parser for SupaSaaS APIs"""

from supasaas._logging import logger


def format_args(args: list | None) -> str:
    "Create comma delimited string of arguments passed to logger"
    return ", ".join(args) if args else ""


def format_kwargs(kwargs: dict) -> str:
    "Create a comma delimited string of keyword arguments passed to logger"
    kwarg_list = [
        f"{key}={'text' if key == 'file_content' else value}"
        for key, value in kwargs.items()
        if key != "exception"
    ]
    return ", ".join(kwarg_list)


def construct_message(
    action: str,
    arg_str: str,
    kwarg_str: str,
    is_error: bool,
    exception: Exception | None = None,
) -> str:
    """
    Formats the log message body

    Args:
        action (str): The action performed.
        arg_str (str): The logger's args parsed into a string.
        kwarg_str (str): The logger's kwargs parsed into a string.
        is_error (bool): Whether or not the log message is for an Exception.
        exception (Exception | None): The exception being logged if there is
            one, defaults to None.

    Returns:
        str: The log message body formatted as a string.
    """
    prefix: str = "Error performing " if is_error else ""
    if arg_str or kwarg_str:
        connector: str = "with " if is_error else " returned "
    else:
        connector = ""
    exc_str = f"\nException: {exception}" if exception else ""
    return f"{prefix}{action}{connector}{arg_str}{kwarg_str}{exc_str}"


def supabase_logger(level: str, action: str, *args, **kwargs) -> None:
    """
    Log actions from Supabase

    Args:
        level (str): The log level.
        action (str): The action being logged.
        *args (Any): Any additional arguments passed to the logger.
        **kwargs (Any): Any additional keywords arguments passed to the logger.
    """
    arg_str = format_args(args)
    kwarg_str = format_kwargs(kwargs)
    exception = kwargs.get("exception", None)

    is_error: bool = level in {"error", "exception"}

    log_message = construct_message(
        action, arg_str, kwarg_str, is_error, exception
    )
    getattr(logger, level)(log_message)
