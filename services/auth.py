#AI Usage Declaration
#Claude was used to clean up, document and structure this code, and to explain
#why passwords should be hashed with SHA256 before being stored rather than
#kept as plain text
#ChatGPT helped us understand Supabase and how to set up data persistence,
#including how to query and insert rows into the `users` table
#The logic and design decisions (the login/register flow and how a failed
#database call should be handled) are our own product

import hashlib

from services.db import get_client, run_query

# simple login backed by a Supabase `users` table. passwords are hashed with SHA256
# before storage and never kept in plain text. deliberately minimal for a school project.


def hash_password(password: str) -> str:
    """Hash a password with SHA256 so we never store it in plain text."""
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str) -> bool:
    """Check a username/password pair against the stored users."""
    rows = run_query(get_client().table("users").select("password").eq("username", username))
    if not rows:
        return False
    # compare the hash, never the plain password
    return rows[0]["password"] == hash_password(password)


def register(username: str, password: str) -> bool:
    """Register a new user. Returns False if the username is already taken."""
    client = get_client()
    taken = run_query(client.table("users").select("username").eq("username", username))
    if taken is None or taken:
        return False
    run_query(client.table("users").insert({"username": username, "password": hash_password(password)}))
    return True
