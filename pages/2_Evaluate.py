#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand which KPIs are typically reported for a
#backtest and how to interpret them
#The logic and design decisions are our own product

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import prices
import theme
import tickers
import ui
from services import storage
from core import forecast, measures
from core.backtest import Backtest
from core.strategy import EqualWeight

#common benchmarks to compare against; the default is SPY
BENCHMARKS = ["SPY", "URTH", "VT", "QQQ", "DIA", "IWM", "VTI", "AGG"]

username = st.session_state.get("username", "")


# ----- chart derivations (the numbers come from core.measures) -----

def _weights_frame(weight_history: list) -> pd.DataFrame:
    """Turn the strategy's (date, weights) history into a DataFrame, one column per ticker."""
    all_tickers = sorted({ticker for _, weights in weight_history for ticker in weights})
    rows = {}
    for when, weights in weight_history:
        rows[pd.Timestamp(when)] = {ticker: weights.get(ticker, 0.0) for ticker in all_tickers}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def _monthly_returns_table(values: pd.Series) -> pd.DataFrame:
    """Pivot a value series into a year x month table of monthly returns."""
    monthly = measures.to_monthly_returns(values)
    if monthly.empty:
        return pd.DataFrame()
    table = pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "ret": monthly.values})
    return table.pivot(index="year", columns="month", values="ret")


def _stars(p_value: float) -> str:
    """Return significance stars for a p-value (*** < 0.01, ** < 0.05, * < 0.10)."""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


# ----- small render helpers -----

def _block_title(text: str) -> None:
    """Render a small bold section title inside the "Further Metrics" expander."""
    st.markdown(f"<p style='color:{theme.TEXT};font-weight:700;font-size:0.95rem;margin:1rem 0 0.35rem'>{text}</p>", unsafe_allow_html=True)


def _metric_row(label: str, value: str, tip: str = "") -> str:
    """Build one <tr> for a metric table, with an optional hover tooltip on the label."""
    info = f"<span class='info-badge'>?<span class='info-pop'>{tip}</span></span>" if tip else ""
    return f"<tr><td>{label}{info}</td><td>{value}</td></tr>"


def _metric_table(rows: list[tuple]) -> None:
    """Render a list of (label, value, tooltip) rows as a two-column metric table."""
    st.markdown(f"<table class='metric-table'>{''.join(_metric_row(*r) for r in rows)}</table>", unsafe_allow_html=True)


# ----- the backtest run + analytics -----

def _factor_models(portfolio: pd.Series) -> tuple[dict, object]:
    """Run CAPM/FF3/FF5 monthly regressions on `portfolio`'s returns.

    Returns (results, last_factor_date) where `results` maps each model name
    to its regression dict, or None if there isn't enough overlapping history
    (~2+ years of monthly data).
    """
    monthly = measures.to_monthly_returns(portfolio)
    specs = {"CAPM": ("FF3", ["Mkt-RF"]),
             "FF3": ("FF3", ["Mkt-RF", "SMB", "HML"]),
             "FF5": ("FF5", ["Mkt-RF", "SMB", "HML", "RMW", "CMA"])}
    results = {}
    last_date = None
    for name, (ff_model, cols) in specs.items():
        try:
            factors = prices.load_factors(ff_model)
        except Exception:
            results[name] = None
            continue
        joined = pd.concat([monthly.rename("ret"), factors], axis=1, join="inner").dropna()
        if len(joined) < 24:
            results[name] = None
            continue
        excess = joined["ret"] - joined["RF"]
        try:
            if name == "CAPM":
                results[name] = measures.capm(excess, joined["Mkt-RF"], periods_per_year=measures.MONTHS)
            else:
                results[name] = measures.factor_model(excess, joined[cols], periods_per_year=measures.MONTHS)
            last_date = joined.index[-1]
        except Exception:
            results[name] = None
    return results, last_date


def _market_model(portfolio: pd.Series, benchmark: pd.Series, rf_annual: float) -> dict | None:
    """Run a single-factor regression of the strategy on the chosen benchmark (daily, rf-adjusted)."""
    sr = measures.simple_returns(portfolio)
    br = measures.simple_returns(benchmark)
    aligned = pd.concat([sr, br], axis=1, join="inner").dropna()
    if len(aligned) < 3:
        return None
    rf_daily = rf_annual / measures.TRADING_DAYS
    return measures.capm(aligned.iloc[:, 0] - rf_daily, aligned.iloc[:, 1] - rf_daily, periods_per_year=measures.TRADING_DAYS)


