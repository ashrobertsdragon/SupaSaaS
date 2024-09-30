from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

from supabase import Client, StorageException

from supasaas._logging.supabase_logger import supabase_logger as default_logger
from supasaas._validators import validate as default_validator
from supasaas.supabase_client import SupabaseClient

LogFunction: TypeAlias = Callable[[str, str, bool, Any, Any], None]
ValidatorFunction: TypeAlias = Callable[[Any, type, bool], None]


class SupabaseStorage:
    def __init__(
        self,
        client: SupabaseClient,
        validator: ValidatorFunction = default_validator,
        log_function: LogFunction = default_logger,
    ) -> None:
        self.client: Client = client.select_client()
        self.log = log_function
        self.validator = validator
        self.empty_value: list[dict] = [{}]

    def _use_storage_connection(
        self, bucket: str, action: str, **kwargs
    ) -> Any:
        """
        Use context manager for connection to Supabase storage.

        Args:
            bucket (str): The name of the storage bucket.
            action (str): The action being performed in the bucket).
            **kwargs: Other commands being passed to the API.
        """
        with self.client.storage as storage_client:
            storage = storage_client.from_(bucket)
            return getattr(storage, action)(**kwargs)

    def _validate_response(
        self,
        response: Any,
        *,
        expected_type: type,
        action: str,
        bucket: str,
        **kwargs,
    ) -> bool:
        """
        Validate the storage response from Supabase.

        Args:
            response (Any): The response object from the API call.
            expected_type (type): The type the response is expected to be.
            action (str): The storage action being performed.
            bucket (str): The storage bucket the action was performed in.
            **kwargs: Other keyword arguments to be logged if validation
                fails.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        try:
            self.validator(response, expected_type)
            return True
        except (ValueError, TypeError) as e:
            self.log(
                level="error",
                action=action,
                bucket=bucket,
                exception=e,
                **kwargs,
            )
            return False

    def upload_file(
        self,
        bucket: str,
        upload_path: str,
        file_content: bytes,
        file_mimetype: str,
    ) -> bool:
        """
        Upload a file to a Supabase storage bucket.

        Args:
            bucket (str): The bucket the file will be uploaded to.
            upload_path (str): The folder and filename for the file to be
                uploaded to.
            file_content (bytes): The file, read as an IO byte-stream, to be
                uploaded.
            file_mimetype (str): The file's mimetype.

        Returns:
            bool: True if upload was successful, False otherwise.
        """
        try:
            self._use_storage_connection(
                bucket,
                "upload",
                path=upload_path,
                file=file_content,
                file_options={"content-type": file_mimetype},
            )
        except StorageException as e:
            self.log(
                level="error",
                action="upload file",
                bucket=bucket,
                upload_path=upload_path,
                file_content=file_content,
                file_mimetype=file_mimetype,
                exception=e,
            )
            return False
        return True

    def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete a file from a Supabase storage bucket

        Args:
            bucket (str): The storage bucket the file will be deleted from.
            file_path (str): The path inside the bucket for the file to be
                deleted.

        Returns:
            bool: True if file deletion was successful, False otherwise.
        """
        try:
            self._use_storage_connection(bucket, "remove", paths=[file_path])
        except StorageException as e:
            self.log(
                level="error",
                action="delete file",
                bucket=bucket,
                file_path=file_path,
                exception=e,
            )
            return False
        return True

    def download_file(
        self, bucket: str, download_path: str, destination_path: Path
    ) -> bool:
        """
        Download a file from a Supabase storage bucket.

        Args:
            bucket (str): The storage bucket the file will be found in.
            download_path (str): The path inside the bucket for the file to be
                downloaded.
            destination_path (Path): The local path to download the file to,
                as a pathlib object.

        Returns:
            bool: True if file was downloaded, False otherwise.
        """
        try:
            with destination_path.open("wb+") as f:
                response = self._use_storage_connection(
                    bucket, "download", path=download_path
                )
                f.write(response)
            return True
        except (StorageException, OSError) as e:
            self.log(
                level="error",
                action="download file",
                bucket=bucket,
                download_path=download_path,
                destination_path=destination_path,
                exception=e,
            )
            return False

    def list_files(
        self, bucket: str, folder: str | None = None
    ) -> list[dict[str, str]]:
        """
        List the files in a Supabase storage bucket or folder.

        Args:
            bucket (str): The storage bucket to retrieve the list of files
                from.
            folder (str): The name of the folder within the storage bucket to
                retrieve the list of files from. Optional, defaults to None.

        Returns:
            list[dict[str, str]]: A list of dictionaries containing
                information about files in the bucket or folder or empty list
                if there is an error.
        """
        action: str = "list files"
        try:
            if folder:
                response = self._use_storage_connection(
                    bucket, "list", path=folder
                )
            else:
                response = self._use_storage_connection(bucket, "list")
        except StorageException as e:
            self.log(level="error", action=action, bucket=bucket, exception=e)
            return self.empty_value
        if self._validate_response(
            response, expected_type=list, action=action, bucket=bucket
        ):
            return response
        else:
            return self.empty_value

    def create_signed_url(
        self,
        bucket: str,
        download_path: str,
        *,
        expires_in: int | None = 3600,
    ) -> str:
        """
        Create a signed download URL to a file in a Supabase storage bucket.

        Args:
            bucket (str): The storage bucket the download file is in.
            download_path (str): The path to the file in the bucket.
            expires_in (in): Optional. Number of seconds the signed url is
                valid for. Defaults to 3600 (one hour).

        Returns:
            str: The signed url for file download or empty string if there is
                an error.
        """
        action = "create signed url"
        try:
            response = self._use_storage_connection(
                bucket,
                "create_signed_url",
                path=download_path,
                expires_in=expires_in,
            )
        except StorageException as e:
            self.log(
                level="error",
                action=action,
                bucket=bucket,
                download_path=download_path,
                expires_in=expires_in,
                exception=e,
            )
            return ""

        url = response["signedURL"]
        if self._validate_response(
            url,
            expected_type=str,
            action=action,
            bucket=bucket,
            download_path=download_path,
            expires_in=expires_in,
        ):
            return url
        else:
            return ""
