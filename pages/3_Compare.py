#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to align two strategies with different
#start dates for a fair comparison
#The logic and design decisions are our own product

import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import prices
import theme
import tickers
import ui
from services import storage
from core import measures
from core.backtest import Backtest
from core.strategy import EqualWeight

BENCHMARKS = ["SPY", "URTH", "VT", "QQQ", "DIA", "IWM", "VTI", "AGG"]

username = st.session_state.get("username", "")


def _annualised_vol(series: pd.Series) -> float:
    """Annualised volatility of a portfolio series, a descriptive stat for the risk-return chart."""
    returns = series.pct_change(fill_method=None).dropna()
    if len(returns) < 2:
        return 0.0
    return float(returns.std() * (252 ** 0.5))


def _market_alpha_beta(net: pd.Series, benchmark_series: pd.Series, rf_annual: float) -> tuple[float, float]:
    """Return CAPM alpha (annualised) and beta of net returns against the selected benchmark."""
    aligned = pd.concat([measures.simple_returns(net), measures.simple_returns(benchmark_series)], axis=1, join="inner").dropna()
    if len(aligned) < 3:
        return float("nan"), float("nan")
    rf_daily = rf_annual / measures.TRADING_DAYS
    capm = measures.capm(aligned.iloc[:, 0] - rf_daily, aligned.iloc[:, 1] - rf_daily, periods_per_year=measures.TRADING_DAYS)
    return capm["alpha_annualized"], capm["beta"]


def _run_comparison(selected: list[dict], benchmark_ticker: str, rf_annual: float) -> dict:
    """Run every selected strategy and the benchmark over their shared period and collect KPIs.

    Returns a dict with either an "error" message, or "strategies" (one row
    of KPIs per strategy), the shared benchmark series and the common date range.
    """
    result = {"key": (tuple(s["name"] for s in selected), benchmark_ticker, rf_annual)}

    #shared window = latest start, earliest end across the selected strategies
    common_start = max(s["start"] for s in selected)
    common_end = min(s["end"] for s in selected)
    if common_start >= common_end:
        result["error"] = "The selected strategies don't share an overlapping date range."
        return result

    benchmark_prices, _ = measures.common_window(prices.load_prices([benchmark_ticker], common_start, common_end), common_start)
    if len(benchmark_prices) < 2:
        result["error"] = "No benchmark data for the shared period."
        return result
    try:
        benchmark_series = Backtest().run(EqualWeight(rebalance_every=252), benchmark_prices)
    except Exception as exc:
        result["error"] = f"Could not run the benchmark backtest: {exc}"
        return result

    rows = []
    skipped = []
    young = set()
    for strategy in selected:
        strategy_raw = prices.load_prices(strategy["tickers"], common_start, common_end)
        #a ticker that doesn't exist on Yahoo Finance (or has no data for this range) is
        #silently dropped by the loader, so flag it here with a clear message
        missing = [t for t in strategy["tickers"] if t not in strategy_raw.columns]
        if missing:
            skipped.append(f"{strategy['name']} (no price data for {', '.join(missing)})")
            continue
        strategy_prices, warns = measures.common_window(strategy_raw, common_start)
        young.update(warns)
        if len(strategy_prices) < 2:
            skipped.append(strategy["name"])
            continue
        try:
            gross = Backtest().run(strategy["strategy"], strategy_prices)
        except Exception:
            skipped.append(strategy["name"])
            continue
        weight_history = strategy["strategy"].weight_history
        #apply the strategy's cash / risk-free overlay, then trading + management fees (net)
        cash = float(strategy["params"].get("_cash", 0.0))
        risk_free = float(strategy["params"].get("_risk_free", 0.0))
        gross = measures.apply_cash_overlay(gross, cash, risk_free, rf_annual / measures.TRADING_DAYS)
        trading_fee = float(strategy["params"].get("_trading_fee", 0.0))
        mgmt_fee = float(strategy["params"].get("_mgmt_fee", 0.0))
        net = measures.apply_costs(gross, weight_history, trading_fee, mgmt_fee)

        analytics = measures.Analytics(net, benchmark_series, rf_annual)
        gross_cagr, net_cagr = measures.cagr(gross), analytics.cagr()
        #alpha/beta as the CAPM regression of net returns against the chosen benchmark
        alpha, beta = _market_alpha_beta(net, benchmark_series, rf_annual)
        candidate = {
            "name": strategy["name"],
            "portfolio": net,
            "cagr": net_cagr,
            "sharpe": analytics.sharpe(),
            "max_drawdown": analytics.max_drawdown(),
            "alpha": alpha,
            "beta": beta,
            "vol": analytics.annualized_volatility(),
            "ann_return": analytics.annualized_return(),
            "gross_cagr": gross_cagr,
            "cost_drag": (1 + gross_cagr) / (1 + net_cagr) - 1,
            "turnover": measures.annual_turnover(weight_history, net),
        }
        #skip a strategy whose curve is unusable (undefined KPIs) rather than poison the table
        numbers = [candidate["cagr"], candidate["sharpe"], candidate["max_drawdown"],
                   candidate["alpha"], candidate["beta"], candidate["vol"], candidate["ann_return"]]
        if not all(math.isfinite(value) for value in numbers):
            skipped.append(strategy["name"])
            continue
        rows.append(candidate)

    if not rows:
        result["error"] = "None of the selected strategies produced a usable backtest result."
        return result

    result["strategies"] = rows
    result["skipped"] = skipped
    result["warnings"] = sorted(young)
    result["common_start"] = common_start
    result["common_end"] = common_end
    result["years"] = (pd.Timestamp(common_end) - pd.Timestamp(common_start)).days / 365.25
    result["rf_annual"] = rf_annual
    result["benchmark_ticker"] = benchmark_ticker
    result["benchmark_series"] = benchmark_series
    result["benchmark_cagr"] = measures.cagr(benchmark_series)
    result["benchmark_vol"] = _annualised_vol(benchmark_series)
    result["benchmark_ann_return"] = measures.annualized_return(measures.simple_returns(benchmark_series))
    return result


