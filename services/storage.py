#AI Usage Declaration
#Claude was used to clean up, document and structure this code, and to explain
#how to rebuild a strategy object from its saved JSONB config via the registry
#ChatGPT helped us understand Supabase and how to set up data persistence,
#including how to store and query JSONB columns
#The logic and design decisions (what gets saved per strategy and how a saved
#strategy is rebuilt) are our own product

import streamlit as st

from services.db import get_client, has_db, run_query
from strategies_config import STRATEGIES

# strategies are persisted in a Supabase `strategies` table, one row each. python objects
# cannot be stored directly, so we keep the configuration (tickers / params / kpis as JSONB)
# and rebuild the strategy object on load via the registry.
#
# when no Supabase is configured (guest mode), the same data lives in st.session_state
# instead, so the app behaves identically for the duration of the session.


def _guest_store(username: str) -> list[dict]:
    """The per-session, per-user list of saved strategies used in guest mode."""
    store = st.session_state.setdefault("_guest_strategies", {})
    return store.setdefault(username, [])


def _rebuild(record: dict) -> dict:
    """Turn a stored strategy record into the dict the pages expect, with a rebuilt object."""
    params = record.get("params") or {}
    strategy_cls = STRATEGIES[record["type"]]["cls"]
    # underscore keys (e.g. the _cash / _risk_free overlay) are config, not constructor args.
    constructor_args = {k: v for k, v in params.items() if not k.startswith("_")}
    return {
        "name": record["name"],
        "type": record["type"],
        "tickers": record.get("tickers") or [],
        "start": str(record.get("start") or record.get("start_date")),
        "end": str(record.get("end") or record.get("end_date")),
        "params": params,
        "kpis": record.get("kpis") or {},
        "strategy": strategy_cls(**constructor_args),
    }


def save_strategy(username: str, strategy_data: dict) -> None:
    """Insert one strategy for a user.

    `strategy_data` holds: name, type, tickers (list), start, end, and params
    (the constructor kwargs for the strategy class).
    """
    if not has_db():
        record = dict(strategy_data)
        record.setdefault("kpis", {})
        _guest_store(username).append(record)
        return
    run_query(get_client().table("strategies").insert({
        "username": username,
        "name": strategy_data["name"],
        "type": strategy_data["type"],
        "tickers": strategy_data["tickers"],
        "start_date": strategy_data["start"],
        "end_date": strategy_data["end"],
        "params": strategy_data["params"],
        # a freshly built strategy has no KPIs yet — they fill in on the first Update
        "kpis": strategy_data.get("kpis", {}),
    }))


def load_strategies(username: str) -> list[dict]:
    """Load a user's strategies (oldest first) and rebuild each strategy object via the registry.

    Returns a list of dicts: name, type, tickers, start, end, params, kpis,
    and strategy (the rebuilt strategy object). Returns an empty list if the
    database is unreachable.
    """
    if not has_db():
        return [_rebuild(record) for record in _guest_store(username)]

    rows = run_query(get_client().table("strategies").select("*").eq("username", username).order("id"))
    if rows is None:
        return []

    return [_rebuild(row) for row in rows]


def delete_strategy(username: str, name: str) -> None:
    """Delete one strategy by name for a user."""
    if not has_db():
        store = _guest_store(username)
        store[:] = [s for s in store if s["name"] != name]
        return
    run_query(get_client().table("strategies").delete().eq("username", username).eq("name", name))


def update_kpis(username: str, name: str, kpis: dict) -> None:
    """Refresh only the stored KPIs for one strategy after an Update, leaving its config untouched."""
    if not has_db():
        for s in _guest_store(username):
            if s["name"] == name:
                s["kpis"] = kpis
        return
    run_query(get_client().table("strategies").update({"kpis": kpis}).eq("username", username).eq("name", name))