def _run_evaluation(strategy: dict, benchmark_ticker: str, rf_annual: float) -> dict:
    """Run the strategy and benchmark backtests and compute everything the page renders.

    Returns a dict with either an "error" message, or the net/gross portfolio
    series, the benchmark series, the weight history and the factor model results.
    """
    result = {"key": (strategy["name"], benchmark_ticker)}

    raw = prices.load_prices(strategy["tickers"], strategy["start"], strategy["end"])
    #a ticker that doesn't exist on Yahoo Finance (or has no data for this range) is
    #silently dropped by the loader, so flag it here with a clear message
    missing = [t for t in strategy["tickers"] if t not in raw.columns]
    if missing:
        result["error"] = f"No price data found for: {', '.join(missing)}. Edit the strategy in the Builder to fix the ticker."
        return result

    bench_raw = prices.load_prices([benchmark_ticker], strategy["start"], strategy["end"])
    strat_prices, warnings = measures.common_window(raw, strategy["start"])
    bench_prices, _ = measures.common_window(bench_raw, strategy["start"])
    if len(strat_prices) < 2 or len(bench_prices) < 2:
        result["error"] = "Not enough price data for this strategy or benchmark."
        return result

    try:
        gross = Backtest().run(strategy["strategy"], strat_prices)
        benchmark = Backtest().run(EqualWeight(rebalance_every=252), bench_prices)
    except Exception as exc:
        result["error"] = f"Could not run the backtest: {exc}"
        return result
    weight_history = strategy["strategy"].weight_history

    cash = float(strategy["params"].get("_cash", 0.0))
    risk_free = float(strategy["params"].get("_risk_free", 0.0))
    gross = measures.apply_cash_overlay(gross, cash, risk_free, rf_annual / measures.TRADING_DAYS)

    #apply trading + management fees to get the net curve (net == gross when both fees are 0)
    trading_fee = float(strategy["params"].get("_trading_fee", 0.0))
    mgmt_fee = float(strategy["params"].get("_mgmt_fee", 0.0))
    net = measures.apply_costs(gross, weight_history, trading_fee, mgmt_fee)

    factors, factor_date = _factor_models(net)
    factors_gross, _ = _factor_models(gross)
    result.update(portfolio=net, gross=gross, benchmark=benchmark, benchmark_ticker=benchmark_ticker,
                  weight_history=weight_history, rf_annual=rf_annual, warnings=warnings,
                  cash=cash, risk_free=risk_free, trading_fee=trading_fee, mgmt_fee=mgmt_fee,
                  annual_turnover=measures.annual_turnover(weight_history, net),
                  market_model=_market_model(net, benchmark, rf_annual),
                  factors=factors, factors_gross=factors_gross, factor_date=factor_date)
    return result


# ----- render: key metrics (above the chart) -----

def _key_metrics(result: dict, benchmark_label: str) -> None:
    """Render the five headline KPI cards: CAGR, Sharpe, Max Drawdown, Alpha, Beta."""
    analytics = measures.Analytics(result["portfolio"], result["benchmark"], result["rf_annual"])
    mm = result["market_model"]
    cagr, sharpe, mdd = analytics.cagr(), analytics.sharpe(), analytics.max_drawdown()
    alpha = mm["alpha_annualized"] if mm else float("nan")
    beta = mm["beta"] if mm else float("nan")

    if mm:
        sig = "significant at 5%" if mm["alpha_pvalue"] < 0.05 else "not significant"
        alpha_tip = (f"Alpha vs the benchmark ({benchmark_label}), annualised from daily data "
                     f"(market-model regression), {sig} (p = {mm['alpha_pvalue']:.3f}).")
    else:
        alpha_tip = f"Alpha vs the benchmark ({benchmark_label})."
    beta_tip = (f"Sensitivity to the benchmark ({benchmark_label}). Beta < 1 means lower volatility "
                f"than the benchmark, > 1 higher, < 0 opposite.")
    rf_text = (f" Risk-free rate = 13-week T-bill ^IRX: {theme.format_pct(result['rf_annual'], 2)}"
               + (f" as of {result['rf_date']}." if result.get("rf_date") else "."))

    cards = st.columns(5)
    with cards[0]:
        ui.kpi_card("CAGR", theme.format_pct(cagr), good=cagr > 0,
                    tooltip="Compound annual growth rate of the equity curve: (V_end/V_start)^(252/n) − 1.")
    with cards[1]:
        ui.kpi_card("Sharpe", f"{sharpe:.2f}",
                    tooltip="Annualised excess return over the risk-free rate ÷ volatility: (mean(R−rf)×252)/(σ×√252). Above 1 is generally good." + rf_text)
    with cards[2]:
        ui.kpi_card("Max Drawdown", theme.format_pct(mdd), good=False,
                    tooltip="The largest peak-to-trough fall in portfolio value.")
    with cards[3]:
        ui.kpi_card("Alpha", theme.format_pct(alpha), good=alpha > 0, tooltip=alpha_tip)
    with cards[4]:
        ui.kpi_card("Beta", f"{beta:.2f}", tooltip=beta_tip)


