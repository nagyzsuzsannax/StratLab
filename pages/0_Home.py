#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to show different content depending on
#whether a user is logged in
#The logic and design decisions are our own product

import base64
import os
from datetime import date, timedelta

import matplotlib.pyplot as plt
import streamlit as st

import theme
import ui
from core import measures
from core.backtest import Backtest
from prices import clear_prices_cache, load_prices, load_risk_free_rate
from services import storage
from strategies_config import STRATEGIES

#the home page after login. it explains how the app works (Build -> Evaluate -> Compare & Decide)
#and lists the saved strategies. it reads the KPIs stored with each strategy so it loads fast —
#a backtest only runs when the user clicks Update on a card.

_LOCKUP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo-lockup.svg")

username = st.session_state.get("username", "")


def _logo_header() -> None:
    """Render the StratLab lockup, centred, as the page's header (replaces a plain title)."""
    with open(_LOCKUP, encoding="utf-8") as logo_file:
        data = base64.b64encode(logo_file.read().encode("utf-8")).decode()
    st.markdown(
        f"<div style='text-align:center; margin: 0.5rem 0 1.5rem'>"
        f"<img src='data:image/svg+xml;base64,{data}' width='300'></div>",
        unsafe_allow_html=True,
    )

def _update_strategy(strategy: dict) -> None:
    """Re-run the backtest with fresh data up to yesterday and persist the new KPIs."""
    clear_prices_cache()
    #yahoo only settles a day after the close, so we pull up to yesterday
    end = (date.today() - timedelta(days=1)).isoformat()
    with st.spinner(f"Updating {strategy['name']}…"):
        prices = load_prices(strategy["tickers"], strategy["start"], end)
        if prices.empty or len(prices) < 2:
            st.session_state["_flash"] = (f"No price data for {strategy['name']}.", "⚠️")
            st.rerun()
        try:
            portfolio = Backtest().run(strategy["strategy"], prices)
            rf_annual, _ = load_risk_free_rate()
            analytics = measures.Analytics(portfolio, rf_annual=rf_annual)
            kpis = {"cagr": analytics.cagr(), "sharpe": analytics.sharpe(), "max_drawdown": analytics.max_drawdown()}
        except Exception as exc:
            st.session_state["_flash"] = (f"Could not update {strategy['name']}: {exc}", "⚠️")
            st.rerun()
    storage.update_kpis(username, strategy["name"], kpis)
    st.session_state["_flash"] = (f"Updated {strategy['name']}", "✅")
    st.rerun()


# ----- "how it works" hero -----

def _step(column, icon: str, title: str, text: str, page: str, link_label: str, highlight: bool) -> None:
    """Render one "How StratLab Works" step card with an icon, title, text and a link button."""
    with column:
        with st.container(border=True):
            st.markdown(
                f"<div style='font-size:1.9rem;color:{theme.PRIMARY};line-height:1.1'>"
                f"<span class='material-symbols-outlined'>{icon}</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{title}**")
            st.write(text)
            if highlight:
                st.markdown("<span class='chip'>Start here</span>", unsafe_allow_html=True)
            if st.button(link_label, key=f"step_{page}", use_container_width=True,
                         type="primary" if highlight else "secondary"):
                st.switch_page(page)


def _how_it_works(has_strategies: bool) -> None:
    """Render the Build -> Evaluate -> Compare & Decide explainer with one card per step."""
    st.subheader("How StratLab Works")
    st.write("Build a strategy, evaluate it in depth, then compare strategies to decide. "
             "Three steps, three pages.")
    steps = st.columns(3)
    _step(steps[0], "build", "1. Build", "Pick assets, a method and the costs to create a strategy.",
          "pages/1_Builder.py", "Open Builder", highlight=not has_strategies)
    _step(steps[1], "insights", "2. Evaluate", "Backtest one strategy in depth: returns, risk, costs and factors.",
          "pages/2_Evaluate.py", "Open Evaluate", highlight=False)
    _step(steps[2], "balance", "3. Compare & Decide", "Put strategies head to head and against a benchmark.",
          "pages/3_Compare.py", "Open Compare", highlight=False)


# ----- saved-strategy cards -----

