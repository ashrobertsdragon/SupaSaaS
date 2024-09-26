# SupaSaaS

SupaSaaS is a Python library that provides an abstraction layer over the Supabase Python client library. It is designed to simplify common tasks such as user authentication, database operations, and error logging, specifically tailored for Software as a Service (SaaS) applications.

## Features

- **User Authentication**: Provides methods for user sign-up, sign-in, sign-out, and password reset.
- **Database Operations**: Supports inserting, selecting, and updating rows in Supabase tables.
- **Error Logging**: Implements error logging and notification mechanisms for easier debugging and monitoring.
- **Role-based Access Control**: Allows using a service role for specific operations, ensuring proper access control and data isolation.

## Installation

You can install SupaSaaS using pip:

```bash
pip install supasaas
```

## Configuration

SupaSaaS requires several environment variables to be set for proper configuration:

- SUPABASE_URL: The URL of your Supabase project.
- SUPABASE_KEY: The API key for your Supabase project.
- SUPABASE_SERVICE_ROLE: The service role key for your Supabase project.

## Usage

1. Import the required classes from the SupaSaaS library:

    ```python
    from supasaas import SupabaseAuth, SupabaseDB, SupabaseStorage, SupabaseClient, SupabaseLogin
    ```

2. Initialize the `SupabaseLogin` and `SupabaseClient`:

    ```python
    supabase_login = SupabaseLogin.from_config()
    supabase_client = SupabaseClient(supabase_login)
    ```

3. Initialize the `SupabaseAuth`, `SupabaseDB`, and `SupabaseStorage` instances:

    ```python
    # If needed, you can also import and provide your own validator and logger
    # from supasaas import validate, supabase_logger

    supabase_auth = SupabaseAuth(client=supabase_client)
    supabase_db = SupabaseDB(client=supabase_client)
    supabase_storage = SupabaseStorage(client=supabase_client)
    ```

4. Use the provided methods for user authentication, database operations, and storage management:

   ### User Authentication

    ```python
    supabase_auth.sign_up(email="example@email.com", password="password123")
    supabase_auth.sign_in(email="example@email.com", password="password123")
    supabase_auth.sign_out()
    supabase_auth.reset_password(email="example@email.com", domain="example.com")
    supabase_auth.update_user(updates={"name": "John Doe"})
    ```

   ### Database Operations

    ```python
    supabase_db.insert_row(table_name="users", updates={"name": "John Doe", "age": 30"})
    row = supabase_db.select_row(table_name="users", match={"name": "John Doe"})
    rows = supabase_db.select_rows(table_name="users", matches={"age": [30, 40]})
    supabase_db.update_row(table_name="users", info={"age": 31}, match={"name": "John Doe"})
    ```

   ### Storage Management

    ```python
    # Create a signed URL for downloading a file
    signed_url = supabase_storage.create_signed_url(
        bucket="my_bucket", download_path="path/to/file"
    )
    
    # List files in a bucket or folder
    files = supabase_storage.list_files(bucket="my_bucket", folder="path/to/folder")
    
    # Download a file from storage
    success = supabase_storage.download_file(
        bucket="my_bucket", download_path="path/to/file", destination_path=Path("/local/path")
    )
    
    # Delete a file from storage
    deleted = supabase_storage.delete_file(bucket="my_bucket", file_path="path/to/file")
    
    # Upload a file to storage
    uploaded = supabase_storage.upload_file(
        bucket="my_bucket",
        upload_path="path/to/upload",
        file_content=b"file contents",
        file_mimetype="text/plain"
    )
    ```

### Notes

- **SupabaseLogin**: `SupabaseLogin.from_config()` uses environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE`), so ensure these are set up properly in your environment.
- **Validator and Logger**: Both the `validator` and `log_function` are optional, defaulting to `validate` and `supabase_logger`, but you can pass your own if needed.
- **Storage Management**: The `SupabaseStorage` class provides methods for file operations, including `upload_file`, `list_files`, and `create_signed_url`.

### Logging

SupaSaaS includes built-in logging mechanisms for both informational and error logs. By default, logs are saved to .log files in the project root directory. You can customize the logging configuration by modifying the logging_config.py file.

## TODO

1. Unit testing
2. Improve documentation

## Contributing

Contributions to SupaSaaS are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on the project's GitHub repository.

## License

SupaSaaS is released under the MIT License.
