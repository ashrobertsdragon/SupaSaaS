from collections.abc import Callable
from typing import Any, TypeAlias

from decouple import config
from pydantic import BaseModel
from supabase import Client, create_client
from supabase._sync.client import SupabaseException

from ._logging.supabase_logger import supabase_logger as default_logger

LogFunction: TypeAlias = Callable[[str, str, bool, Any, Any], None]


class SupabaseLogin(BaseModel):
    url: str
    key: str
    service_role: str

    @classmethod
    def from_config(cls):
        return cls(
            url=config("SUPABASE_URL"),
            key=config("SUPABASE_KEY"),
            service_role=config("SUPABASE_SERVICE_ROLE"),
        )


class SupabaseClient:
    def __init__(
        self,
        supabase_login: SupabaseLogin,
        log_function: LogFunction = default_logger,
    ):
        self.login = supabase_login
        self.log = log_function
        self.default_client: Client = self._initialize_client(
            self.login.url, self.login.key
        )
        self.service_client: Client = self._initialize_client(
            url=self.login.url, key=self.login.service_role
        )

    def _initialize_client(self, url: str, key: str) -> Client:
        try:
            return create_client(supabase_url=url, supabase_key=key)
        except SupabaseException as e:
            self.log(
                level="error",
                action="initialize client",
                exception=e,
            )

    def select_client(self, use_service_role: bool = False) -> Client:
        return self.service_client if use_service_role else self.default_client
