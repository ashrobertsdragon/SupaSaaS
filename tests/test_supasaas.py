import pytest
from supabase._sync.client import SupabaseException

from supasaas.supabase_client import SupabaseClient, SupabaseLogin


@pytest.fixture
def supabase_login(mocker):
    mocker.patch(
        "supasaas.supabase_client.config",
        side_effect=lambda key: {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "example_key",
            "SUPABASE_SERVICE_ROLE": "example_service_role",
        }[key],
    )
    return SupabaseLogin.from_config()


def test_initializes_from_config(mocker):
    mocker.patch(
        "supasaas.supabase_client.config",
        side_effect=lambda key: {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "example_key",
            "SUPABASE_SERVICE_ROLE": "example_service_role",
        }[key],
    )

    login = SupabaseLogin.from_config()

    assert login.url == "https://example.supabase.co"
    assert login.key == "example_key"
    assert login.service_role == "example_service_role"


def test_initializes_without_service_role(mocker):
    mocker.patch(
        "supasaas.supabase_client.config",
        side_effect=lambda key: {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "example_key",
        }[key],
    )

    login = SupabaseLogin.from_config()

    assert login.url == "https://example.supabase.co"
    assert login.key == "example_key"
    assert login.service_role is None


def test_missing_supabase_url(mocker):
    mocker.patch(
        "supasaas.supabase_client.config",
        side_effect=lambda key: {
            "SUPABASE_KEY": "example_key",
            "SUPABASE_SERVICE_ROLE": "example_service_role",
        }[key],
    )

    with pytest.raises(KeyError):
        SupabaseLogin.from_config()


def test_supabase_client_valid(mocker, supabase_login):
    mock_initialize_client = mocker.patch.object(
        SupabaseClient, "_initialize_client"
    )
    client = SupabaseClient(supabase_login)
    assert mock_initialize_client.call_count == 2
    mock_initialize_client.assert_any_call(
        supabase_login.url, supabase_login.key
    )
    assert client.default_client == mock_initialize_client.return_value
    assert client.service_client == mock_initialize_client.return_value


def test_supabase_client_no_service_role(mocker):
    mocker.patch(
        "supasaas.supabase_client.config",
        side_effect=lambda key: {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "example_key",
        }[key],
    )
    login = SupabaseLogin.from_config()
    client = SupabaseClient(login)
    assert client.service_client == client.default_client


def test_supabase_client_accepts_custom_logger(mocker, supabase_login):
    def mock_logger(level: str, action: str, bool_arg: bool, *args, **kwargs):
        pass

    mocker.patch.object(SupabaseClient, "_initialize_client")
    client = SupabaseClient(supabase_login, mock_logger)

    assert client.log == mock_logger


def test_initialize_client(mocker, supabase_login):
    mock_create_client = mocker.patch("supasaas.supabase_client.create_client")

    client = SupabaseClient(supabase_login)

    mock_create_client.assert_has_calls([
        mocker.call(
            supabase_url=supabase_login.url, supabase_key=supabase_login.key
        ),
        mocker.call(
            supabase_url=supabase_login.url,
            supabase_key=supabase_login.service_role,
        ),
    ])
    assert client.default_client == mock_create_client.return_value
    assert client.service_client == mock_create_client.return_value


def test_initialize_client_error(mocker, supabase_login):
    mock_create_client = mocker.patch("supasaas.supabase_client.create_client")
    mock_logger = mocker.patch("supasaas.supabase_client.default_logger")
    error_obj = SupabaseException("Error")
    mock_create_client.side_effect = error_obj

    SupabaseClient(supabase_login, mock_logger)

    assert mock_create_client.call_count == 2
    mock_logger.assert_any_call(
        level="error", action="initialize client", exception=error_obj
    )


def test_select_client(mocker, supabase_login):
    mocker.patch("supasaas.supabase_client.create_client")
    client = SupabaseClient(supabase_login)

    assert client.select_client() == client.default_client
    assert client.select_client(use_service_role=True) == client.service_client
