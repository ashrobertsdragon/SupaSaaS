import pytest
from postgrest import SyncPostgrestClient

from supasaas.supasaas import (
    PostgrestAPIError,
    SupabaseDB,
    default_logger,
    default_validator,
)


@pytest.fixture
def mock_client(mocker):
    mock_client = mocker.Mock()
    mock_client.default_client = mocker.Mock()
    mock_client.service_client = mocker.Mock()

    def select_client_side_effect(use_service_role: bool = False):
        return (
            mock_client.service_client
            if use_service_role
            else mock_client.default_client
        )

    mock_client.select_client.side_effect = select_client_side_effect

    return mock_client


@pytest.fixture
def mock_validator(mocker):
    return mocker.Mock(return_value=None)


@pytest.fixture
def mock_logger(mocker):
    return mocker.Mock()


def test_supabase_db(mocker, mock_client):
    db = SupabaseDB(mock_client)

    assert db.client == mock_client
    assert db.validator == default_validator
    assert db.log == default_logger
    assert db.empty_value == [{}]


def test_supabase_db_init_with_validator(mocker, mock_client):
    mock_validator = mocker.Mock()

    db = SupabaseDB(mock_client, mock_validator)

    assert db.client == mock_client
    assert db.validator == mock_validator
    assert db.log == default_logger


def test_supabase_db_init_with_logger(mocker, mock_client):
    mock_logger = mocker.Mock()

    db = SupabaseDB(mock_client, log_function=mock_logger)

    assert db.client == mock_client
    assert db.validator == default_validator
    assert db.log == mock_logger


def test_supabase_db_get_client(mocker, mock_client):
    db = SupabaseDB(mock_client)

    assert db._get_client(use_service_role=False) == mock_client.default_client
    assert db._get_client(use_service_role=True) == mock_client.service_client


def test_execute_query(mocker, mock_client):
    db = SupabaseDB(mock_client)
    db_client = mock_client.default_client
    table_name = "test_table"

    mock_query = mocker.MagicMock(return_value=mocker.Mock())
    mock_query.return_value.execute.return_value = "success"

    mock_postgrest = mocker.Mock(spec=SyncPostgrestClient)
    db_client.postgrest = mock_postgrest
    mock_postgrest.__enter__ = mocker.Mock(return_value=mock_postgrest)
    mock_postgrest.__exit__ = mocker.Mock()

    mock_from_result = mocker.Mock()
    mock_postgrest.from_.return_value = mock_from_result

    result = db._execute_query(
        db_client=db_client, table_name=table_name, query=mock_query
    )
    assert result == "success"

    mock_postgrest.from_.assert_called_once_with(table_name)
    mock_query.assert_called_once_with(mock_from_result)
    mock_query.return_value.execute.assert_called_once()


def test_validate_response(mocker, mock_client, mock_validator):
    db = SupabaseDB(mock_client, mock_validator)
    data = [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]
    action = "test_action"
    table_name = "test_table"

    assert db._validate_response(data, action=action, table_name=table_name)
    mock_validator.has_calls([
        mocker.call(data, list),
        mocker.call(data[0], dict),
        mocker.call(data[1], dict),
    ])


def test_validate_response_list_type_error(mocker, mock_client, mock_logger):
    error = TypeError("Response must be a list")
    mock_validator = mocker.Mock(side_effect=error)
    action = "test_action"
    table_name = "test_table"
    data = {"id": 1, "name": "John"}
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    assert not db._validate_response(
        data, action=action, table_name=table_name
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="test_action",
        table_name="test_table",
        data=data,
        exception=error,
    )


def test_validate_response_dict_type_error(mocker, mock_client, mock_logger):
    error = ValueError("Response must be a dict")
    mock_validator = mocker.Mock(side_effect=[None, error])
    action = "test_action"
    table_name = "test_table"
    data = ["id", 1, "name", "John"]
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    assert not db._validate_response(
        data, action=action, table_name=table_name
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="test_action",
        table_name="test_table",
        data=data,
        exception=error,
    )


def test_validate_response_value_error(mocker, mock_client, mock_logger):
    error = ValueError("Response must not be empty")
    mock_validator = mocker.Mock(side_effect=error)
    action = "test_action"
    table_name = "test_table"
    data = []
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    assert not db._validate_response(
        data, action=action, table_name=table_name
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="test_action",
        table_name="test_table",
        data=data,
        exception=error,
    )

    mock_validator.assert_called_once_with(data, list)