# --- render helpers ---

def _equity_chart(rows: list[dict], benchmark_series: pd.Series, benchmark_ticker: str) -> None:
    """Plot every strategy's and the benchmark's equity curves, all indexed to 100."""
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for i, row in enumerate(rows):
        indexed = ui.rebase_to_100(row["portfolio"])
        color = theme.CHART_SEQUENCE[i % len(theme.CHART_SEQUENCE)]
        ax.plot(indexed.index, indexed.values, color=color, linewidth=2, label=row["name"])
    benchmark = ui.rebase_to_100(benchmark_series)
    ax.plot(benchmark.index, benchmark.values, color=theme.TEXT_MUTED, linewidth=1.5, linestyle="--",
            label=benchmark_ticker)
    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed to 100")
    #legend further below the chart, so it never overlaps the "Date" label
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=min(len(rows) + 1, 6))
    fig.tight_layout()
    ui.show_figure(fig)


def _best_max(series: pd.Series) -> set:
    """Return the index label of the largest non-NaN value in `series` (or an empty set)."""
    clean = series.dropna()
    return {clean.idxmax()} if len(clean) else set()


def _best_min(series: pd.Series) -> set:
    """Return the index label of the smallest non-NaN value in `series` (or an empty set)."""
    clean = series.dropna()
    return {clean.idxmin()} if len(clean) else set()


def _core_table(rows: list[dict]) -> None:
    """Render table 1, Key Metrics.

    Same metrics and wording as Evaluate (unlabelled = net of fees), plus the
    annualised average return and volatility from the risk-return chart.
    """
    names = [r["name"] for r in rows]
    raw = pd.DataFrame({
        "CAGR": [r["cagr"] for r in rows],
        "Ann. Return": [r["ann_return"] for r in rows],
        "Ann. Volatility": [r["vol"] for r in rows],
        "Sharpe": [r["sharpe"] for r in rows],
        "Max DD": [r["max_drawdown"] for r in rows],
        "Alpha": [r["alpha"] for r in rows],
        "Beta": [r["beta"] for r in rows],
    }, index=names)
    #best value per column in blue: higher is better, except Volatility (lower); Beta left plain
    highlights = {col: _best_max(raw[col]) for col in ("CAGR", "Ann. Return", "Sharpe", "Max DD", "Alpha")}
    highlights["Ann. Volatility"] = _best_min(raw["Ann. Volatility"])
    disp = pd.DataFrame({
        "CAGR": [theme.format_pct(v) for v in raw["CAGR"]],
        "Ann. Return": [theme.format_pct(v) for v in raw["Ann. Return"]],
        "Ann. Volatility": [theme.format_pct(v) for v in raw["Ann. Volatility"]],
        "Sharpe": [f"{v:.2f}" for v in raw["Sharpe"]],
        "Max DD": [theme.format_pct(v) for v in raw["Max DD"]],
        "Alpha": [theme.format_pct(v) for v in raw["Alpha"]],
        "Beta": [f"{v:.2f}" for v in raw["Beta"]],
    }, index=names)
    tips = {
        "CAGR": "Net (after-fee) compound annual growth rate.",
        "Ann. Return": "Annualised average (arithmetic) return, net of fees.",
        "Ann. Volatility": "Annualised volatility of net returns (the risk-return x-axis).",
        "Sharpe": "Sharpe ratio on net returns.",
        "Alpha": "Annualised CAPM alpha of net returns vs the selected benchmark.",
        "Beta": "Beta of net returns vs the selected benchmark.",
    }
    ui.data_table(disp, highlights=highlights, tips=tips)
    st.caption("Like Evaluate, unlabelled figures are net of fees; Alpha is the CAPM alpha vs the selected benchmark.")


