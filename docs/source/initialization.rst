Initialization
==============

Here’s a brief example of how to use SupaSaaS:

1. Import the required classes from the SupaSaaS library:

.. code-block:: python

    from supasaas import SupabaseAuth, SupabaseDB, SupabaseStorage, SupabaseClient, SupabaseLogin

2. Initialize the `SupabaseLogin` and `SupabaseClient`:

.. code-block:: python

    supabase_login = SupabaseLogin.from_config()
    supabase_client = SupabaseClient(supabase_login)

3. Initialize the `SupabaseAuth`, `SupabaseDB`, and `SupabaseStorage` instances:

.. code-block:: python

    supabase_auth = SupabaseAuth(client=supabase_client)
    supabase_db = SupabaseDB(client=supabase_client)
    supabase_storage = SupabaseStorage(client=supabase_client)

See the README for more detailed usage instructions.