def test_get_filter(mocker, mock_client, mock_validator):
    db = SupabaseDB(mock_client, mock_validator)
    match = {"id": 1}

    assert db._get_filter(
        match=match,
        expected_value_type=int,
        action="select",
        table_name="test_table",
    )
    mock_validator.has_calls([
        mocker.call(match, dict),
        mocker.call("id", str),
        mocker.call(match["id"], int),
    ])


def test_get_filter_not_dict(mocker, mock_client, mock_logger):
    error = TypeError("Match must be a dict")
    mock_validator = mocker.Mock(side_effect=error)
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    match = 1

    with pytest.raises(TypeError):
        db._get_filter(
            match=match,
            expected_value_type=int,
            action="select",
            table_name="test_table",
        )
    mock_logger.assert_called_once_with(
        level="error",
        exception=error,
        action="select",
        match=match,
        table_name="test_table",
    )


def test_get_filter_too_many_keys(
    mocker, mock_client, mock_logger, mock_validator
):
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    match = {"id": 1, "name": "John"}

    with pytest.raises(ValueError):
        db._get_filter(
            match=match,
            expected_value_type=int,
            action="select",
            table_name="test_table",
        )
    mock_logger.assert_called_once_with(
        level="error",
        exception=mocker.ANY,
        action="select",
        match=match,
        table_name="test_table",
    )


def tes_get_filter_key_not_str(mocker, mock_client, mock_logger):
    error = TypeError("Key must be a string")
    mock_validator = mocker.Mock(side_effect=[None, error])
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    match = {1: "id"}

    with pytest.raises(TypeError):
        db._get_filter(
            match=match,
            expected_value_type=int,
            action="select",
            table_name="test_table",
        )
    mock_logger.assert_called_once_with(
        level="error",
        exception=error,
        action="select",
        match=match,
        table_name="test_table",
    )


def test_get_filter_value_wrong_type(mocker, mock_client, mock_logger):
    mock_validator = mocker.Mock(
        side_effect=[None, None, TypeError("Value must be of type int")]
    )
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    match = {"id": "1"}

    with pytest.raises(TypeError) as exc_info:
        db._get_filter(
            match=match,
            expected_value_type=int,
            action="select",
            table_name="test_table",
        )
    assert str(exc_info.value) == "Value for filter 'id' must be a int"
    mock_logger.assert_called_once_with(
        level="error",
        exception=mocker.ANY,
        action="select",
        match=match,
        table_name="test_table",
    )


def test_insert_row(mocker, mock_client):
    db = SupabaseDB(mock_client)
    row = {"id": 1, "name": "John"}
    mock_execute = mocker.Mock(return_value={"data": [row], "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    assert db.insert_row(table_name="test_table", data=row)

    mock_execute.assert_called_once()
    call_args = mock_execute.call_args[1]
    assert call_args["db_client"] == mock_client.default_client
    assert call_args["table_name"] == "test_table"
    mock_table = mocker.Mock()
    call_args["query"](mock_table)
    mock_table.insert.assert_called_once_with(row)


def test_insert_row_uses_correct_client(mocker, mock_client):
    row = {"id": 1, "name": "John"}
    mock_execute = mocker.Mock(return_value={"data": [row], "count": 1})
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)

    db = SupabaseDB(mock_client)
    db.insert_row(table_name="test_table", data=row, use_service_role=True)

    assert mock_execute.call_args[1]["db_client"] == mock_client.service_client


def test_insert_row_raises_error_for_empty_response(
    mocker, mock_client, mock_logger
):
    mock_execute = mocker.Mock(return_value={"data": [], "count": 0})
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    row = {"id": 1, "name": "John"}

    assert not db.insert_row(table_name="test_table", data=row)

    mock_logger.assert_called_once_with(
        level="error",
        action="insert",
        data=row,
        table_name="test_table",
        exception=mocker.ANY,
    )

    error = mock_logger.call_args[1]["exception"]
    assert error.message == "Failed to insert row into test_table"


def test_insert_row_catches_exception_from_supabase(
    mocker, mock_client, mock_logger
):
    error = PostgrestAPIError({"message": "test error"})
    mock_execute = mocker.Mock(side_effect=error)
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, mock_validator, mock_logger)
    row = {"id": 1, "name": "John"}

    assert not db.insert_row(table_name="test_table", data=row)

    mock_logger.assert_called_once_with(
        level="error",
        action="insert",
        data=row,
        table_name="test_table",
        exception=error,
    )


