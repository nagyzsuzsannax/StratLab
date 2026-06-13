#AI Usage Declaration
#Claude was used to clean up, document and structure this code, and to explain
#the difference between @st.cache_resource and @st.cache_data so the Supabase
#client is only created once instead of on every rerun
#ChatGPT helped us understand Supabase and how to set up data persistence,
#including how the query builder (.table().select() etc.) and .execute() work
#The logic and design decisions (the shared client and the centralised
#run_query error handling) are our own product

import streamlit as st
from supabase import Client, create_client

# one shared Supabase client, cached across reruns so we don't reconnect every time.
# credentials live in .streamlit/secrets.toml (never committed) under a [supabase] section.


@st.cache_resource
def get_client() -> Client:
    """Return a cached Supabase client built from .streamlit/secrets.toml."""
    config = st.secrets["supabase"]
    return create_client(config["url"], config["key"])


def run_query(builder):
    """Execute a Supabase query builder and return its data, or None on failure.

    Centralises error handling for every database call: network or
    permission errors are shown to the user via st.error instead of
    crashing the page with an unhandled exception. Every function in
    services/auth.py and services/storage.py goes through this, so a single
    try/except here covers all database access in the app.
    """
    try:
        return builder.execute().data
    except Exception as exc:
        st.error(f"Database error: {exc}")
        return None
