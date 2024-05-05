
import logging
from typing import Optional
from unittest.mock import patch

import pytest

from supasaas import SupabaseClient

@pytest.fixture(scope="module")
def client():
    # Initialize the client instance only once
    client = SupabaseClient()
    yield client

def test_get_env_value_valid_key(client):
    value = client._get_env_value("TEST_KEY")
    assert value == "TEST_VALUE"

def test_get_env_value_invalid_key(client):
    with pytest.raises(LookupError) as exc_info:
        client._get_env_value("INVALID_KEY")
    assert str(exc_info.value) == "Supabase API INVALID_KEY not found"

def test_get_env_value_non_string_key(client):
    with pytest.raises(TypeError) as exc_info:
        client._get_env_value(123)
    assert str(exc_info.value) == "123 must be string"

def test_log_info_with_args_and_kwargs(client):
    action = "test_action"
    args = ("arg1", "arg2")
    kwargs = {"key1": "value1", "key2": "value2"}

    with patch.object(logging, "info") as mock_info:
        client.log_info(action, *args, **kwargs)
        mock_info.assert_called_once_with(f"{action} returned arg1, arg2, key1=value1, key2=value2")

def test_log_info_with_only_args(client):
    action = "test_action"
    args = ("arg1", "arg2")

    with patch.object(logging, "info") as mock_info:
        client.log_info(action, *args)
        mock_info.assert_called_once_with(f"{action} returned arg1, arg2")

def test_log_info_with_only_kwargs(client):
    action = "test_action"
    kwargs = {"key1": "value1", "key2": "value2"}

    with patch.object(logging, "info") as mock_info:
        client.log_info(action, **kwargs)
        mock_info.assert_called_once_with(f"{action} returned key1=value1, key2=value2")

def test_log_info_without_args_or_kwargs(client):
    action = "test_action"

    with patch.object(logging, "info") as mock_info:
        client.log_info(action)
        mock_info.assert_called_once_with(f"{action} returned ")


def test_create_error_message_with_action_only(client):
    action = "test_action"
    expected_message = "Error performing test_action"
    result = client.create_error_message(action)
    assert result == expected_message

def test_create_error_message_with_action_and_kwargs(client):
    action = "test_action"
    kwargs = {
        "updates": {"name": "John"},
        "table_name": "users",
        "email": "john@example.com",
    }
    expected_message = "Error performing test_action with updates: {'name': 'John'} with table_name: users with email: john@example.com"
    result = client.create_error_message(action, **kwargs)
    assert result == expected_message

def test_create_error_message_with_empty_kwargs(client):
    action = "test_action"
    kwargs = {}
    expected_message = "Error performing test_action"
    result = client.create_error_message(action, **kwargs)
    assert result == expected_message

def test_create_error_message_with_falsy_values_in_kwargs(client):
    action = "test_action"
    kwargs = {
        "updates": None,
        "table_name": "",
        "email": 0,
    }
    expected_message = "Error performing test_action"
    result = client.create_error_message(action, **kwargs)
    assert result == expected_message

def test_log_error(client, caplog):
    action = "test_action"
    kwargs = {
        "updates": {"name": "John"},
        "table_name": "users",
        "email": "john@example.com",
    }
    exception = Exception("Something went wrong")

    with caplog.at_level(logging.ERROR):
        client.log_error(exception, action, **kwargs)

    error_message = client.create_error_message(action, **kwargs)
    error_message += "\nException: Something went wrong"

    assert len(caplog.records) == 1
    assert caplog.records[0].message == error_message

def test_log_error_with_no_kwargs(client, caplog):
    action = "test_action"
    exception = Exception("Something went wrong")

    with caplog.at_level(logging.ERROR):
        client.log_error(exception, action)

    error_message = client.create_error_message(action)
    error_message += "\nException: Something went wrong"

    assert len(caplog.records) == 1
    assert caplog.records[0].message == error_message

def test_validate_type_valid_value(client):
    client._validate_type(value=42, name="age", is_type=int, allow_none=False)
    # No exception raised, test passes

def test_validate_type_valid_value_with_none(client):
    client._validate_type(value=None, name="age", is_type=int, allow_none=True)
    # No exception raised, test passes

def test_validate_type_invalid_value_type(client):
    with pytest.raises(TypeError) as exc_info:
        client._validate_type(value="42", name="age", is_type=int, allow_none=False)
    assert str(exc_info.value) == "age must be int"

def test_validate_type_none_value_not_allowed(client):
    with pytest.raises(ValueError) as exc_info:
        client._validate_type(value=None, name="age", is_type=int, allow_none=False)
    assert str(exc_info.value) == "age must have value"

def test_validate_type_is_type_none(client):
    with pytest.raises(TypeError) as exc_info:
        client._validate_type(value=42, name="age", is_type=None, allow_none=False)
    assert str(exc_info.value) == "is_type must not be None"

def test_validate_dict_valid_dict(client):
    client._validate_dict(value={"key": "value"}, name="test_dict")
    # No exception raised, test passes

def test_validate_dict_invalid_type(client):
    with pytest.raises(TypeError) as exc_info:
        client._validate_dict(value=42, name="test_dict")
    assert str(exc_info.value) == "test_dict must be dict"

def test_validate_dict_none_value(client):
    with pytest.raises(ValueError) as exc_info:
        client._validate_dict(value=None, name="test_dict")
    assert str(exc_info.value) == "test_dict must have value"

def test_validate_list_valid_list(client):
    client._validate_list(value=["value1", "value2"], name="test_list")
    #No exception raised, test passes

def test_validate_list_invalid_list(client):
    with pytest.raises(TypeError) as exc_info:
        client._validate_list(value=42, name="test_list")
    assert str(exc_info.value) == "test_list must be list"

def test_validate_list_none_value(client):
    with pytest.raises(ValueError) as exc_info:
        client._validate_list(value=None, name="test_list")
    assert str(exc_info.value) == "test_list must have value"

def test_validate_string_valid_string(client):
    client._validate_string(value="value", name="test_string")
    #No exception raised, test passes

def test_validate_string_invalid_string(client):
    with pytest.raises(TypeError) as exc_info:
        client._validate_string(value=42, name="test_string")
    assert str(exc_info.value) == "test_string must be str"

def test_validate_string_none_value(client):
    with pytest.raises(ValueError) as exc_info:
        client._validate_string(value=None, name="test_string")
    assert str(exc_info.value) == "test_string must have value"

def test_collect_param_value_with_non_optional_param(client):
    result = client._collect_param_value(5, "param1", int)
    assert result == (5, "param1", int, False)

def test_collect_param_value_with_optional_param(client):
    result = client._collect_param_value(None, "param2", Optional[int])
    assert result == (None, "param2", int, True)

def test_collect_param_value_with_non_none_optional_param(client):
    result = client._collect_param_value(10, "param3", Optional[int])
    assert result == (10, "param3", int, True)

def test_collect_param_value_with_string_param(client):
    result = client._collect_param_value("hello", "param4", str)
    assert result == ("hello", "param4", str, False)

