from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias

from postgrest import SyncRequestBuilder
from supabase import Client, PostgrestAPIError, PostgrestAPIResponse

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
        self,
        use_service_role: bool,
        table_name: str,
        query_func: Callable,
    ) -> PostgrestAPIResponse:
        """
        Execute the database query on the table with the correct client.

        Checks if the client has been closed. If so, it refreshes the client
        by calling the `refresh_clients` method and retries the action.

        Args:
            db_client (Client): The Supabase client with the correct
                permissions for the query.
            table_name (str): The name of the table to be queried.
            query (Callable): The lambda function of the Supabase SDK query.
                Example: `lambda table: table.insert(row_dictionary)`

        Returns:
            PostgrestAPIResponse: The json response object with a data list and
                count integer.
        """
        db_client: Client = self._get_client(use_service_role)
        try:
            with db_client.postgrest as postgrest:
                table = postgrest.from_(table_name)
                return query_func(table).execute()
        except RuntimeError as e:
            if "Cannot send a request, as the client has been closed." in str(
                e
            ):
                self._refresh_client()
                return self._execute_query(
                    use_service_role, table_name, query_func
                )
            raise

    def _refresh_client(self):
        """
        Refresh the Supabase client by re-initializing the internal clients.
        """
        self.log(level="info", action="Calling for new clients")
        self.client.refresh_clients()

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

        try:
            response = self._execute_query(
                use_service_role=use_service_role,
                table_name=table_name,
                query_func=lambda table: table.insert(data),
            )
            if not response.data:
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
        self,
        *,
        table_name: str,
        match: dict,
        match_type: type,
        use_service_role: bool = False,
    ) -> bool:
        """
        Deletes a row from a table based on a matching condition.
        Args:
            table_name (str): The name of the table to delete the row from.
            match (dict): A dictionary representing the matching condition for
            the row to delete. The keys should be the column name and the value
            should be the corresponding value to match.
            match_type (type): The type of the value in the match dictionary.
            use_service_role (bool, optional): Determines whether to use the
            service role client or the default client. Service role client
            should only be used for operations where there is no logged in
            user. Otherwise use default client for RLS policy on authenticated
            user. Defaults to False.

        Returns:
            bool: True if the row deletion was successful, False otherwise.
        """
        action: str = "delete"
        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            self._execute_query(
                use_service_role=use_service_role,
                table_name=table_name,
                query_func=lambda table: table.delete.eq(
                    match_name, match_value
                ),
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
        use_service_role: bool = False,
    ) -> list[dict]:
        """
        Retrieves a row or columns from a table based on a matching condition.

        Args:
            table_name (str): The name of the table to retrieve the row from.
            match (dict): A dictionary representing the matching condition.
            The key should be the column name and the value should be
            the corresponding value to match.
            match_type (type): The type of the value in the match dictionary.
            columns (list[str], optional): A list of column names to retrieve
                from the row. Defaults to None, which retrieves all columns.
            use_service_role (bool, optional): Determines whether to use the
                service role client or the default client. Service role client
                should only be used for operations where there is no logged in
                user. Otherwise use default client for RLS policy on
                authenticated user. Defaults to False.

        Returns:
            List[dict]: A list of dictionaries representing the retrieved row
                or rows. If no row is found matching the condition, an empty
                dictionary is returned.
        """
        action = "select"
        column_str = "*" if columns is None else ", ".join(columns)

        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            response = self._execute_query(
                use_service_role=use_service_role,
                table_name=table_name,
                query_func=lambda table: table.select(column_str).eq(
                    match_name, match_value
                ),
            )
            if not response.data:
                self.log(level="info", action=action, response=response)
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
            response.data,
            expected_type=list,
            action=action,
            table_name=table_name,
            column_str=column_str,
            match=match,
        ):
            return response.data
        else:
            return self.empty_value

    def update_row(
        self,
        *,
        table_name: str,
        info: dict,
        match: dict,
        match_type: type,
        use_service_role: bool = False,
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
            match_type (type): The type of the value in the match dictionary.
            use_service_role (bool, optional): Determines whether to use the
                service role client or the default client. Service role client
                should only be used for operations where there is no logged in
                user. Otherwise use default client for RLS policy on
                authenticated user. Defaults to False.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        action: str = "update"

        try:
            match_name, match_value = self._get_filter(
                match,
                expected_value_type=match_type,
                action=action,
                table_name=table_name,
            )
            response = self._execute_query(
                use_service_role=use_service_role,
                table_name=table_name,
                query_func=lambda table: table.update(info).eq(
                    match_name, match_value
                ),
            )
            if not response.data:
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
        use_service_role: bool = False,
    ) -> list[dict]:
        """
        Retrieves a row or columns from a table based on a matching condition
        within a specified period.

        Args:
            table_name (str): The name of the table to retrieve the row from.
            match_column (str): The name of the column to match on.
            within_period (int): The number of seconds within which to search
                for the matching row.
            columns (list[str], optional): A list of column names to retrieve
                from the row. Defaults to None, which retrieves all columns.
            use_service_role (bool, optional): Determines whether to use the
                service role client or the default client. Service role client
                should only be used for operations where there is no logged in
                user. Otherwise use default client for RLS policy on
                authenticated user. Defaults to False.

        Returns:
            List[dict]: A list of dictionaries representing the retrieved row
        """
        action: str = "find row"
        column_str = "*" if columns is None else ", ".join(columns)

        try:
            response = self._execute_query(
                use_service_role=use_service_role,
                table_name=table_name,
                query_func=lambda table: table.select(column_str).lte(
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

        if response.data and self._validate_response(
            response.data,
            expected_type=list,
            action=action,
            table_name=table_name,
            match_column=match_column,
            within_period=within_period,
            columns=columns,
        ):
            return response.data
        return self.empty_value
