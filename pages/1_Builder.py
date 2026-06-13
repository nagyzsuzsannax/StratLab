from datetime import date, timedelta

import streamlit as st

import tickers
import ui
from services import storage
from strategies_config import STRATEGIES

#rebalancing presets, mapped to trading days; "Custom…" reveals a free number input
REBALANCE_OPTIONS = {"Monthly": 21, "Quarterly": 63, "Yearly": 252, "Custom…": None}

username = st.session_state.get("username", "")


def _format_param_label(name: str) -> str:
    """Turn a param name into a readable label, e.g. "top_n" -> "Top N"."""
    return name.replace("_", " ").title()


def _render_param_block(spec: list[dict]) -> dict:
    """Render the parameter widgets straight from the registry spec and return their values.

    A new strategy shows up here automatically without any change to this page.
    """
    params = {}
    context = {}  #track values so a show_if field can depend on an earlier one (short)
    for p in spec:
        condition = p.get("show_if")
        if condition and not all(context.get(k) == v for k, v in condition.items()):
            continue

        name, ptype = p["name"], p["type"]
        label, help_text, key = _format_param_label(name), p.get("help"), f"builder_{name}"

        if ptype == "bool":
            value = st.checkbox(label, value=bool(p["default"]), help=help_text, key=key)
        elif ptype == "int":
            #a bounded int gets a slider, an open-ended one a number input
            if "min" in p and "max" in p:
                value = int(st.slider(label, min_value=int(p["min"]), max_value=int(p["max"]),
                                      value=int(p["default"]), help=help_text, key=key))
            else:
                value = int(st.number_input(label, min_value=int(p["min"]) if "min" in p else None,
                                            max_value=int(p["max"]) if "max" in p else None,
                                            value=int(p["default"]), step=int(p.get("step", 1)),
                                            help=help_text, key=key))
        else:  # float
            value = float(st.number_input(label, min_value=float(p["min"]) if "min" in p else None,
                                          max_value=float(p["max"]) if "max" in p else None,
                                          value=float(p["default"]), step=float(p.get("step", 0.001)),
                                          format="%.3f", help=help_text, key=key))

        params[name] = value
        context[name] = value
    return params


def _render_weight_fields(symbols: list[str]) -> tuple[dict[str, float], float]:
    """Render one weight field (in %) per ticker for FixedWeight, with a live "sums to 100%?" check.

    Returns the percents per ticker and their total so the page can validate and normalise.
    """
    if not symbols:
        st.info("Select tickers above to set their weights.")
        return {}, 0.0

    st.caption("Set a weight per ticker (in %).")
    default = round(100 / len(symbols), 2)
    columns = st.columns(min(len(symbols), 4))
    percents = {}
    for i, ticker in enumerate(symbols):
        with columns[i % len(columns)]:
            percents[ticker] = st.number_input(f"{ticker} (%)", min_value=0.0, max_value=100.0,
                                               value=default, step=1.0, key=f"builder_weight_{ticker}")

    total = sum(percents.values())
    #green when it adds up to 100%, red otherwise
    if abs(total - 100) < 0.5:
        st.success(f"Weights sum to {total:.1f}% ✓")
    else:
        st.error(f"Weights sum to {total:.1f}%, adjust to 100%")
    return percents, total


def _validate(name: str, symbols: list[str], strategy_type: str, params: dict,
              weights_total: float | None, start: date, end: date,
              cash_pct: float, rf_pct: float) -> list[str]:
    """Collect every reason this strategy cannot be saved yet (empty list = ready to save)."""
    errors = []
    if not name.strip():
        errors.append("Give the strategy a name.")
    if not symbols:
        errors.append("Select at least one ticker.")
    if start >= end:
        errors.append("Start date must be before the end date.")
    if end >= date.today():
        errors.append("End date must be yesterday or earlier.")

    n = len(symbols)
    if strategy_type == "Momentum" and n:
        top_n = params.get("top_n", 0)
        if top_n >= n:
            errors.append(f"Top N ({top_n}) must be less than the number of tickers ({n}).")
        if params.get("short"):
            bottom_n = params.get("bottom_n", 0)
            if bottom_n >= n:
                errors.append(f"Bottom N ({bottom_n}) must be less than the number of tickers ({n}).")
            if top_n + bottom_n > n:
                errors.append(f"Top N + Bottom N ({top_n}+{bottom_n}) cannot exceed the number of tickers ({n}).")
    if strategy_type == "MeanVariance" and n < 2:
        errors.append("Mean-Variance needs at least two tickers.")
    if STRATEGIES[strategy_type].get("needs_weights"):
        if weights_total is None or abs(weights_total - 100) >= 0.5:
            errors.append("Weights must sum to 100%.")
    if cash_pct + rf_pct > 100:
        errors.append("Cash + risk-free cannot exceed 100%.")
    return errors


# --- PAGE ---

ui.verb_stepper("Build")
ui.page_header("Build Strategy", "Create and configure a strategy.", icon="build")

