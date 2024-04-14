# SupaSaaS

SupaSaaS is a Python library that provides an abstraction layer over the Supabase Python client library. It is designed to simplify common tasks such as user authentication, database operations, and error logging, specifically tailored for Software as a Service (SaaS) applications.

## Features

- **User Authentication**: Provides methods for user sign-up, sign-in, sign-out, and password reset.
- **Database Operations**: Supports inserting, selecting, and updating rows in Supabase tables.
- **Error Logging**: Implements error logging and notification mechanisms for easier debugging and monitoring.
- **Role-based Access Control**: Allows using a service role for specific operations, ensuring proper access control and data isolation.

## Installation

You can install SupaSaaS using pip:

```
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
  from supasaas import SupabaseAuth, SupabaseDB
  ```

2. Initialize the SupabaseAuth and SupabaseDB instances:

  ```python
  supabase_auth = SupabaseAuth()
  supabase_db = SupabaseDB()
  ```

3. Use the provided methods for user authentication and database operations:

  ```python
  # User Authentication
  supabase_auth.sign_up(email="example@email.com", password="password123")
  supabase_auth.sign_in(email="example@email.com", password="password123")
  supabase_auth.sign_out()
  supabase_auth.reset_password(email="example@email.com", domain="example.com")
  supabase_auth.update_user(updates={"name": "John Doe"})

  # Database Operations
  supabase_db.insert_row(table_name="users", updates={"name": "John Doe", "age": 30})
  row = supabase_db.select_row(table_name="users", match={"name": "John Doe"})
  rows = supabase_db.select_rows(table_name="users", matches={"age": [30, 40]})
  supabase_db.update_row(table_name="users", info={"age": 31}, match={"name": "John Doe"})
  ```

### Logging

SupaSaaS includes built-in logging mechanisms for both informational and error logs. By default, logs are saved to .log files in the project root directory. You can customize the logging configuration by modifying the logging_config.py file.

## TODO

1. Unit testing
2. Improve documentation
3. Add sesssion management features to SupabaseAuth class
4. Create storage class

## Contributing

Contributions to SupaSaaS are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on the project's GitHub repository.

## License

SupaSaaS is released under the MIT License.