def test_delete_row(mocker, mock_client):
    db = SupabaseDB(mock_client)
    match = {"id": 1}
    row = {"id": 1, "name": "John"}
    mock_execute = mocker.Mock(return_value={"data": [row], "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    assert db.delete_row(table_name="test_table", match=match, match_type=int)

    mock_execute.assert_called_once()
    call_args = mock_execute.call_args[1]
    assert call_args["db_client"] == mock_client.default_client
    assert call_args["table_name"] == "test_table"
    mock_table = mocker.Mock()
    call_args["query"](mock_table)
    mock_table.delete.eq.assert_called_once_with("id", 1)


def test_delete_row_uses_correct_client(mocker, mock_client):
    db = SupabaseDB(mock_client)
    match = {"id": 1}
    row = {"id": 1, "name": "John"}
    mock_execute = mocker.Mock(return_value={"data": [row], "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    db.delete_row(table_name="test_table", match=match, match_type=int)

    assert mock_execute.call_args[1]["db_client"] == mock_client.default_client


def test_delete_row_catches_exception_from_supabase(
    mocker, mock_client, mock_logger
):
    error = PostgrestAPIError({"message": "test error"})
    mock_execute = mocker.Mock(side_effect=error)
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    assert not db.delete_row(
        table_name="test_table", match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        table_name="test_table",
        exception=error,
        action="delete",
        match=match,
    )


def test_delete_row_catches_value_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=ValueError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)

    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    assert not db.delete_row(
        table_name="test_table", match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        table_name="test_table",
        exception=mocker.ANY,
        action="delete",
        match=match,
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, ValueError)
    mock_execute.assert_not_called()


def test_delete_row_catches_type_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=TypeError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)

    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    assert not db.delete_row(
        table_name="test_table", match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        table_name="test_table",
        exception=mocker.ANY,
        action="delete",
        match=match,
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, TypeError)
    mock_execute.assert_not_called()


def test_select_row(mocker, mock_client):
    db = SupabaseDB(mock_client)
    match = {"id": 1}
    row = [{"id": 1, "name": "John"}]
    mock_execute = mocker.Mock(return_value={"data": row, "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    result = db.select_row(
        table_name="test_table", match=match, match_type=int
    )

    assert result == row
    call_args = mock_execute.call_args[1]
    assert call_args["db_client"] == mock_client.service_client
    assert call_args["table_name"] == "test_table"
    mock_table = mocker.Mock()
    call_args["query"](mock_table)
    mock_table.select.assert_called_once_with("*")
    mock_table.select().eq.assert_called_once_with("id", 1)


def test_select_row_accepts_custom_columns(
    mocker, mock_client, mock_validator
):
    db = SupabaseDB(mock_client, mock_validator)
    match = {"id": 1}
    row = [{"name": "John", "age": 30}]
    columns = ["name", "age"]
    mock_execute = mocker.Mock(return_value={"data": row, "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    result = db.select_row(
        table_name="test_table", match=match, match_type=int, columns=columns
    )

    assert result == row
    mock_table = mocker.Mock()
    mock_execute.call_args[1]["query"](mock_table)
    mock_table.select.assert_called_once_with("name, age")


def test_select_row_catches_exception_from_supabase(
    mocker, mock_client, mock_logger
):
    error = PostgrestAPIError({"message": "test error"})
    mock_execute = mocker.Mock(side_effect=error)
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    result = db.select_row(
        table_name="test_table", match=match, match_type=int
    )

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        exception=error,
        action="select",
        table_name="test_table",
        column_str="*",
        match=match,
    )


def test_select_row_catches_value_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=ValueError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)

    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    result = db.select_row(
        table_name="test_table", match=match, match_type=int
    )

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        exception=mocker.ANY,
        action="select",
        table_name="test_table",
        column_str="*",
        match=match,
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, ValueError)
    mock_execute.assert_not_called()


def test_select_row_catches_type_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=TypeError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)

    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}

    result = db.select_row(
        table_name="test_table", match=match, match_type=int
    )

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        exception=mocker.ANY,
        action="select",
        table_name="test_table",
        column_str="*",
        match=match,
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, TypeError)
    mock_execute.assert_not_called()