def _cost_metrics(result: dict) -> None:
    """Render the three cost KPI cards: Gross CAGR, Cost Drag and Annual Turnover."""
    net_cagr = measures.cagr(result["portfolio"])
    gross_cagr = measures.cagr(result["gross"])
    cost_drag = (1 + gross_cagr) / (1 + net_cagr) - 1
    cards = st.columns(3)
    with cards[0]:
        ui.kpi_card("Gross CAGR", theme.format_pct(gross_cagr),
                    tooltip="CAGR of the strategy before any fees, the theoretical return of the pure strategy.")
    with cards[1]:
        ui.kpi_card("Cost Drag (p.a.)", theme.format_pct(cost_drag), good=False if cost_drag > 0.0001 else None,
                    tooltip="Return lost to fees each year: (1 + Gross CAGR) / (1 + Net CAGR) − 1. The headline cost metric.")
    with cards[2]:
        ui.kpi_card("Annual Turnover", theme.format_pct(result["annual_turnover"]),
                    tooltip="Average fraction of the portfolio bought and sold per year, explains the cost drag.")


# ----- render: charts -----

def _equity_chart(result: dict, strategy_name: str) -> None:
    """Plot the strategy's and benchmark's equity curves, both indexed to 100."""
    portfolio = ui.rebase_to_100(result["portfolio"])
    benchmark = ui.rebase_to_100(result["benchmark"])
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(portfolio.index, portfolio.values, color=theme.PRIMARY, linewidth=2, label=strategy_name)
    ax.plot(benchmark.index, benchmark.values, color=theme.TEXT_MUTED, linewidth=1.5, linestyle="--",
            label=result["benchmark_ticker"])
    for year in range(portfolio.index[0].year + 1, portfolio.index[-1].year + 1):
        ax.axvline(pd.Timestamp(f"{year}-01-01"), color=theme.BORDER, linewidth=1, linestyle=":")
    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed to 100")
    ax.legend(loc="upper left")
    fig.tight_layout()
    ui.show_figure(fig)


def _drawdown_chart(portfolio: pd.Series) -> None:
    """Plot the portfolio's drawdown (% below its running peak) over time."""
    peak = portfolio.cummax()
    drawdown = (portfolio - peak) / peak * 100
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(drawdown.index, drawdown.values, 0, color=theme.NEGATIVE, alpha=0.2)
    ax.plot(drawdown.index, drawdown.values, color=theme.NEGATIVE, linewidth=1)
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    fig.tight_layout()
    ui.show_figure(fig)


def _allocation_chart(weight_history: list) -> None:
    """Plot the portfolio's weight per ticker over time as a stacked area chart."""
    if not weight_history:
        st.info("No allocation history for this strategy.")
        return
    frame = _weights_frame(weight_history) * 100
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.stackplot(frame.index, frame.values.T, labels=frame.columns,
                  colors=theme.CHART_SEQUENCE[:len(frame.columns)])
    ax.set_xlabel("Date")
    ax.set_ylabel("Weight (%)")
    #legend further below the chart, so it never overlaps the "Date" label
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=min(len(frame.columns), 6))
    fig.tight_layout()
    ui.show_figure(fig)


