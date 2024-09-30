from collections.abc import Callable
from typing import Any, TypeAlias

from gotrue._async.gotrue_client import (
    AuthInvalidCredentialsError,
    AuthSessionMissingError,
)
from gotrue.types import AuthResponse, UserResponse
from supabase import Client

from supasaas._logging.supabase_logger import supabase_logger as default_logger
from supasaas._validators import validate as default_validator
from supasaas.supabase_client import SupabaseClient

LogFunction: TypeAlias = Callable[[str, str, bool, Any, Any], None]
ValidatorFunction: TypeAlias = Callable[[Any, type, bool], None]


class SupabaseAuth:
    def __init__(
        self,
        client: SupabaseClient,
        validator: ValidatorFunction = default_validator,
        log_function: LogFunction = default_logger,
    ):
        self.client: Client = client.select_client()
        self.log = log_function
        self.validate_response = validator

    def sign_up(self, *, email: str, password: str) -> AuthResponse:
        """
        Signs up a user with the provided email and password.

        Args:
            email (str): The email of the user.
            password (str): The password of the user.

        Returns:
            AuthResponse: The response object containing the authentication
                information.

        Raises:
            AuthInvalidCredentialsError: If an error occurs during the sign up
                process.

        Example:
            sign_up(email="example@example.com", password="password123")
        """
        try:
            response: dict = self.client.auth.sign_up({
                "email": email,
                "password": password,
            })
            self.validate_response(response, expected_type="tuple")
            return response
        except AuthInvalidCredentialsError as e:
            self.log(level="error", action="signup", email=email, exception=e)
            raise

    def sign_in(self, *, email: str, password: str) -> AuthResponse:
        """
        Signs in a user with the provided email and password.

        Args:
            email (str): The email of the user.
            password (str): The password of the user.

        Returns:
            AuthResponse: The response object containing the authentication
                information.

        Raises:
            AuthInvalidCredentialsError: If an error occurs during the sign in
                process.

        Example:
            sign_in(email="example@example.com", password="password123")
        """
        try:
            return self.client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except AuthInvalidCredentialsError as e:
            self.log(level="error", action="login", email=email, exception=e)

    def sign_out(self) -> None:
        """
        Signs out the currently authenticated user.

        Raises:
            AuthInvalidCredentialsError: If an error occurs during the sign
                out process.

        Example:
            sign_out()
        """
        # Supabase library suppresses sign out errors
        self.client.auth.sign_out()

    def reset_password(self, *, email: str, domain: str) -> None:
        """
        Resets the password for a user with the provided email.

        Args:
            email (str): The email of the user.
            domain (str): The domain of the application.

        Raises:
            AuthInvalidCredentialsError: If an error occurs during the
                password reset process.

        Example:
            reset_password(email="example@example.com", domain="example.com")
        """
        # Supabase library does not raise any errors
        self.client.auth.reset_password_email(
            email, options={"redirect_to": f"{domain}/reset-password.html"}
        )

    def update_user(self, updates: dict) -> UserResponse:
        """
        Updates a user with the provided updates.

        Args:
            updates (dict): A dictionary containing the updates to be made to
                the user.

        Raises:
            AuthInvalidCredentialsError: If an error occurs during the update
                process.

        Example:
            update_user(updates={"name": "John", "age": 30})
        """
        try:
            return self.client.auth.update_user(updates)
        except AuthSessionMissingError as e:
            self.log(
                level="error",
                action="update user",
                updates=updates,
                exception=e,
            )
            raise