def test_update_row(mocker, mock_client):
    db = SupabaseDB(mock_client)
    match = {"id": 1}
    info = {"name": "John"}
    row = [{"id": 1, "name": "John"}]
    mock_execute = mocker.Mock(return_value={"data": row, "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    assert db.update_row(
        table_name="test_table", info=info, match=match, match_type=int
    )

    call_args = mock_execute.call_args[1]
    assert call_args["db_client"] == mock_client.default_client
    assert call_args["table_name"] == "test_table"
    mock_table = mocker.Mock()
    call_args["query"](mock_table)
    mock_table.update.assert_called_once_with({"name": "John"})
    mock_table.update().eq.assert_called_once_with("id", 1)


def test_update_row_catches_exception_from_supabase(
    mocker, mock_client, mock_logger
):
    error = PostgrestAPIError({"message": "test error"})
    mock_execute = mocker.Mock(side_effect=error)
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, log_function=mock_logger)
    match = {"id": 1}
    info = {"name": "John"}

    assert not db.update_row(
        table_name="test_table", info=info, match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="update",
        info=info,
        match=match,
        exception=error,
        table_name="test_table",
    )


def test_update_row_catches_value_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=ValueError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    match = {"id": 1}
    info = {"name": "John"}

    db = SupabaseDB(mock_client, log_function=mock_logger)
    assert not db.update_row(
        table_name="test_table", info=info, match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="update",
        info=info,
        match=match,
        exception=mocker.ANY,
        table_name="test_table",
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, ValueError)
    mock_execute.assert_not_called()


def test_update_row_catches_type_error_from_get_filter(
    mocker, mock_client, mock_logger
):
    mock_get_filter = mocker.Mock(side_effect=TypeError)
    mocker.patch.object(SupabaseDB, "_get_filter", mock_get_filter)
    mock_execute = mocker.Mock()
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    match = {"id": 1}
    info = {"name": "John"}
    db = SupabaseDB(mock_client, log_function=mock_logger)
    assert not db.update_row(
        table_name="test_table", info=info, match=match, match_type=int
    )

    mock_logger.assert_called_once_with(
        level="error",
        action="update",
        info=info,
        match=match,
        exception=mocker.ANY,
        table_name="test_table",
    )

    error = mock_logger.call_args[1]["exception"]
    assert isinstance(error, TypeError)
    mock_execute.assert_not_called()


def test_find_row(mocker, mock_client):
    db = SupabaseDB(mock_client)
    table_name = "test_table"
    match_column = "date"
    within_period = 1
    row = [{"id": 1, "date": "2024-09-30"}]
    mock_execute = mocker.Mock(return_value={"data": row, "count": 1})
    mocker.patch.object(db, "_execute_query", mock_execute)

    result = db.find_row(
        table_name=table_name,
        match_column=match_column,
        within_period=within_period,
    )

    assert result == row
    call_args = mock_execute.call_args[1]
    assert call_args["db_client"] == mock_client.default_client
    assert call_args["table_name"] == table_name
    mock_table = mocker.Mock()
    call_args["query"](mock_table)
    mock_table.select.assert_called_once_with(["*"])
    mock_table.select().lte.assert_called_once_with(
        match_column, within_period
    )


def find_row_accepts_custom_column(mocker, mock_client):
    db = SupabaseDB(mock_client)
    table_name = "test_table"
    match_column = "age"
    within_period = 30
    rows = [
        {"id": 1, "name": "John", "age": 30},
        {"id": 5, "name": "Jane", "age": 25},
    ]
    mock_execute = mocker.Mock(return_value={"data": rows, "count": 2})
    mocker.patch.object(db, "_execute_query", mock_execute)

    db.find_row(
        table_name=table_name,
        match_column=match_column,
        within_period=within_period,
        columns=["id", "name", "age"],
    )

    assert mock_execute.call_args[1]["columns"] == ["id", "name", "age"]


def test_find_row_catches_exception_from_supabase(
    mocker, mock_client, mock_logger
):
    error = PostgrestAPIError({"message": "test error"})
    mock_execute = mocker.Mock(side_effect=error)
    mocker.patch.object(SupabaseDB, "_execute_query", mock_execute)
    db = SupabaseDB(mock_client, log_function=mock_logger)
    match_column = "date"
    within_period = 1
    table_name = "test_table"

    result = db.find_row(
        table_name=table_name,
        match_column=match_column,
        within_period=within_period,
    )

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        exception=error,
        action="find row",
        table_name=table_name,
        match_column=match_column,
        within_period=within_period,
        columns=["*"],
    )