def _monthly_heatmap(portfolio: pd.Series) -> None:
    """Render a year x month heatmap of the portfolio's monthly returns."""
    pivot = _monthly_returns_table(portfolio)
    if pivot.empty:
        st.info("Not enough history for a monthly breakdown.")
        return
    bound = float(max(abs(pivot.min().min()), abs(pivot.max().max())) * 100) or 1.0
    names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
             7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    data = (pivot * 100).rename(columns=names)
    cmap = mcolors.LinearSegmentedColormap.from_list("returns", [theme.NEGATIVE, "#FFFFFF", theme.POSITIVE])

    fig, ax = plt.subplots(figsize=(10, 0.4 * len(data) + 1.5))
    im = ax.imshow(data.values, cmap=cmap, vmin=-bound, vmax=bound, aspect="auto")
    ax.set_xticks(range(len(data.columns)))
    ax.set_xticklabels(data.columns)
    ax.set_yticks(range(len(data.index)))
    ax.set_yticklabels(data.index)
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.grid(False)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data.values[i, j]
            if not pd.isna(value):
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=9, color=theme.TEXT)
    fig.colorbar(im, ax=ax, label="%", shrink=0.8)
    fig.tight_layout()
    ui.show_figure(fig)


def _cml_chart(result: dict, strategy_name: str) -> None:
    """Render the risk/return scatter with the Capital Market Line and an explanatory caption.

    A strategy above the line beats the benchmark on a risk-adjusted basis.
    """
    rf = result["rf_annual"]
    analytics = measures.Analytics(result["portfolio"], result["benchmark"], rf)
    p_vol, p_ret = analytics.annualized_volatility(), analytics.annualized_return()
    bench_returns = measures.simple_returns(result["benchmark"])
    b_vol = measures.volatility(bench_returns, annualized=True)
    b_ret = measures.annualized_return(bench_returns)

    above_list = ui.cml_chart(
        strategies=[{"name": strategy_name, "vol": p_vol, "ann_return": p_ret}],
        benchmark={"ticker": result["benchmark_ticker"], "vol": b_vol, "ann_return": b_ret},
        rf=rf, height=380,
    )
    if not above_list:
        return

    word = "above" if above_list[0] else "below"
    quality = "higher" if above_list[0] else "lower"
    st.markdown(f"The strategy lies **{word}** the Capital Market Line → a **{quality}** risk-adjusted return "
                f"(Sharpe) than the benchmark ({result['benchmark_ticker']}). The annualised risk-free rate over "
                f"this period is **{theme.format_pct(rf, 2)}** (^IRX, where the line starts on the y-axis).")


# ----- render: advanced metrics, grouped in the quant flow -----

