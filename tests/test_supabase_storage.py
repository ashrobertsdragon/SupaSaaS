import pytest

from supasaas.supasaas import (
    StorageException,
    SupabaseStorage,
    default_logger,
    default_validator,
)


@pytest.fixture
def client_with_mocks(mocker):
    mock_client = mocker.Mock()
    mock_client.default_client = mocker.Mock()
    mock_client.select_client.return_value = mock_client.default_client

    return mock_client


@pytest.fixture
def mock_validator(mocker):
    return mocker.Mock(return_value=None)


@pytest.fixture
def mock_logger(mocker):
    return mocker.Mock()


def test_supabase_storage_init(mocker, client_with_mocks):
    storage = SupabaseStorage(client_with_mocks)

    assert storage.client == client_with_mocks.default_client
    assert storage.validator == default_validator
    assert storage.log == default_logger


def test_supabase_storage_init_with_validator(mocker, client_with_mocks):
    mock_validator = mocker.Mock()
    storage = SupabaseStorage(client_with_mocks, mock_validator)

    assert storage.client == client_with_mocks.default_client
    assert storage.validator == mock_validator
    assert storage.log == default_logger


def test_supabase_storage_init_with_logger(
    mocker, client_with_mocks, mock_logger
):
    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    assert storage.client == client_with_mocks.default_client
    assert storage.validator == default_validator
    assert storage.log == mock_logger


def test_use_storage_connection(mocker, client_with_mocks):
    storage = SupabaseStorage(client_with_mocks)
    bucket = "test_bucket"
    action = "mock_action"
    test_kwargs = {"test": "test"}

    mock_storage = mocker.Mock(name="mock.default_client.storage")
    storage.client.storage = mock_storage
    mock_storage.__enter__ = mocker.Mock(return_value=mock_storage)
    mock_storage.__exit__ = mocker.Mock()

    mock_from_result = mocker.Mock()
    mock_storage.from_.return_value = mock_from_result

    mock_action_method = mocker.Mock(return_value="success")
    setattr(mock_from_result, action, mock_action_method)

    result = storage._use_storage_connection(bucket, action, test="test")

    assert result == "success"
    mock_storage.from_.assert_called_once_with("test_bucket")
    mock_action_method.assert_called_once_with(**test_kwargs)


def test_validate_response(mocker, client_with_mocks, mock_validator):
    storage = SupabaseStorage(client_with_mocks, mock_validator)

    assert (
        storage._validate_response(
            "test",
            expected_type=str,
            action="test_action",
            bucket="test_bucket",
        )
        is True
    )


def test_validate_response_invalid_type(
    mocker, client_with_mocks, mock_logger
):
    error = TypeError("Response must be a list")
    mock_validator = mocker.Mock(side_effect=error)
    storage = SupabaseStorage(client_with_mocks, mock_validator, mock_logger)
    assert not storage._validate_response(
        "test", expected_type=list, action="test_action", bucket="test_bucket"
    )
    mock_logger.assert_called_once_with(
        level="error",
        action="test_action",
        bucket="test_bucket",
        exception=error,
    )


def test_validate_response_empty_response(
    mocker, client_with_mocks, mock_logger
):
    error = ValueError("Response must have a value")
    mock_validator = mocker.Mock(side_effect=error)

    storage = SupabaseStorage(client_with_mocks, mock_validator, mock_logger)
    assert not storage._validate_response(
        "", expected_type=list, action="test_action", bucket="test_bucket"
    )
    mock_logger.assert_called_once_with(
        level="error",
        action="test_action",
        bucket="test_bucket",
        exception=error,
    )


def test_upload_file(mocker, client_with_mocks):
    mock_connection = mocker.Mock()
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks)
    bucket = "test_bucket"
    path = "test_path"
    file_content = "test_content"
    file_mimetype = "test_file_mimetype"

    assert storage.upload_file(bucket, path, file_content, file_mimetype)

    mock_connection.assert_called_once_with(
        bucket,
        "upload",
        path=path,
        file=file_content,
        file_options={"content-type": file_mimetype},
    )


def test_upload_file_storage_exception(mocker, client_with_mocks, mock_logger):
    error = StorageException()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    path = "test_path"
    file_content = "test_content"
    file_mimetype = "test_file_mimetype"

    assert not storage.upload_file(bucket, path, file_content, file_mimetype)

    mock_logger.assert_called_once_with(
        level="error",
        action="upload file",
        bucket="test_bucket",
        upload_path="test_path",
        file_content="test_content",
        file_mimetype="test_file_mimetype",
        exception=error,
    )


def test_delete_file(mocker, client_with_mocks):
    mock_connection = mocker.Mock()
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks)
    bucket = "test_bucket"
    path = "test_path"

    assert storage.delete_file(bucket, path)

    mock_connection.assert_called_once_with(
        bucket,
        "remove",
        paths=[path],
    )


def test_delete_file_storage_exception(mocker, client_with_mocks, mock_logger):
    error = StorageException()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    path = "test_path"

    assert not storage.delete_file(bucket, path)

    mock_logger.assert_called_once_with(
        level="error",
        action="delete file",
        bucket="test_bucket",
        file_path="test_path",
        exception=error,
    )


