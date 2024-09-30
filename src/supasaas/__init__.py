from typing import Any

from ._logging import LoggerProxy
from .supabase_auth import SupabaseAuth
from .supabase_client import SupabaseClient, SupabaseLogin
from .supabase_db import SupabaseDB
from .supabase_storage import SupabaseStorage

__all__ = [
    "SupabaseClient",
    "SupabaseLogin",
    "SupabaseAuth",
    "SupabaseDB",
    "SupabaseStorage",
    "set_logger",
]

logger = LoggerProxy()


def set_logger(custom_logger: Any) -> None:
    """
    Set the logger for the entire library.

    Args:
        custom_logger: The logger object to be used throughout the library.
    """
    logger.set_logger(custom_logger)