def _frictions_table(rows: list[dict]) -> None:
    """Render table 2, Costs: the same metrics as Evaluate's Costs section."""
    names = [r["name"] for r in rows]
    raw = pd.DataFrame({
        "Gross CAGR": [r["gross_cagr"] for r in rows],
        "Cost Drag": [r["cost_drag"] for r in rows],
        "Annual Turnover": [r["turnover"] for r in rows],
    }, index=names)
    #best value per column in blue: highest gross CAGR, lowest cost drag and turnover
    highlights = {
        "Gross CAGR": _best_max(raw["Gross CAGR"]),
        "Cost Drag": _best_min(raw["Cost Drag"]),
        "Annual Turnover": _best_min(raw["Annual Turnover"]),
    }
    disp = pd.DataFrame({
        "Gross CAGR": [theme.format_pct(v) for v in raw["Gross CAGR"]],
        "Cost Drag": [theme.format_pct(v) for v in raw["Cost Drag"]],
        "Annual Turnover": [theme.format_pct(v) for v in raw["Annual Turnover"]],
    }, index=names)
    tips = {
        "Gross CAGR": "CAGR before fees, the pure strategy.",
        "Cost Drag": "Yearly return lost to fees: (1+Gross CAGR)/(1+CAGR) − 1.",
        "Annual Turnover": "Average fraction of the portfolio traded per year.",
    }
    ui.data_table(disp, highlights=highlights, tips=tips)
    st.caption("The best value per column (highest gross CAGR, lowest cost drag and turnover) is highlighted.")


def _cml_chart(rows: list[dict], benchmark_ticker: str, benchmark_return: float, benchmark_vol: float, rf: float) -> None:
    """Render the risk-return scatter with the Capital Market Line, one point per strategy, net returns."""
    if benchmark_vol <= 0:
        return
    above_list = ui.cml_chart(
        strategies=[{"name": row["name"], "vol": row["vol"], "ann_return": row["ann_return"]} for row in rows],
        benchmark={"ticker": benchmark_ticker, "vol": benchmark_vol, "ann_return": benchmark_return},
        rf=rf, height=440,
    )
    if not above_list:
        return
    st.markdown(f"Strategies **above** the Capital Market Line beat the benchmark ({benchmark_ticker}) on a "
                f"risk-adjusted basis (a higher Sharpe), those **below** it do not. The annualised risk-free rate "
                f"over this period is **{theme.format_pct(rf, 2)}** (^IRX, where the line starts on the y-axis). "
                f"All returns are net of fees.")


# --- PAGE ---

ui.verb_stepper("Compare & Decide")
ui.page_header("Compare Strategies", "Put several strategies head to head.", icon="balance")

strategies = storage.load_strategies(username)
if len(strategies) < 2:
    build_clicked = ui.empty_state("You need at least two saved strategies to compare. Build a few first.", "Go to the Builder")
    if build_clicked:
        st.switch_page("pages/1_Builder.py")
    st.stop()

names = [s["name"] for s in strategies]
#risk-free rate fetched automatically (13-week T-bill ^IRX), same as on Evaluate
rf_annual, _ = prices.load_risk_free_rate()
controls = st.columns([3, 2, 1])
with controls[0]:
    selected_names = st.multiselect("Strategies", names, default=names[:2], key="compare_strategies")
with controls[1]:
    benchmark = st.selectbox("Benchmark", BENCHMARKS, index=0, format_func=tickers.label_for, key="compare_benchmark")
with controls[2]:
    st.write("")  #line the button up with the selects
    run = st.button("Run comparison", type="primary", use_container_width=True)

if run:
    if len(selected_names) < 2:
        st.warning("Select at least two strategies to compare.")
    else:
        by_name = {s["name"]: s for s in strategies}
        selected = [by_name[name] for name in selected_names]
        with st.spinner("Running comparison…"):
            st.session_state["compare_result"] = _run_comparison(selected, benchmark, rf_annual)

result = st.session_state.get("compare_result")
current_key = (tuple(selected_names), benchmark, rf_annual)

if not result or result.get("key") != current_key:
    st.info("Select two or more strategies and a benchmark, then click Run comparison.")
elif result.get("error"):
    st.warning(result["error"])
else:
    rows = result["strategies"]
    if result.get("skipped"):
        st.warning(f"Skipped (no usable backtest result): {', '.join(result['skipped'])}.")
    for message in result.get("warnings", []):
        st.warning(f"{message}, it only enters the backtest from then.")

    st.info(f"Comparing all strategies over their shared timeframe: {result['common_start']} to "
            f"{result['common_end']} ({result['years']:.1f} years).")

    st.subheader("Equity Curves")
    _equity_chart(rows, result["benchmark_series"], result["benchmark_ticker"])

    st.subheader("Key Metrics")
    _core_table(rows)

    st.subheader("Costs")
    _frictions_table(rows)

    st.subheader("Risk vs Return (Capital Market Line)")
    _cml_chart(rows, result["benchmark_ticker"], result["benchmark_ann_return"], result["benchmark_vol"], result["rf_annual"])
