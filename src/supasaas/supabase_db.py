from collections.abc import Callable
from typing import Any, TypeAlias

from postgrest import APIResponse, SyncRequestBuilder
from supabase import Client, PostgrestAPIError

from supasaas._logging.supabase_logger import supabase_logger as default_logger
from supasaas._validators import validate as default_validator
from supasaas.supabase_client import SupabaseClient

LogFunction: TypeAlias = Callable[[str, str, bool, Any, Any], None]
ValidatorFunction: TypeAlias = Callable[[Any, type, bool], None]
Table: TypeAlias = SyncRequestBuilder


class SupabaseDB:
    def __init__(
        self,
        client: SupabaseClient,
        validator: ValidatorFunction = default_validator,
        log_function: LogFunction = default_logger,
    ) -> None:
        self.client = client
        self.log = log_function
        self.validator = validator
        self.empty_value: list[dict] = [{}]

    def _get_client(self, use_service_role: bool) -> Client:
        "Return the correct client based on the `use_service_role` boolean"
        return self.client.select_client(use_service_role)

    def _execute_query(
        self, db_client: Client, table_name: str, query: Callable
    ) -> APIResponse:
        """
        Execute the database query on the table with the correct client.

        Args:
            db_client (Client): The Supabase client with the correct
                permissions for the query.
            table_name (str): The name of the table to be queried.
            query (Callable): The lambda function of the Supabase SDK query.
                Example: `lambda table: table.insert(row_dictionary)`

        Returns:
            APIResponse: The json response object with a data list and count
                integer.
        """
        with db_client.postgrest as postgrest:
            table = postgrest.from_(table_name)
            return query(table).execute()

    def _validate_response(
        self,
        data: Any,
        *,
        action: str,
        table_name: str,
        **kwargs,
    ) -> bool:
        """
        Validate the data response from the Supabase SDK against the expected
        type and log an error if it doesn't match.

        Args:
            data (Any): The data object from the JSON response.
            action (str): The query action being performed.
            table_name (str): The table the query was performed on.
            **kwargs: Any other keyword arguments to be logged.

        Returns:
            bool: True if the data object is a list of dictionaries and False
                if not.
        """
        try:
            self.validator(data, list)
            for item in data:
                self.validator(item, dict)
            return True
        except (ValueError, TypeError) as e:
            self.log(
                level="error",
                action=action,
                table_name=table_name,
                data=data,
                exception=e,
                **kwargs,
            )
            return False

    def _get_filter(
        self,
        match: dict,
        *,
        expected_value_type: type,
        action: str,
        table_name: str,
    ) -> tuple[str, str]:
        """
        Parse the dictionary storing the query filter

        Args:
            match (dict): The dictionary containing the query filter.
            action (str): The query action being performed.
            table_name (str): The table the query is being performed on.

        Returns:
            tuple[str, str]: The match_name and match_value of the query
                filter.
        """
        try:
            self.validator(match, dict)
            if len(match.keys()) > 1:
                raise ValueError(
                    "Match dictionary must have one key-value pair"
                )
            for key, value in match.items():
                self.validator(key, str)
                try:
                    self.validator(value, expected_value_type)
                except TypeError as error:
                    raise TypeError(
                        f"Value for filter '{key}' "
                        f"must be a {expected_value_type.__name__}"
                    ) from error
        except (ValueError, TypeError) as e:
            self.log(
                level="error",
                exception=e,
                action=action,
                match=match,
                table_name=table_name,
            )
            raise

        match_name, match_value = next(iter(match.items()))
        return match_name, match_value

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
            bool: True if the update was successful, False otherwise.
        """

        db_client: Client = self._get_client(use_service_role)
        try:
            response = self._execute_query(
                db_client=db_client,
                table_name=table_name,
                query=lambda table: table.insert(data),
            )
            if not response.get("data"):
                raise PostgrestAPIError({
                    "message": f"Failed to insert row into {table_name}"
                })
        except PostgrestAPIError as e:
            self.log(
                level="error",
                action="insert",
                data=data,
                table_name=table_name,
                exception=e,
            )
            return False
        return True

    def delete_row(
        self, *, table_name: str, match: dict, match_type: type
    ) -> bool:
        """
        Deletes a row from a table based on a matching condition.
        Args:
            table_name (str): The name of the table to delete the row from.
            match (dict): A dictionary representing the matching condition for
                the row to delete. The keys should be the column name and the
                value should be the corresponding value to match.

        Returns:
            bool: True if the row deletion was successful, False otherwise.
        """
        action: str = "delete"
        db_client: Client = self._get_client(use_service_role=False)
        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            self._execute_query(
                db_client=db_client,
                table_name=table_name,
                query=lambda table: table.delete.eq(match_name, match_value),
            )
            return True
        except (PostgrestAPIError, ValueError, TypeError) as e:
            self.log(
                level="error",
                table_name=table_name,
                exception=e,
                action=action,
                match=match,
            )
            return False

    def select_row(
        self,
        *,
        table_name: str,
        match: dict,
        match_type: type,
        columns: list[str] | None = None,
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
            columns (List[str], optional): A list of column names to retrieve
                from the row. Defaults to ["*"], which retrieves all columns.

        Returns:
            List[dict]: A list of dictionaries representing the retrieved row
                or rows. If no row is found matching the condition, an empty
                dictionary is returned.
        """
        action = "select"
        column_str = "*" if columns is None else ", ".join(columns)

        db_client: Client = self._get_client(use_service_role=True)
        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            response = self._execute_query(
                db_client=db_client,
                table_name=table_name,
                query=lambda table: table.select(column_str).eq(
                    match_name, match_value
                ),
            )
            if not response.get("data"):
                raise PostgrestAPIError({
                    "message": f"Failed to select row into {table_name}"
                })
        except (PostgrestAPIError, ValueError, TypeError) as e:
            self.log(
                level="error",
                exception=e,
                action=action,
                table_name=table_name,
                column_str=column_str,
                match=match,
            )
            return self.empty_value
        if self._validate_response(
            response.get("data"),
            expected_type=list,
            action=action,
            table_name=table_name,
            column_str=column_str,
            match=match,
        ):
            return response["data"]
        else:
            return self.empty_value

    def update_row(
        self, *, table_name: str, info: dict, match: dict, match_type: type
    ) -> bool:
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
        """
        action: str = "update"
        db_client: Client = self._get_client(use_service_role=False)
        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            response = self._execute_query(
                db_client=db_client,
                table_name=table_name,
                query=lambda table: table.update(info).eq(
                    match_name, match_value
                ),
            )
            if not response.get("data"):
                raise PostgrestAPIError({
                    "message": f"Failed to update row into {table_name}"
                })
            return True
        except (PostgrestAPIError, ValueError, TypeError) as e:
            self.log(
                level="error",
                action=action,
                info=info,
                match=match,
                exception=e,
                table_name=table_name,
            )
            return False

    def find_row(
        self,
        *,
        table_name: str,
        match_column: str,
        within_period: int,
        columns: list[str] | None = None,
    ) -> list[dict]:
        action: str = "find row"
        if columns is None:
            columns = ["*"]

        db_client: Client = self._get_client(use_service_role=False)
        try:
            response = self._execute_query(
                db_client=db_client,
                table_name=table_name,
                query=lambda table: table.select(columns).lte(
                    match_column, within_period
                ),
            )
        except PostgrestAPIError as e:
            self.log(
                level="error",
                exception=e,
                action=action,
                table_name=table_name,
                match_column=match_column,
                within_period=within_period,
                columns=columns,
            )
            return self.empty_value

        if response.get("data") and self._validate_response(
            response.get("data"),
            expected_type=list,
            action=action,
            table_name=table_name,
            match_column=match_column,
            within_period=within_period,
            columns=columns,
        ):
            return response["data"]
        return self.empty_value