def _advanced_metrics(result: dict) -> None:
    """Render the "Further Metrics" expander: distribution, risk, factor models and cost analysis."""
    analytics = measures.Analytics(result["portfolio"], result["benchmark"], result["rf_annual"])
    capm_result = result["factors"].get("CAPM")

    _block_title("1. Absolute Performance & Volatility")
    _metric_table([
        ("Average daily return", theme.format_pct(analytics.average_daily_return(), 3), "Mean of the daily returns."),
        ("Average monthly return", theme.format_pct(analytics.average_monthly_return(), 2), "Mean of the monthly returns."),
        ("Volatility (daily)", theme.format_pct(analytics.daily_volatility(), 2), "Standard deviation of daily returns."),
        ("Volatility (monthly)", theme.format_pct(analytics.monthly_volatility(), 2), "Standard deviation of monthly returns."),
        ("Volatility (annualised)", theme.format_pct(analytics.annualized_volatility()), "Daily volatility × √252."),
    ])

    _block_title("2. Downside & Tail Risk")
    var_index = ["Historic VaR (next day)", "Var-cov VaR (next day)", "Var-cov VaR (next month)"]
    var_table = pd.DataFrame({
        "95%": [f"{v:.2%}" for v in (analytics.historic_var(0.95), analytics.parametric_var(0.95, 1), analytics.parametric_var(0.95, 21))],
        "99%": [f"{v:.2%}" for v in (analytics.historic_var(0.99), analytics.parametric_var(0.99, 1), analytics.parametric_var(0.99, 21))],
    }, index=var_index)
    ui.data_table(var_table, bold=False)
    jb_stat, jb_p = analytics.jarque_bera()
    verdict = "looks normal" if jb_p > 0.05 else "not normal (fat tails / skew)"
    _metric_table([
        ("Skewness", f"{analytics.skewness():.2f}", "Asymmetry; 0 = symmetric, <0 = longer left tail."),
        ("Excess kurtosis", f"{analytics.excess_kurtosis():.2f}", "Fat-tailedness vs normal (K − 3); >0 = fatter tails."),
        ("Jarque-Bera stat", f"{jb_stat:.1f}", "Test statistic, χ²(2) under normality."),
        ("Jarque-Bera p-value", f"{jb_p:.3f} ({verdict})", "A small p-value rejects normality."),
    ])

    _block_title("3. Risk-Adjusted (vs Itself)")
    _metric_table([
        ("Sortino ratio", f"{analytics.sortino():.2f}", "Like Sharpe but only downside volatility is penalised."),
    ])

    _block_title("4. Benchmark & Factor Models")
    _metric_table([
        ("Treynor ratio (annual)", f"{analytics.treynor():.3f}", "Annualised excess return ÷ beta (systematic risk)."),
        ("Appraisal / Information ratio", f"{capm_result['appraisal_ratio']:.3f}" if capm_result else "—", "Jensen alpha ÷ residual risk (α/σ(ε))."),
    ])
    st.caption("Factor models, monthly regressions, annualised α (*** p<0.01, ** p<0.05, * p<0.1)")
    _factor_table(result)

    _block_title("5. Costs & Frictions")
    gross_ff3 = result["factors_gross"].get("FF3")
    net_ff3 = result["factors"].get("FF3")
    gross_alpha = gross_ff3["alpha_annualized"] if gross_ff3 else None
    net_alpha = net_ff3["alpha_annualized"] if net_ff3 else None
    g_final, n_final, g_start = result["gross"].iloc[-1], result["portfolio"].iloc[-1], result["gross"].iloc[0]
    total_frictions = (g_final - n_final) / (g_final - g_start) if g_final > g_start else 0.0
    decay = gross_alpha - net_alpha if (gross_alpha is not None and net_alpha is not None) else None
    _metric_table([
        ("Gross alpha (FF3, annual)", theme.format_pct(gross_alpha) if gross_alpha is not None else "—", "FF3 alpha of the strategy before fees."),
        ("Net alpha (FF3, annual)", theme.format_pct(net_alpha) if net_alpha is not None else "—", "FF3 alpha after fees."),
        ("Alpha decay", theme.format_pct(decay) if decay is not None else "—", "How much of the alpha the fees eat up (gross − net)."),
        ("Total frictions", theme.format_pct(total_frictions), "Share of the gross gains consumed by costs over the whole period."),
    ])


def _factor_table(result: dict) -> None:
    """Render the CAPM/FF3/FF5 factor regression table (annualised alpha, t/p-stats, R², betas)."""
    factors = result["factors"]
    if all(value is None for value in factors.values()):
        st.info("Not enough monthly history yet for the factor regressions (need ~2+ years).")
        return
    factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    columns = ["Ann. α", "t(α)", "p(α)", "R²", "Appraisal"] + factor_cols
    rows = {}
    for name, res in factors.items():
        if res is None:
            continue
        betas, betap = res["betas"], res["beta_pvalues"]
        rows[name] = {
            "Ann. α": theme.format_pct(res["alpha_annualized"]) + _stars(res["alpha_pvalue"]),
            "t(α)": f"{res['alpha_tstat']:.2f}",
            "p(α)": f"{res['alpha_pvalue']:.3f}",
            "R²": f"{res['r_squared']:.2f}",
            "Appraisal": f"{res['appraisal_ratio']:.3f}",
            **{col: (f"{betas[col]:.2f}{_stars(betap[col])}" if col in betas else "—") for col in factor_cols},
        }
    ui.data_table(pd.DataFrame(rows).T[columns])
    if result.get("factor_date") is not None:
        st.caption(f"Caution: Fama-French data runs only to {result['factor_date'].date()} "
                   "(the library is published with a ~2-month lag).")


# --- PAGE ---

ui.verb_stepper("Evaluate")
ui.page_header("Evaluate Strategy", "Backtest one strategy in depth.", icon="insights")

