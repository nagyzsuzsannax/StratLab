#AI Usage Declaration
#Claude was used to clean up, document and structure this code, and to explain
#how to rebuild a strategy object from its saved JSONB config via the registry
#ChatGPT helped us understand Supabase and how to set up data persistence,
#including how to store and query JSONB columns
#The logic and design decisions (what gets saved per strategy and how a saved
#strategy is rebuilt) are our own product

from services.db import get_client, run_query
from strategies_config import STRATEGIES

# strategies are persisted in a Supabase `strategies` table, one row each. python objects
# cannot be stored directly, so we keep the configuration (tickers / params / kpis as JSONB)
# and rebuild the strategy object on load via the registry.


def save_strategy(username: str, strategy_data: dict) -> None:
    """Insert one strategy for a user.

    `strategy_data` holds: name, type, tickers (list), start, end, and params
    (the constructor kwargs for the strategy class).
    """
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
    rows = run_query(get_client().table("strategies").select("*").eq("username", username).order("id"))
    if rows is None:
        return []

    strategies = []
    for row in rows:
        params = row["params"] or {}
        # rebuild the object from the registry. underscore keys (e.g. the _cash / _risk_free
        # overlay) are config, not constructor arguments, so they are filtered out here.
        strategy_cls = STRATEGIES[row["type"]]["cls"]
        constructor_args = {k: v for k, v in params.items() if not k.startswith("_")}
        strategies.append({
            "name": row["name"],
            "type": row["type"],
            "tickers": row["tickers"] or [],
            "start": str(row["start_date"]),
            "end": str(row["end_date"]),
            "params": params,
            "kpis": row["kpis"] or {},
            "strategy": strategy_cls(**constructor_args),
        })
    return strategies


def delete_strategy(username: str, name: str) -> None:
    """Delete one strategy by name for a user."""
    run_query(get_client().table("strategies").delete().eq("username", username).eq("name", name))


def update_kpis(username: str, name: str, kpis: dict) -> None:
    """Refresh only the stored KPIs for one strategy after an Update, leaving its config untouched."""
    run_query(get_client().table("strategies").update({"kpis": kpis}).eq("username", username).eq("name", name))
