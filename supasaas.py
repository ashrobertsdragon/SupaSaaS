import inspect
import logging
import os
from typing import Optional, Callable, TypeVar, ParamSpec, get_type_hints, get_origin, get_args
from functools import wraps

from gotrue.types import AuthResponse, UserResponse
from supabase import create_client, Client


T = TypeVar('T')
P = ParamSpec('P')

class SupabaseClient():
    """
    Parent class for initializing the client to interact with Supabse API and
    methods to be inherited by child classes such as logging and validation.

    Attributes:
        _mono_state (dict): A dictionary representing the shared state of all
            instances of the class.
    """
    _mono_state: dict = {}

    def _get_env_value(self, key: str) -> str:
        """Retrieves the value of an environment variable"""
        if isinstance(key, str):
            try:
                return os.environ[key]
            except Exception:
                raise LookupError(f"Supabase API {key} not found")
        else:
            raise TypeError(f"{key} must be string")

    def __init__(self) -> None:
        """Initiate one and only copy of the client."""
        self.__dict__ = self._mono_state

        try:
            self.url: str = self._get_env_value("SUPABASE_URL")
        except Exception:
            raise LookupError("Supabase API URL not found")
        
        if "default_client" not in self.__dict__:
            key: str = self._get_env_value("SUPABASE_KEY")
            self.default_client: Client = create_client(self.url, key)
            if self.default_client:
                self.log_info(action="Initialized Supabase default client")

    
    def log_info(self, action: str, *args, **kwargs) -> None:
        """
        Log a Supabase response with the info logger.

        Args:
            action (str): The action being performed.
            response (dict): The dictionary of table data returned.
        
        Example:
            log_info("select", {"email": "example@example.com", "name": "John"})
        
        """
        all_args: str = ", ".join(*args)
        all_kwargs: str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        logging.info(f"{action} returned {all_args}{all_kwargs}")

    def create_error_message(self, action: str, **kwargs) -> str:
        """
        Create the error message for for logging errors.

        Args:
            action (str): The action being performed.
            updates (dict, optional): The updates being made. Defaults to
                None.
            match (dict, optional): The matching criteria. Defaults to None.
            email (str, optional): The email associated with the error.
                Defaults to None.
            table_name (str, optional): The name of the table. Defaults to 
                None.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The error message.

        Example:
            create_error_message(
                "insert", updates={"name": "John"}, table_name="users"
            )
        """
        error_message: list = [f"Error performing {action}"]

        arguments = {**kwargs}
        for arg_name, arg_value in arguments.items():
            if arg_value:
                error_message.append(f" with {arg_name}: {arg_value}")

        return " ".join(error_message)

    def log_error(self, e: Exception, action: str, **kwargs) -> None:
        """
        Log an error and send an email to the admin.

        Args:
            e (Exception): The exception that occurred.
            action (str): The action being performed.
            **kwargs: Additional keyword arguments.

        Returns:
            None

        Example:
            log_error(
                Exception("Something went wrong"), "insert",
                updates={"name": "John"}, table_name="users"
            )
        """
        error_message = self.create_error_message(action, **kwargs)
        error_message += "\nException: %s"
        logging.error(error_message, str(e))

    @classmethod
    def _validate_type(cls, value: Optional[any], *, name: str, is_type: type, allow_none: bool) -> None:
        """
        Validate the type of a value.

        Args:
            value (Optional[any]): The value to be validated. May be any type,
                or None.
            name (str): The name of the argument or parameter.
            is_type (type): The expected type of the value.
            allow_none (bool): Whether None is allowed as a value.

        Raises:
            ValueError: If the value is None and allow_none is False or if
                is_type is None.
            TypeError:  If the value is not an instance of the expected type.
        """
        if value is None:
            if not allow_none:
                raise ValueError(f"{name} must have value")
        else:
            if is_type is None:
                raise ValueError("is_type must not be None")
            if not isinstance(value, is_type):
                raise TypeError(f"{name} must be {is_type.__name__}")

    @classmethod
    def _validate_dict(cls, value: any, name: str) -> None:
        """Validate a dictionary"""
        cls._validate_type(value, name=name, is_type=dict)

    @classmethod    
    def _validate_list(cls, value: any, name: str) -> None:
        """Validate a list"""
        cls._validate_type(value, name=name, is_type=list)

    @classmethod    
    def _validate_string(cls, value: any, name: str) -> None:
        """Validate a string"""
        cls._validate_type(value, name=name, is_type=str)

    @classmethod
    def _validate_param_value(cls, param_value: Optional[any], param_name: str, param_type: type) -> None:
        """
        Validate the value of a parameter.

        Args:
            param_value (Optional[any]): The value of the parameter. It can be
                any type or None.
            param_name (str): The name of the parameter.
            param_type (type): The expected type of the parameter.

        Returns:
            None

        Raises:
            ValueError: If the param_value is None and the param_type is not
                Optional.
            TypeError: If the param_value is not an instance of the expected
                param_type.
        """
        origin_type = get_origin(param_type)
        check_type = origin_type if origin_type is not Optional else get_args(param_type)[0]
        none_bool = (origin_type is Optional)   
        cls._validate_type(param_value, name=param_name, is_type=check_type, allow_none=none_bool)

    @staticmethod
    def validate_arguments(func: Callable[P, T]) -> Callable[P, T]:
        """
        Validate the arguments of a function based on their type annotations.

        Args:
            func (Callable[P, T]): The function to be decorated.

        Returns:
            Callable[P, T]: The decorated function.

        Example:
            @validate_arguments
            def my_function(arg1: int, arg2: str) -> bool:
                ...

        The 'validate_arguments' decorator validates the arguments of a
        function based on their type annotations. It uses the 'get_type_hints'
        function from the 'typing' module to retrieve the type hints of the
        function parameters.

        The decorator works by creating a wrapper function that performs the
        argument validation before calling the original function. It uses the
        'inspect' module to get the signature of the function and bind the
        arguments to their corresponding parameters.

        For each argument, the decorator checks if its value matches the
        expected type based on the type annotation. If the value is not of the
        expected type, a 'TypeError' is raised.

        The decorator can be used by applying the '@validate_arguments'
        decorator to a function definition. This will enable argument 
        validation for that function.

        Note: When uses in a child class, the decorator becomes
        '@SupabaseClient.validate_arguments' as decorators are not inherited.

        Note: The 'validate_arguments' decorator only validates the types of
        the arguments. It does not perform any other form of validation or 
        modification of the arguments.

        """
        type_hints: dict = get_type_hints(func)

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            signature = inspect.signature(func)
            bound_args = signature.bind_partial(*args, **kwargs)

            bound_args_arguments: dict = {k: v for k, v in bound_args.arguments.items() if k != 'self'}
            for param_name, param_value in bound_args_arguments.items():
                param_type: type = type_hints[param_name]
                self._validate_param_value(param_value, param_name, param_type)
            return func(self, *args, **kwargs)

        return wrapper