strategies = storage.load_strategies(username)
if not strategies:
    build_clicked = ui.empty_state("No strategies yet, build one first, then come back to evaluate it.", "Go to the Builder")
    if build_clicked:
        st.switch_page("pages/1_Builder.py")
    st.stop()

rf_annual, rf_date = prices.load_risk_free_rate()

names = [s["name"] for s in strategies]
controls = st.columns([2, 2, 1])
with controls[0]:
    chosen_name = st.selectbox("Strategy", names, key="eval_strategy")
with controls[1]:
    benchmark = st.selectbox("Benchmark", BENCHMARKS, index=0, format_func=tickers.label_for, key="eval_benchmark")
with controls[2]:
    st.write("")
    run = st.button("Run backtest", type="primary", use_container_width=True)

strategy = next(s for s in strategies if s["name"] == chosen_name)

if run:
    with st.spinner("Running backtest and analytics…"):
        result = _run_evaluation(strategy, benchmark, rf_annual)
        result["rf_date"] = rf_date
        st.session_state["eval_result"] = result

result = st.session_state.get("eval_result")

if not result or result.get("key") != (chosen_name, benchmark):
    st.info("Choose a strategy and benchmark, then click Run backtest.")
elif result.get("error"):
    st.warning(result["error"])
else:
    for message in result.get("warnings", []):
        st.warning(f"{message}, it only enters the backtest from then (the backtest starts once every ticker has data).")

    st.subheader("Key Metrics")
    _key_metrics(result, tickers.label_for(result["benchmark_ticker"]))

    with st.expander("Further Metrics (advanced)"):
        _advanced_metrics(result)

    st.subheader("Costs")
    _cost_metrics(result)

    st.subheader("Absolute Metrics")
    #the start capital the user can change, projected (net of fees) over the backtest period,
    #plus the same two cost points as the Costs section but in absolute dollars
    capital_col, grown_col = st.columns([1, 2], vertical_alignment="center")
    with capital_col:
        start_capital = st.number_input("Start capital ($)", min_value=1, value=10000, step=1000, key="eval_capital")
    net_final = start_capital * result["portfolio"].iloc[-1] / result["portfolio"].iloc[0]
    gross_final = start_capital * result["gross"].iloc[-1] / result["gross"].iloc[0]
    with grown_col:
        st.markdown(
            f"<div class='grow-box'><span>{theme.format_money(start_capital)}</span>"
            f"<span class='grow-arrow'>→</span>"
            f"<span class='grow-final'>{theme.format_money(net_final)}</span>"
            f"<span class='grow-caption'>net, over the backtest period</span></div>",
            unsafe_allow_html=True,
        )
    abs_cards = st.columns(2)
    with abs_cards[0]:
        ui.kpi_card("Gross final value", theme.format_money(gross_final),
                    tooltip="What the start capital would be worth with no fees, the pure strategy.")
    with abs_cards[1]:
        ui.kpi_card("Total cost", theme.format_money(gross_final - net_final),
                    good=False if gross_final - net_final > 0.5 else None,
                    tooltip="Money lost to trading and management fees over the whole period (gross final − net final).")

    st.subheader("Charts")
    st.markdown("**Performance (Indexed to 100)**")
    _equity_chart(result, chosen_name)
    st.markdown("**Drawdown**")
    _drawdown_chart(result["portfolio"])

    st.subheader("Allocation Over Time")
    _allocation_chart(result["weight_history"])

    st.subheader("Monthly Returns")
    _monthly_heatmap(result["portfolio"])

    st.subheader("Risk vs Return (Capital Market Line)")
    _cml_chart(result, chosen_name)

    st.subheader("Forecast")
    direction = forecast.predict_direction(result["portfolio"])
    if direction is None:
        st.info("Not enough price history for a forecast.")
    else:
        st.metric("Probability of a positive return tomorrow", theme.format_pct(direction["probability_up"]))
        st.caption(f"Model accuracy on historical test data: {theme.format_pct(direction['accuracy'])}")
    st.caption("Logistic regression on the last 10 days' returns. For educational purposes only, not investment advice.")

#next step in the flow: jump to Compare
ui.next_step("Go to Compare", "pages/3_Compare.py")
