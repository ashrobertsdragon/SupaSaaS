import pytest
from gotrue.errors import AuthInvalidCredentialsError, AuthSessionMissingError

from supasaas.supabase_auth import (
    SupabaseAuth,
    default_logger,
    default_validator,
)


@pytest.fixture
def mock_client(mocker):
    mock_client = mocker.Mock()
    mock_client.default_client = mocker.Mock()

    mock_client.select_client.return_value = mock_client.default_client
    return mock_client


@pytest.fixture
def auth_with_mocks(mocker, mock_client):
    logger = mocker.Mock()
    validator = mocker.Mock()

    return SupabaseAuth(mock_client, validator, logger)


def test_supabase_auth_init(mocker, mock_client):
    auth = SupabaseAuth(mock_client)

    assert auth.client == mock_client.default_client

    assert auth.validate_response == default_validator
    assert auth.log == default_logger


def test_supabase_auth_init_with_validator(mocker, mock_client):
    validator = mocker.Mock()
    auth = SupabaseAuth(mock_client, validator)

    assert auth.client == mock_client.default_client
    assert auth.validate_response == validator
    assert auth.log == default_logger


def test_supabase_auth_init_with_logger(mocker, mock_client):
    logger = mocker.Mock()
    auth = SupabaseAuth(mock_client, log_function=logger)

    assert auth.client == mock_client.default_client
    assert auth.validate_response == default_validator
    assert auth.log == logger


def test_supabase_auth_sign_up(mocker, auth_with_mocks):
    email = "example@email.com"
    password = "password123"
    mock_response = {
        "email": email,
        "id": "123",
        "name": "John Doe",
        "created_at": "2022-01-01T00:00:00.000Z",
    }
    auth_with_mocks.client.auth.sign_up.return_value = mock_response
    auth_with_mocks.sign_up(email=email, password=password)

    auth_with_mocks.client.auth.sign_up.assert_called_with({
        "email": email,
        "password": password,
    })
    auth_with_mocks.validate_response.assert_called_with(
        mock_response, expected_type="tuple"
    )
    auth_with_mocks.log.assert_not_called()


def test_supabase_auth_sign_up_error(mocker, auth_with_mocks):
    email = "example@email.com"
    password = "password123"
    error = AuthInvalidCredentialsError(
        "You must provide either an email or phone number and a password"
    )
    auth_with_mocks.client.auth.sign_up.side_effect = error
    with pytest.raises(AuthInvalidCredentialsError):
        auth_with_mocks.sign_up(email=email, password=password)
        auth_with_mocks.log.assert_called_with(
            level="error", action="signup", email=email, exception=error
        )


def test_supabase_auth_sign_in(mocker, auth_with_mocks):
    email = "example@email.com"
    password = "password123"

    auth_with_mocks.sign_in(email=email, password=password)

    auth_with_mocks.client.auth.sign_in_with_password.assert_called_with({
        "email": email,
        "password": password,
    })
    auth_with_mocks.log.assert_not_called()


def test_supabase_auth_sign_in_error(mocker, auth_with_mocks):
    email = "example@email.com"
    password = "password123"

    error = AuthInvalidCredentialsError(
        "You must provide either an email or phone number and a password"
    )
    auth_with_mocks.client.auth.sign_in_with_password.side_effect = error

    auth_with_mocks.sign_in(email=email, password=password)

    auth_with_mocks.log.assert_called_with(
        level="error", action="login", email=email, exception=error
    )


def test_supabase_auth_sign_out(mocker, auth_with_mocks):
    auth_with_mocks.sign_out()
    auth_with_mocks.client.auth.sign_out.assert_called_once()


def test_supabase_reset_password(mocker, auth_with_mocks):
    email = "example@email.com"
    domain = "example.com"

    auth_with_mocks.reset_password(email=email, domain=domain)

    auth_with_mocks.client.auth.reset_password_email.assert_called_with(
        email, options={"redirect_to": f"{domain}/reset-password.html"}
    )
    auth_with_mocks.log.assert_not_called()


def test_supabase_update_user(mocker, auth_with_mocks):
    updates = {"name": "John", "age": 30}
    auth_with_mocks.update_user(updates=updates)
    auth_with_mocks.client.auth.update_user.assert_called_with(updates)
    auth_with_mocks.log.assert_not_called()


def test_supabase_update_user_error(mocker, auth_with_mocks):
    updates = {"name": "John", "age": 30}
    error = AuthSessionMissingError()
    auth_with_mocks.client.auth.update_user.side_effect = error
    with pytest.raises(AuthSessionMissingError):
        auth_with_mocks.update_user(updates=updates)
        auth_with_mocks.log.assert_called_with(
            level="error",
            action="update_user",
            updates=updates,
            exception=error,
        )