class SupabaseAuth(SupabaseClient):
    """
    Subclass of SupabaseClient for user authentication and managing the
    authentication table via Supabase API.
    """
    def __init__(self) -> None:
        super().__init__()

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
            Exception: If an error occurs during the sign up process.

        Example:
            sign_up(email="example@example.com", password="password123")
        """
        try:
            return self.default_client.auth.sign_up({
                "email": email,
                "password": password,
            })
        except Exception as e:
            action = "signup"
            self.log_error(e, action, email=email)
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
            Exception: If an error occurs during the sign in process.

        Example:
            sign_in(email="example@example.com", password="password123")
        """
        try:
            return self.default_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        except Exception as e:
            action = "login"
            self.log_error(e, action, email=email)
            raise

    def sign_out(self) -> None:
        """
        Signs out the currently authenticated user.

        Raises:
            Exception: If an error occurs during the sign out process.

        Example:
            sign_out()
        """
        try:
            self.default_client.auth.sign_out()
        except Exception as e:
            action = "logout"
            self.log_error(e, action)
            raise

    def reset_password(self, *, email: str, domain: str) -> None:
        """
        Resets the password for a user with the provided email.

        Args:
            email (str): The email of the user.
            domain (str): The domain of the application.

        Raises:
            Exception: If an error occurs during the password reset process.

        Example:
            reset_password(email="example@example.com", domain="example.com")
        """
        try:
            self.default_client.auth.reset_password_email(
                email,
                options={"redirect_to": f"{domain}/reset-password.html"}
            )
        except Exception as e:
            action = "reset_password"
            self.log_error(e, action, email=email)
            raise

    def update_user(self, updates: dict) -> UserResponse:
        """
        Updates a user with the provided updates.

        Args:
            updates (dict): A dictionary containing the updates to be made to
                the user.

        Returns:
            UserResponse: The response object containing the updated user
                information.

        Raises:
            Exception: If an error occurs during the update process.

        Example:
            update_user(updates={"name": "John", "age": 30})
        """
        try:
            return self.default_client.auth.update_user(updates)
        except Exception as e:
            action = "update user"
            self.log_error(e, action, updates=updates)
            raise

