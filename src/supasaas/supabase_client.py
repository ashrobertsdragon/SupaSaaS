from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias

from decouple import UndefinedValueError, config
from pydantic import BaseModel
from supabase import Client, create_client
from supabase._sync.client import SupabaseException

from ._logging.supabase_logger import supabase_logger as default_logger

LogFunction: TypeAlias = Callable[[str, str, bool, Any, Any], None]


class ServiceRoleNoteSet(Exception):
    """Exception raised when a service role note is set."""

    pass


class SupabaseLogin(BaseModel):
    """Supabase login details. Service role is optional."""

    url: str
    key: str
    service_role: str | None = None
    log_function: LogFunction = default_logger

    def __post_init__(self):
        self.log(
            level="info",
            action=f"Supabase url {',' if self.service_role else 'and'} key "
            f"{', and service role key' if self.service_role else ''}"
            " initialized",
        )

    @classmethod
    def from_config(cls):
        """Creates a SupabaseLogin object from environment variables."""
        url: str = config("SUPABASE_URL")
        key: str = config("SUPABASE_KEY")
        try:
            service_role: str = config("SUPABASE_SERVICE_ROLE")
        except (KeyError, UndefinedValueError):
            service_role = None
        return cls(
            url=url,
            key=key,
            service_role=service_role,
        )


class SupabaseClient:
    """Supabase client."""

    def __init__(
        self,
        supabase_login: SupabaseLogin,
        log_function: LogFunction = default_logger,
    ):
        """
        Initializes a Supabase client.

        Args:
            supabase_login (SupabaseLogin): The Supabase login details.
            log_function (LogFunction, optional): The log function to use.
                Defaults to default_logger.
        """
        self.login = supabase_login
        self.log = log_function
        self.default_client: Client = self._initialize_client(
            self.login.url, self.login.key
        )
        self.log(level="info", action="Default client initialized")
        self.service_client: Client | None = None
        if self.login.service_role:
            self.service_client: Client = self._initialize_client(
                url=self.login.url, key=self.login.service_role
            )
            self.log(level="info", action="Service role client initialized")

    def _initialize_client(self, url: str, key: str) -> Client:
        """
        Initializes a Supabase client.

        Args:
            url (str): The URL of the Supabase instance.
            key (str): The API key of the Supabase instance.

        Returns:
            Client: The initialized Supabase client.

        Raises:
            SupabaseException: If an error occurs during the client
                initialization.
        """
        try:
            return create_client(supabase_url=url, supabase_key=key)
        except SupabaseException as e:
            self.log(
                level="error",
                action="initialize client",
                exception=e,
            )

    def select_client(self, use_service_role: bool = False) -> Client:
        """
        Selects the appropriate Supabase client based on the use_service_role
        parameter.

        Args:
            use_service_role (bool, optional): Determines whether to use the
                service role client or the default client. Defaults to False.

        Returns:
            Client: The appropriate Supabase client.

        Raises:
            ServiceRoleNoteSet: If service_client is None and use_service_role
                is True.
        Notes:
            Service role client should only be used for operations where a new
                user row is being inserted. Otherwise use default client for
                RLS policy on authenticated user.
        """
        if not self.service_client and use_service_role:
            raise ServiceRoleNoteSet("No service role key provided.")
        return self.service_client if use_service_role else self.default_client