def _allocation_pie(strategy: dict, type_label: str) -> plt.Figure:
    """Build a donut chart of how capital is split: the strategy sleeve, risk-free sleeve and cash."""
    cash = float(strategy["params"].get("_cash", 0.0))
    risk_free = float(strategy["params"].get("_risk_free", 0.0))
    invested = max(1 - cash - risk_free, 0.0)
    colors = {type_label: theme.PRIMARY, "Risk-free": theme.ACCENT, "Cash": theme.TEXT_MUTED}
    slices = [(label, value) for label, value in
              [(type_label, invested), ("Risk-free", risk_free), ("Cash", cash)] if value > 0]

    #fixed figure size and axes position (no tight_layout) so every card's donut renders
    #at the same size, regardless of how many slices/legend entries it has. the figure is
    #wide enough that a 3-column legend with the longest strategy label ("Inverse
    #Volatility") still fits inside the canvas with bbox_inches=None
    fig = plt.figure(figsize=(3.4, 2.9))
    ax = fig.add_axes((0.05, 0.28, 0.9, 0.68))
    _, _, autotexts = ax.pie(
        [s[1] for s in slices], colors=[colors[s[0]] for s in slices],
        autopct="%1.0f%%", pctdistance=0.78, startangle=90, wedgeprops=dict(width=0.45),
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(9)
    #ncol is fixed at 3 so the legend always takes up a single row, however many slices there are
    ax.legend([s[0] for s in slices], loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3, fontsize=8,
              handlelength=1.1, handletextpad=0.4, columnspacing=0.8, borderaxespad=0.2)
    return fig


def _strategy_card(strategy: dict) -> tuple[bool, bool]:
    """Render one strategy card (allocation pie, name, tickers, net CAGR and Sharpe, update/delete buttons).

    Returns (update_clicked, delete_clicked).
    """
    kpis = strategy["kpis"]
    type_label = STRATEGIES.get(strategy["type"], {}).get("label", strategy["type"])
    ticker_list = strategy["tickers"]
    ticker_text = ", ".join(ticker_list) if len(ticker_list) <= 6 else f"{len(ticker_list)} tickers"

    with st.container(border=True):
        pie_col, info_col = st.columns([1, 2], vertical_alignment="center")
        with pie_col:
            #bbox_inches=None keeps the fixed figure size, so every donut renders identically
            ui.show_figure(_allocation_pie(strategy, type_label), bbox_inches=None)
        with info_col:
            st.markdown(f"#### {strategy['name']}")
            st.write(f"{type_label} · {ticker_text}")
            metrics = st.columns(2)
            metrics[0].metric("CAGR (net)", theme.format_pct(kpis["cagr"]) if "cagr" in kpis else "—")
            metrics[1].metric("Sharpe", f"{kpis['sharpe']:.2f}" if "sharpe" in kpis else "—")
            buttons = st.columns(2)
            update = buttons[0].button("Update", key=f"upd_{strategy['name']}", use_container_width=True)
            delete = buttons[1].button("Delete", key=f"del_{strategy['name']}", use_container_width=True)
    return update, delete


# --- PAGE ---

#show a toast queued before a rerun, so update/delete confirmations survive the rerun
if "_flash" in st.session_state:
    message, icon = st.session_state.pop("_flash")
    st.toast(message, icon=icon)

_logo_header()

strategies = storage.load_strategies(username)

_how_it_works(bool(strategies))
st.divider()

st.subheader("Your Strategies")

if not strategies:
    build_clicked = ui.empty_state(
        "You haven't built any strategies yet. Start with step 1 above to create your first one.",
        "Go to the Builder",
    )
    if build_clicked:
        st.switch_page("pages/1_Builder.py")
else:
    #let the user order the cards by a KPI from the last backtest
    sort_options = {"Default": None, "Highest Sharpe": "sharpe", "Highest CAGR": "cagr", "Smallest Max Drawdown": "max_drawdown"}
    sort_col, _ = st.columns([1, 2])
    with sort_col:
        sort_choice = st.selectbox("Sort by", list(sort_options.keys()), key="home_sort")
    sort_key = sort_options[sort_choice]
    if sort_key:
        #strategies that have not been updated yet (no KPI) sort to the bottom
        strategies = sorted(strategies, key=lambda s: s["kpis"].get(sort_key, float("-inf")), reverse=True)

    for strategy in strategies:
        update, delete = _strategy_card(strategy)
        if update:
            _update_strategy(strategy)
        elif delete:
            storage.delete_strategy(username, strategy["name"])
            st.session_state["_flash"] = (f"Deleted {strategy['name']}", "🗑️")
            st.rerun()

st.divider()

st.subheader("Research The Universe")
st.write("Before you build, get to know the assets. Explore lets you chart any tickers side by side and "
         "compare their returns, volatility and CAGR, with a correlation heatmap, for a single stock or a "
         "whole basket, over any date range.")
if st.button("Open Explore", key="home_explore"):
    st.switch_page("pages/4_Explore.py")

st.subheader("The Theory")
st.write("Not sure what a Sharpe ratio, a factor model or the Capital Market Line is? The Glossary explains "
         "every metric and strategy in plain language, grouped from the basics to the advanced, each with "
         "its formula.")
if st.button("Open Glossary", key="home_glossary"):
    st.switch_page("pages/5_Glossary.py")

st.subheader("About Us")
st.write("We are two Master in Banking and Finance students at the University of St. Gallen. While running "
         "our own strategy analysis for coursework, we kept rebuilding the same backtests in spreadsheets, "
         "slow, error-prone and impossible to compare cleanly. So we built StratLab: a simple, free tool to "
         "backtest straightforward strategies in minutes instead of hours, without writing a line of code or "
         "paying for data. The whole app follows one idea, Build a strategy, Evaluate it in depth, then "
         "Compare & Decide, so you can go from a hunch to an evidence-based decision fast.")