class SupabaseStorage(SupabaseClient):
    """
    Subclass of the 'SupabaseClient' class for interacting with the Supabase
    storage service via API.
    """
    @SupabaseClient.validate_arguments
    def upload_file(self, bucket: str, upload_path: str, file_content: bytes, file_mimetype: str) -> bool:
        """
        Upload a file to the specified bucket.

        Args:
            bucket (str): The name of the bucket.
            upload_path (str): The path where the file will be uploaded.
            file_content (bytes): The content of the file to be uploaded.
            file_mimetype (str): The mimetype of the file.

        Returns:
            bool: True if the file is successfully uploaded, False otherwise.

        Raises:
            Exception: If an error occurs during the process.

        Example:
            file_content = file.read()
            upload_file(
              "my_bucket",
              "path/to/file.txt", file_content, "text/plain")
        """
        action: str = "upload file"
        try:
            self.default_client.storage.from_(bucket).upload(
                path=upload_path,
                file=file_content,
                file_options={"content-type": file_mimetype}
            )
        except Exception as e:
            self.log_error(
                e, action, 
                upload_path=upload_path,
                file_mimetype=file_mimetype
            )
            return False
        return True
    
    @SupabaseClient.validate_arguments
    def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete a file from the specified bucket.

        Args:
            bucket (str): The name of the bucket.
            file_path (str): The path of the file to be deleted.

        Returns:
            bool: True if the file is successfully deleted, False otherwise.

        Raises:
            Exception: If an error occurs during the process.

        Example:
            delete_file("my_bucket", "path/to/file.txt")
        """
        action: str = "delete file"
        try:
            self.default_client.storage.from_(bucket).remove(file_path)
        except Exception as e:
            self.log_error(
                e, action, 
                file_path=file_path
            )
            return False
        success: str = "File deleted"
        self.log_info(action, success)
        return True

    @SupabaseClient.validate_arguments
    def list_files(self, bucket: str, folder: Optional[str] = None) -> list:
        """
        List files or folders in a specified bucket. If the folder argument is
        provided, the method will list the files in the specificed folder in 
        the bucket.

        Args:
            bucket (str): The name of the bucket.
            folder (Optional[str], optional): The folder within the bucket to
                list files from. Defaults to None.

        Returns:
            list: A list of the files and folders in the specified bucket or
                folder.

        Raises:
            Exception: If an error occurs during the process.

        Example:
            files = list_files("my_bucket", folder="path/to/folder")
        """
        action: str = "list files"
        try:
            if folder:
                response = self.default_client.storage.from_(bucket).list(folder)
            else:
                response = self.default_client.storage.from_(bucket).list()
        except Exception as e:
            self.log_error(e, action, bucket=bucket)
            return []
        try:
            self._validate_list(response, name="response")
            return response
        except Exception as e:
            self.log_error(e, action, bucket=bucket)
            return []
        
    @SupabaseClient.validate_arguments
    def create_signed_url(self, bucket: str, download_path: str, *, expires_in: Optional[int] = 3600) -> str:
        """
        Create a signed URL for downloading a file from the specified bucket
        and path.

        Args:
            bucket (str): The name of the bucket where the file is stored.
            download_path (str): The path of the file to be downloaded.
            expires_in (Optional[int], optional): The expiration time of the
                signed URL in seconds. Defaults to 3600.

        Returns:
            str: The signed URL for downloading the file.

        Raises:
            Exception: If an error occurs during the process.

        Example:
            signed_url = create_signed_url(
                "my_bucket",
                "path/to/file.txt",
                expires_in=3600
            )
        """
        action: str = "create signed url"
        
        try:
            response = self.default_client.storage.from_(bucket).create_signed_url(download_path, expires_in=expires_in)
            self._validate_string(response, name="response")
            return response
        except Exception as e:
            self.log_error(
                e, action,
                download_path=download_path,
                expires_in=expires_in
            )
            return ""

class SupabaseDB(SupabaseClient):
    """
    Subclass of the 'SupabaseClient' for connecting to Postgres database via
    Supabase API and perform common SQL tasks necessary for SaaS management.
    """
    def __init__(self) -> None:
        """
        Initializes one and only one copy of client with service role
        credentials and inherits default_client from 'SupabaseClient'.
        """
        super().__init__()

        if "service_client" not in self.__dict__:
            service_role: str = super()._get_env_value("SUPABASE_SERVICE_ROLE")
            self.service_client: Client = create_client(self.url, service_role)
            if self.service_client:
                self.log_info(action="Initialized Supabase service client")

    def _select_client(self, use_service_role: bool = False) -> Client:
        """
        Selects the appropriate Supabase client.

        Args:
            use_service_role (bool, optional): Determines whether to use the 
                service role client or the default client. Defaults to False.

        Returns:
            Client: The selected Supabase client.
        """
        try:
            if use_service_role:
                return self.service_client
            else:
                return self.default_client
        except Exception as e:
            action = "accessing client"
            self.log_error(e, action)
            return None

    @classmethod
    def _extract_match(cls, match: dict) -> tuple[str, str]:
        """
        Checks the match dictionary for correct data and then extracts it.

        Args:
            match (dict): The dictionary with a key and value to be extracted.
        
        Returns:
            key (str): The key of the key-value pair.
            value (str): The value of the key-value pair.

        Raises:
            IndexError: If the dictionary is empty or has more than one key-
                value pair.
            KeyError: If the key or value is not a string.
        """
        try:
            if len(match.keys()) != 1:
                raise IndexError("Match dictionary must have one key-value pair")
            for key, value in match.items():
                if not isinstance(key, str):
                    raise KeyError(f"{key} must be a string")
                if not isinstance(value, str):
                    raise KeyError(f"Value for filter '{key}' must be a string")
        except Exception as e:
            cls.log_error(e, match=match)

        key, value = list(match.items())[0]
        return key, value

    @SupabaseClient.validate_arguments
    def insert_row(
        self, *, table_name: str, data: dict, use_service_role: bool = False
    ) -> bool:
        """
        Inserts a row into a table.

        Args:
            table_name (str): The name of the table to insert the row into.
            data (dict): The data to be inserted as a row. Should be a 
                dictionary where the keys represent the column names and the 
                values represent the corresponding values for each column.
            use_service_role (bool, optional): Determines whether to use the 
              service role client or the default client. Service role client
              should only be used for operations where a new user row is being
              inserted. Otherwise use default client for RLS policy on
              authenticated user. Defaults to False.

        Returns:
            bool: True if the insert was successful, False otherwise.

        Raises:
            ValueError: If the response did not return a populated data list.
            Exception: If there is an error while inserting the row, an 
                exception will be raised and logged.

        Example:
            supabase_db = SupabaseDB()
            supabase_db.insert_row(
                table_name="users",
                data={
                    "name": "John Doe",
                    "age": 30,
                    "email": "johndoe@example.com"
                },
                use_service_role=True
            )
        """
        db_client = self._select_client(use_service_role)
        action: str = "insert"

        try:
            res = db_client.table(table_name).insert(data).execute()
            if not res.data:
                raise ValueError("Response has no data")
        except Exception as e:
            self.log_error(e, action, data=data, table_name=table_name)
            return False
        return True

    @SupabaseClient.validate_arguments
    def select_row(
        self, *, table_name: str, match: dict, columns: list[str] = ["*"]
    ) -> list[dict]:
        """
        Retrieves a row or columns from a table based on a matching condition.

        Args:
            table_name (str): The name of the table to retrieve the row from.
            match (dict): A dictionary representing the matching condition.
                The key should be the column name and the value should be 
                the corresponding value to match.
            ValueError: If the match argument is not a dictionary, or
                table_name is not a string.
            columns (list[str], optional): A list of column names to retrieve 
                from the row. Defaults to ["*"], which retrieves all columns.

        Returns:
            list[dict]: A list of dictionaries representing the retrieved row
                or rows. If no row is found matching the condition, an empty
                dictionary is returned.

        Raises:
            IndexError: If the match dictionary has more than one key-value
                pair.
            TypeError: If the response returned was not a list.
            ValueError: If there was no response returned or no data object.
            Exception: If there is an error while retrieving the row, an
                exception will be raised and logged.

        Example:
            supabase_db = SupabaseDB()
            result = supabase_db.select_row(
                table_name="users",
                match={"name": "John Doe"},
                columns=["name", "age", "email"]
            )
            print(result)
            # Output: {"name": "John Doe", "age": 30, "email": "johndoe@example.com"}
        """
        db_client = self._select_client()
        action = "select"

        try:
            match_name, match_value = self._extract_match(match)
            res = db_client.table(table_name).select(*columns).eq(match_name, match_value).execute()

            if res and res.data:
                self._validate_dict(res.data)
                return res.data
        except Exception as e:
            self.log_error(e, action, columns=columns, match=match)
            return {}

    @SupabaseClient.validate_arguments
    def update_row(self, *, table_name: str, info: dict, match: dict) -> bool:
        """
        Updates a row in the table with data when the row matches a column.
        Returns True if the update was successful, False otherwise.

        Args:
            table_name (str): The name of the table to update the row in.
            info (dict): A dictionary representing the data to update in the
                row. The keys should be the column names and the values should
                be the corresponding values to update.
            match (dict): A dictionary representing the matching condition for
                the row to update. The keys should be the column name and the
                value should be the corresponding value to match.

        Returns:
            bool: True if the update was successful, False otherwise.

        Raises:
            ValueError: If the match argument is not a dictionary, or
                table_name is not a string.
            Exception: If there is an error while updating the row, an
                exception will be raised and logged.

        Example:
            supabase_db = SupabaseDB()
            result = supabase_db.update_row(
                table_name="users",
                info={"age": 31},
                match={"name": "John Doe"}
            )
            print(result)
            # Output: True
        """
        db_client = self._select_client()
        action = "update"

        try:
            match_name, match_value = self._extract_match(match)
            res = db_client.table(table_name).update(info).eq(match_name, match_value).execute()
        except Exception as e:
            self.log_error(e, action, updates=info, match=match)
            return False
        if res.data:
            return True
        else:
            log="Data is the same"
            self.log_info(action, res, info=info, log=log)
            return False

    @SupabaseClient.validate_arguments
    def find_row(self, *, table_name: str, date_column: str, within_period: int, columns: list[str] = ["*"]) -> dict:
        """
        Retrieves a row from a table based on a matching condition.

        Args:
            table_name (str): The name of the table to retrieve the row from.
            date_column (str): The name of a column with a date format to be
                compared against.
            within_period (int): The range of days against which to check for
                a row.
            columns (list[str], optional): A list of column names to retrieve 
                from the row. Defaults to ["*"], which retrieves all columns.

        Returns:
            dict: A dictionary representing the retrieved row or rows. If no
                row is found matching the condition, an empty dictionary is
                returned.

        Raises:
            Exception: If there is an error while retrieving the row, an
                exception will be raised and logged.

        Example:
            supabase_db = SupabaseDB()
            result = supabase_db.find_row(
                table_name="users",
                match_column="age",
                within_period=30,
                columns=["name", "age", "email"]
            )
            print(result)
        """
        db_client = self._select_client()
        action: str = "find row"

        try:
            res = db_client.table(table_name).select(columns).lte(date_column, within_period).execute()
            if res and res.data:
                self._validate_dict(res.data)
                return res.data
        except Exception as e:
            self.log_error(
                e, action,
                table_name=table_name,
                match_column=date_column,
                within_period=within_period,
                columns=columns
            )
            return {}
