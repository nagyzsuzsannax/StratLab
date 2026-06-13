import hashlib

from services.db import get_client, run_query

# simple login backed by a Supabase `users` table. passwords are hashed with SHA256
# before storage and never kept in plain text. deliberately minimal for a school project.

# Error handling: run_query (services/db.py) returns None if the database is
# unreachable. login() treats a None/empty result as "not found" -> returns
# False. register() treats a None/non-empty "taken" check as "username taken"
# -> returns False, so a DB outage fails safe (no account created) rather than
# raising.


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