def test_download_file(mocker, client_with_mocks):
    mock_connection = mocker.Mock()
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks)
    bucket = "test_bucket"
    download_path = "test_path"
    destination_path = mocker.MagicMock()

    assert storage.download_file(bucket, download_path, destination_path)

    mock_connection.assert_called_once_with(
        bucket,
        "download",
        path=download_path,
    )
    assert destination_path.open.call_count == 1


def test_download_file_storage_exception(
    mocker, client_with_mocks, mock_logger
):
    error = StorageException()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    download_path = "test_path"
    destination_path = mocker.MagicMock()

    assert not storage.download_file(bucket, download_path, destination_path)

    mock_logger.assert_called_once_with(
        level="error",
        action="download file",
        bucket="test_bucket",
        download_path="test_path",
        destination_path=destination_path,
        exception=error,
    )


def test_download_file_os_error(mocker, client_with_mocks, mock_logger):
    error = OSError()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    download_path = "test_path"
    destination_path = mocker.MagicMock()

    assert not storage.download_file(bucket, download_path, destination_path)

    mock_logger.assert_called_once_with(
        level="error",
        action="download file",
        bucket="test_bucket",
        download_path="test_path",
        destination_path=destination_path,
        exception=error,
    )


def test_list_files_in_folder(mocker, client_with_mocks, mock_validator):
    storage_list = ["file1", "file2", "file3"]
    mock_connection = mocker.Mock(return_value=storage_list)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks, mock_validator)
    bucket = "test_bucket"
    folder = "test_folder"

    assert storage.list_files(bucket, folder)

    mock_connection.assert_called_once_with(
        bucket,
        "list",
        path=folder,
    )

    mock_validator.assert_called_once_with(storage_list, list)


def test_list_files_no_folder(mocker, client_with_mocks, mock_validator):
    storage_list = ["file1", "file2", "file3"]
    mock_connection = mocker.Mock(return_value=storage_list)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks, mock_validator)
    bucket = "test_bucket"

    assert storage.list_files(bucket)

    mock_connection.assert_called_once_with(
        bucket,
        "list",
    )

    mock_validator.assert_called_once_with(storage_list, list)


def test_list_files_storage_exception(mocker, client_with_mocks, mock_logger):
    error = StorageException()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    folder = "test_folder"

    result = storage.list_files(bucket, folder)

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        action="list files",
        bucket="test_bucket",
        exception=error,
    )


def test_list_files_validator_exception(
    mocker, client_with_mocks, mock_logger
):
    error = ValueError()
    mock_validator = mocker.Mock(side_effect=error)
    mock_connection = mocker.Mock(return_value="")
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(
        client_with_mocks, mock_validator, log_function=mock_logger
    )

    bucket = "test_bucket"
    folder = "test_folder"

    result = storage.list_files(bucket, folder)

    assert result == [{}]
    mock_logger.assert_called_once_with(
        level="error",
        action="list files",
        bucket="test_bucket",
        exception=error,
    )


def test_create_signed_url(mocker, client_with_mocks, mock_validator):
    mock_url = "https://example.com"
    mock_connection = mocker.Mock(return_value={"signedURL": mock_url})
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks, mock_validator)
    bucket = "test_bucket"
    path = "test_path"

    result = storage.create_signed_url(bucket, path)

    assert result == mock_url
    mock_connection.assert_called_once_with(
        bucket, "create_signed_url", path="test_path", expires_in=3600
    )

    mock_validator.assert_called_once_with(mock_url, str)


def test_create_signed_url_accepts_expires_in(mocker, client_with_mocks):
    mock_url = "https://example.com"
    mock_connection = mocker.Mock(return_value={"signedURL": mock_url})
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )
    storage = SupabaseStorage(client_with_mocks)
    bucket = "test_bucket"
    path = "test_path"
    expires_in = 1800

    result = storage.create_signed_url(bucket, path, expires_in=expires_in)

    assert result == mock_url
    mock_connection.assert_called_once_with(
        bucket, "create_signed_url", path="test_path", expires_in=1800
    )


def test_create_signed_url_storage_exception(
    mocker, client_with_mocks, mock_logger
):
    error = StorageException()
    mock_connection = mocker.Mock(side_effect=error)
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(client_with_mocks, log_function=mock_logger)

    bucket = "test_bucket"
    path = "test_path"

    result = storage.create_signed_url(bucket, path)

    assert result == ""
    mock_logger.assert_called_once_with(
        level="error",
        action="create signed url",
        bucket="test_bucket",
        download_path="test_path",
        expires_in=3600,
        exception=error,
    )


def test_create_signed_url_validator_exception(
    mocker, client_with_mocks, mock_logger
):
    error = ValueError()
    mock_validator = mocker.Mock(side_effect=error)
    mock_connection = mocker.Mock(return_value={"signedURL": ""})
    mocker.patch.object(
        SupabaseStorage, "_use_storage_connection", mock_connection
    )

    storage = SupabaseStorage(
        client_with_mocks, mock_validator, log_function=mock_logger
    )

    bucket = "test_bucket"
    path = "test_path"

    result = storage.create_signed_url(bucket, path)

    assert result == ""
    mock_logger.assert_called_once_with(
        level="error",
        action="create signed url",
        bucket="test_bucket",
        download_path="test_path",
        expires_in=3600,
        exception=error,
    )