# 1. GENERAL SETUP 
st.subheader("1. General Setup")
name = st.text_input("Strategy name", key="builder_name", placeholder="e.g. My 60/40")
symbols = tickers.select_tickers("Tickers", key="builder_tickers", placeholder="e.g. Microsoft (MSFT)")
strategy_type = st.selectbox("Strategy type", list(STRATEGIES.keys()),
                             format_func=lambda k: STRATEGIES[k]["label"], 
                             key="builder_type", placeholder="Select a strategy type")

needs_weights = STRATEGIES[strategy_type].get("needs_weights", False)
spec = STRATEGIES[strategy_type]["params"]

# 2. STRATEGY PARAMETERS & RULES 
st.subheader("2. Strategy Parameters & Rules")
params = _render_param_block(spec)
percents, weights_total = (None, None)

if needs_weights:
    percents, weights_total = _render_weight_fields(symbols)
elif not spec:
    st.caption("This strategy has no extra parameters.")

choice = st.selectbox("Rebalancing frequency", list(REBALANCE_OPTIONS.keys()), index=2, placeholder="Select rebalancing frequency")
if REBALANCE_OPTIONS[choice] is None:
    rebalance_every = int(st.number_input("Custom (trading days)", min_value=1, value=252, step=1))
else:
    rebalance_every = REBALANCE_OPTIONS[choice]

# 3. CASH ALLOCATION & RISK-FREE ASSETS
st.subheader("3. Cash & Risk-Free Allocation (Optional)")
safe_left, safe_right = st.columns(2)
with safe_left:
    cash_pct = st.number_input("Cash (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0,
                               help="Held uninvested, earns 0%")
with safe_right:
    rf_pct = st.number_input("Risk-free / T-bills (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0,
                             help="Held invested in safe assets, earns the risk-free rate")

# 4. COSTS
st.subheader("4. Trading & Management Costs (Optional)")
cost_left, cost_right = st.columns(2)
with cost_left:
    trading_fee_pct = st.number_input("Trading fee (% of turnover)", min_value=0.0, max_value=5.0, value=0.0, step=0.05,
                                      help="Charged on the traded amount at each rebalance, e.g. 0.10%")
with cost_right:
    mgmt_fee_pct = st.number_input("Management fee (% p.a.)", min_value=0.0, max_value=5.0, value=0.0, step=0.25,
                                   help="Annual fee deducted daily from the whole portfolio, e.g. 1.00%")

# 5. BACKTEST ENVIRONMENT
st.subheader("5. Backtest Timeframe")
yesterday = date.today() - timedelta(days=1)
left, right = st.columns(2)
with left:
    start = st.date_input("Start date", value=date.today() - timedelta(days=5 * 365), max_value=yesterday)
with right:
    end = st.date_input("End date", value=yesterday, max_value=yesterday)

st.divider()
#centre the save button
save_cols = st.columns([1, 1, 1])
with save_cols[1]:
    save_clicked = st.button("Save strategy", type="primary", use_container_width=True)
if save_clicked:
    errors = _validate(name, symbols, strategy_type, params, weights_total, start, end, cash_pct, rf_pct)
    #guard against duplicates and a runaway number of saved strategies
    existing = storage.load_strategies(username)
    if name.strip() in {s["name"] for s in existing}:
        errors.append("A strategy with this name already exists, choose another name.")
    if len(existing) >= 10:
        errors.append("You can save at most 10 strategies, delete one first.")
    if errors:
        st.session_state.pop("_builder_saved", None)
        for error in errors:
            st.error(error)
    else:
        #assemble the constructor kwargs: strategy-specific params + the shared rebalance,
        #plus normalised weights for FixedWeight so they always sum to exactly 1
        final_params = dict(params)
        final_params["rebalance_every"] = rebalance_every
        if needs_weights:
            final_params["weights"] = {ticker: percents[ticker] / weights_total for ticker in symbols}
        #cash / risk-free overlay — underscore keys are not passed to the strategy constructor
        final_params["_cash"] = cash_pct / 100
        final_params["_risk_free"] = rf_pct / 100
        #trading + management fees (turn the gross backtest into a net one)
        final_params["_trading_fee"] = trading_fee_pct / 100
        final_params["_mgmt_fee"] = mgmt_fee_pct / 100

        storage.save_strategy(username, {
            "name": name.strip(),
            "type": strategy_type,
            "tickers": symbols,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "params": final_params,
        })
        st.toast(f"Saved {name.strip()}", icon="✅")
        st.session_state["_builder_saved"] = name.strip()

#after a successful save, keep a confirmation with a link back to Home
if st.session_state.get("_builder_saved"):
    st.success(f"'{st.session_state['_builder_saved']}' has been saved.")
    if st.button("Go to Home", key="builder_go_home"):
        st.session_state.pop("_builder_saved", None)
        st.switch_page("pages/0_Home.py")

#next step in the flow: jump to Evaluate
ui.next_step("Go to Evaluate", "pages/2_Evaluate.py")
